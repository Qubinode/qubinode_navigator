# ADR-0066: Developer Agent DAG Validation and Smart Pipelines

## Status

**ACCEPTED** - Implemented (2025-12-08)

## Context

### The Problem: Silent DAG Failures

Traditional Airflow DAG execution has a critical blind spot: **shadow errors**.

**Shadow Errors** are failures that:
- Don't cause the DAG to fail (task succeeds, but output is wrong)
- Happen in external systems (VM not created, certificate not issued, DNS not updated)
- Pass validation but break downstream dependencies
- Are only discovered when dependent DAGs fail or users manually verify

**Example Scenario:**
```
1. DAG "freeipa_deployment" runs and marks SUCCESS ✅
2. User expects FreeIPA VM at freeipa.example.com
3. VM creation silently failed (libvirt error, but task didn't catch it)
4. Dependent DAG "keycloak_deployment" fails because FreeIPA DNS not available ❌
5. Hours wasted debugging Keycloak, when root cause was FreeIPA VM creation
```

### Current State (ADR-0046)

ADR-0046 established DAG validation standards:
- Syntax validation (Python AST parsing)
- Import validation (Airflow DagBag)
- Lint checks (ADR-0045 standards)

**Gap**: These only validate the DAG code, not the execution outcomes.

## Decision

### 1. Smart Pipeline Pattern

Implement **Smart Pipelines**: DAG executions enhanced with pre-validation, outcome verification, and shadow error detection.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Traditional DAG Execution                   │
│  User → Trigger DAG → Tasks Run → Status: SUCCESS/FAIL          │
│                                                                  │
│  Problem: Status=SUCCESS doesn't mean infrastructure is correct │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Smart Pipeline (ADR-0066)                   │
│                                                                  │
│  1. Developer Agent validates prerequisites                      │
│  2. DAG executes with OpenLineage tracking                       │
│  3. Observer Agent detects shadow errors                         │
│  4. Feedback loop with corrective actions                        │
│                                                                  │
│  Result: User knows actual infrastructure state, not just status │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Developer Agent Pre-Flight Validation

Before triggering a DAG, the Developer Agent performs comprehensive validation:

```python
# Phase 1: Prerequisites Check
prerequisites = {
    "vm": {
        "check": "libvirt connection active",
        "command": "virsh list",
    },
    "image": {
        "check": "VM image available",
        "command": "kcli list images | grep centos9stream",
    },
    "dns": {
        "check": "DNS server reachable",
        "command": "dig +short dns.example.com",
    },
    "disk_space": {
        "check": "Sufficient disk space",
        "command": "df -h /var/lib/libvirt | awk 'NR==2 {print $5}'"
    }
}

# Phase 2: Provider-First Rule
# Ensure required Airflow providers are installed
required_providers = ["ssh", "http", "postgres"]
installed_providers = list_installed_providers()
missing = [p for p in required_providers if p not in installed_providers]
if missing:
    raise ValueError(f"Missing providers: {missing}")

# Phase 3: RAG Documentation Query
# Find relevant documentation for the task
docs = query_rag(f"How to deploy {task_type}")
confidence = compute_confidence(docs, prerequisites)
```

**Output**: `DeveloperTaskResult` with:
- `prerequisites_met: bool` - Can the DAG run?
- `confidence: float` - How confident are we it will succeed?
- `validation_errors: List[str]` - Specific issues to fix
- `recommended_actions: List[str]` - What to do before running

### 3. Observer Agent Shadow Error Detection

After DAG execution, the Observer Agent validates actual outcomes:

```python
class ShadowError:
    """Represents a shadow error detected by Observer Agent."""
    error_type: str  # "vm_not_created", "cert_not_issued", "dns_not_updated"
    severity: str    # "critical", "warning", "info"
    detected_by: str # "vm_status_check", "dig_query", "cert_verify"
    evidence: str    # Command output or API response
    fix_commands: List[str]  # Shell commands to fix the issue

# Example Shadow Error Detection
async def detect_vm_shadow_errors(vm_name: str) -> List[ShadowError]:
    """Check if VM actually exists and is running."""
    errors = []
    
    # Check 1: VM exists in virsh
    result = run_command(f"virsh list --all | grep {vm_name}")
    if result.returncode != 0:
        errors.append(ShadowError(
            error_type="vm_not_created",
            severity="critical",
            detected_by="virsh_list",
            evidence=f"VM {vm_name} not found in virsh list",
            fix_commands=[
                f"kcli create vm {vm_name} -i centos9stream",
                f"kcli start vm {vm_name}"
            ]
        ))
    
    # Check 2: VM is running (not just created)
    result = run_command(f"virsh list --state-running | grep {vm_name}")
    if result.returncode != 0:
        errors.append(ShadowError(
            error_type="vm_not_running",
            severity="critical",
            detected_by="virsh_state",
            evidence=f"VM {vm_name} exists but is not running",
            fix_commands=[f"virsh start {vm_name}"]
        ))
    
    # Check 3: VM has IP address
    result = run_command(f"kcli info vm {vm_name} | grep 'ip:'")
    if "N/A" in result.stdout or not result.stdout:
        errors.append(ShadowError(
            error_type="vm_no_ip",
            severity="warning",
            detected_by="kcli_info",
            evidence=f"VM {vm_name} has no IP address",
            fix_commands=[
                f"virsh net-dhcp-leases default | grep {vm_name}",
                f"kcli restart vm {vm_name}"
            ]
        ))
    
    return errors
```

### 4. OpenLineage DataQuality Facets

Integrate OpenLineage DataQuality facets to track validation results:

```python
class DataQualityAssertion:
    """Per OpenLineage spec: DataQualityAssertionsDatasetFacet."""
    assertion: str  # "vm_exists", "vm_running", "dns_resolves"
    success: bool
    column: Optional[str] = None
    details: Optional[str] = None

# Emit to OpenLineage/Marquez
emit_lineage_event(
    run_id=dag_run_id,
    dataset="vms",
    facets={
        "dataQuality": {
            "assertions": [
                {"assertion": "vm_exists", "success": True},
                {"assertion": "vm_running", "success": False, 
                 "details": "VM created but failed to start"},
                {"assertion": "dns_resolves", "success": False,
                 "details": "dig +short freeipa.example.com returned empty"}
            ]
        }
    }
)
```

### 5. Self-Correction with ModelRetry Pattern

When shadow errors are detected, use PydanticAI's ModelRetry pattern for self-correction:

```python
class ModelRetry(Exception):
    """Signal agent should retry with corrected parameters."""
    def __init__(
        self,
        message: str,
        corrected_params: Dict[str, Any],
        fix_commands: List[str],
        retry_count: int = 0,
        max_retries: int = 2,
    ):
        self.message = message
        self.corrected_params = corrected_params
        self.fix_commands = fix_commands
        self.retry_count = retry_count
        self.max_retries = max_retries

# Example Usage
async def validate_outcome(result: DAGResult) -> ObserverReport:
    """Validate DAG outcome and raise ModelRetry if shadow errors found."""
    shadow_errors = await detect_all_shadow_errors(result)
    
    if shadow_errors and retry_count < max_retries:
        # Attempt automatic correction
        fix_commands = [err.fix_commands for err in shadow_errors]
        raise ModelRetry(
            message=f"Found {len(shadow_errors)} shadow errors",
            corrected_params={"apply_fixes": True},
            fix_commands=flatten(fix_commands),
            retry_count=retry_count + 1
        )
    
    return ObserverReport(
        execution_status="success_with_errors" if shadow_errors else "success",
        shadow_errors=shadow_errors,
        concern_level=compute_concern_level(shadow_errors),
        recommendations=generate_recommendations(shadow_errors)
    )
```

### 6. Full Smart Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: User Intent                                             │
│   POST /orchestrator/intent                                      │
│   {"intent": "Deploy FreeIPA", "auto_approve": true}             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Manager Agent Planning                                  │
│   - Parse intent: "Deploy FreeIPA" → freeipa_deployment DAG     │
│   - Identify providers: ssh, kcli                                │
│   - Create SessionPlan                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Developer Agent Pre-Flight                              │
│   - Check libvirt connection ✅                                  │
│   - Verify centos9stream image ✅                                │
│   - Check DNS server ✅                                          │
│   - Query RAG for FreeIPA docs                                   │
│   - Confidence: 0.92 → PROCEED                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: DAG Execution (Airflow)                                 │
│   - Trigger freeipa_deployment                                   │
│   - Track with OpenLineage                                       │
│   - Emit DataQuality facets                                      │
│   - Result: SUCCESS ✅                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: Observer Agent Validation                               │
│   - Check VM exists: virsh list ✅                               │
│   - Check VM running: virsh list --state-running ❌              │
│   - Shadow Error Detected! VM created but not running            │
│   - Generate fix: virsh start freeipa                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 6: Self-Correction (ModelRetry)                            │
│   - Apply fix: virsh start freeipa                               │
│   - Re-check: VM running ✅                                      │
│   - Re-check: DNS resolves ✅                                    │
│   - Final Status: SUCCESS (with corrections applied)             │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

The Smart Pipeline is exposed via FastAPI endpoints:

### 1. Intent-Based Deployment
```bash
POST /orchestrator/intent
{
  "intent": "Deploy FreeIPA server",
  "params": {"vm_name": "freeipa"},
  "auto_approve": true,
  "auto_execute": true
}
```

### 2. DAG Pre-Flight Validation
```bash
POST /orchestrator/validate
{
  "dag_id": "freeipa_deployment",
  "conf": {"vm_name": "freeipa"}
}
```

### 3. Shadow Error Detection
```bash
GET /orchestrator/shadow-errors?dag_id=freeipa_deployment&run_id=abc123
```

### 4. Observer Agent Monitoring
```bash
POST /orchestrator/observe?dag_id=freeipa_deployment
```

## Implementation Files

| File | Purpose |
|------|---------|
| `ai-assistant/src/smart_pipeline.py` | Core Smart Pipeline orchestration |
| `ai-assistant/src/dag_validator.py` | Pre-flight DAG validation |
| `ai-assistant/src/agents/developer.py` | Developer Agent implementation |
| `ai-assistant/src/agents/observer.py` | Observer Agent implementation |
| `ai-assistant/src/feedback_loop.py` | Self-correction and retry logic |
| `ai-assistant/src/project_registry.py` | Project-aware DAG creation |

## Consequences

### Positive

1. **No More Silent Failures**: Shadow errors detected immediately after DAG completion
2. **Higher Confidence**: Pre-flight validation prevents failed runs
3. **Self-Healing**: ModelRetry pattern enables automatic correction
4. **Better UX**: Users know actual infrastructure state, not just DAG status
5. **Traceability**: OpenLineage DataQuality facets provide audit trail
6. **Cost Savings**: Prevents wasted time debugging downstream failures caused by upstream shadow errors

### Negative

1. **Increased Complexity**: More validation code to maintain
2. **Execution Time**: Pre-flight and post-flight validation adds overhead (typically 10-30 seconds)
3. **False Positives**: Shadow error detection may flag issues that aren't actually problems
4. **API Dependencies**: Requires Airflow API, Marquez API, and host SSH access

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Validation overhead too high | Make validation optional with `skip_validation=true` flag |
| False positive shadow errors | Tune detection thresholds, allow user overrides |
| Self-correction breaks things | Limit to safe operations, require approval for destructive fixes |
| API availability issues | Graceful degradation: skip validation if APIs unavailable |

## Validation Scope

The Smart Pipeline validates common infrastructure patterns:

| Infrastructure Type | Validation Checks |
|---------------------|-------------------|
| **VM Deployment** | VM exists, VM running, IP assigned, SSH accessible |
| **DNS Records** | Record exists, resolves correctly, matches expected IP |
| **Certificates** | Cert file exists, valid dates, correct CN/SAN, trusted CA |
| **FreeIPA** | Server running, admin password works, realm configured |
| **Keycloak** | Service running, admin console accessible, realm exists |
| **Step-CA** | CA running, root cert valid, provisioner configured |

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Pre-flight validation | 5-15s | Parallel checks, can be cached |
| DAG execution | Varies | No overhead (existing Airflow) |
| Shadow error detection | 5-20s | Depends on number of checks |
| Self-correction | 10-60s | Depends on fix complexity |
| **Total overhead** | **20-95s** | Acceptable for infrastructure tasks |

## Testing Strategy

Smart Pipeline is validated via E2E testing (ADR-0067):

```yaml
# .github/workflows/e2e-test.yml
- name: Deploy FreeIPA via Smart Pipeline
  run: |
    curl -X POST http://localhost:8080/orchestrator/intent \
      -d '{"intent": "Deploy FreeIPA", "auto_execute": true}'
    
- name: Validate Shadow Error Detection
  run: |
    # Inject failure: stop VM after creation
    virsh destroy freeipa
    
    # Observer should detect shadow error
    response=$(curl http://localhost:8080/orchestrator/observe?dag_id=freeipa_deployment)
    if ! echo "$response" | grep "vm_not_running"; then
      echo "FAIL: Shadow error not detected"
      exit 1
    fi
```

## Related ADRs

- **[ADR-0045](adr-0045-airflow-dag-development-standards.md)**: DAG Development Standards
- **[ADR-0046](adr-0046-dag-validation-pipeline-and-host-execution.md)**: DAG Validation Pipeline
- **[ADR-0049](adr-0049-multi-agent-llm-memory-architecture.md)**: Multi-Agent LLM Memory Architecture
- **[ADR-0063](adr-0063-pydanticai-core-agent-orchestrator.md)**: PydanticAI Core Agent Orchestrator
- **[ADR-0067](adr-0067-self-hosted-runner-e2e-testing.md)**: E2E Testing with Smart Pipeline Validation

## References

- OpenLineage DataQuality Facets: https://openlineage.io/spec/facets/1-0-0/DataQualityAssertionsDatasetFacet.json
- PydanticAI ModelRetry Pattern: https://ai.pydantic.dev/validation/#model-retry
- Marquez API: https://marquezproject.github.io/marquez/openapi.html

---

*Status: Implemented*  
*Last Updated: 2025-12-08*  
*Implementation: `ai-assistant/src/smart_pipeline.py`, `ai-assistant/src/agents/observer.py`*
