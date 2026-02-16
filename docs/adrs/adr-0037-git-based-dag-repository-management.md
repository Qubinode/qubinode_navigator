______________________________________________________________________

## layout: default title: ADR-0037 Git-Based DAG Repository parent: Configuration & Automation grand_parent: Architectural Decision Records nav_order: 37

# ADR-0037: Git-Based DAG Repository Management

**Status:** Proposed
**Date:** 2025-11-15
**Decision Makers:** Platform Team, DevOps Team
**Related ADRs:** ADR-0036 (Airflow Integration)

## Context and Problem Statement

Users need to deploy and manage Airflow DAGs from their own Git repositories. Currently, users must manually copy DAG files to the Airflow directory, which is error-prone and doesn't support:

- Automatic synchronization with Git repositories
- Version control and rollback
- Webhook-based instant updates
- Multi-repository management
- Secure credential handling

**Key Requirements:**

- Support multiple Git repositories (GitHub, GitLab, Bitbucket)
- Automatic DAG synchronization
- Secure credential management
- DAG validation before deployment
- Webhook integration for instant updates
- Multi-repository namespace isolation

## Decision Drivers

- Enable GitOps workflow for DAG management
- Reduce manual deployment errors
- Support team collaboration through Git
- Enable CI/CD integration
- Maintain security and access control
- Support both public and private repositories

## Considered Options

1. **Git-Sync Sidecar Pattern** - Dedicated container for Git synchronization
1. **Built-in Git Client** - Integrate Git directly into AI Assistant
1. **Manual Git Operations** - Users manage Git manually
1. **Airflow Git-Sync Plugin** - Use existing Airflow plugin
1. **Hybrid Approach** - Combine AI Assistant integration with Git-Sync

## Decision Outcome

**Chosen option:** Hybrid Approach - AI Assistant manages Git repositories with optional Git-Sync sidecar

**Justification:**

- Provides both automated (Git-Sync) and managed (AI Assistant) approaches
- Leverages existing Git-Sync for Kubernetes deployments
- Adds intelligent layer for validation, security, and user experience
- Supports webhook integration for instant updates
- Enables chat-based repository management

### Implementation Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    AI Assistant Container                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Git Repository Manager                                │  │
│  │  - Add/remove repositories                             │  │
│  │  - Credential management                               │  │
│  │  - DAG validation                                      │  │
│  │  - Webhook handling                                    │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│              Git-Sync Sidecar (Optional)                      │
│  - Automatic polling (60s interval)                           │
│  - Multi-repository support                                   │
│  - Branch/tag selection                                       │
│  - Kubernetes-native                                          │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                  Shared DAG Volume                            │
│  /opt/airflow/dags/                                           │
│  ├── repo1/                                                   │
│  ├── repo2/                                                   │
│  └── repo3/                                                   │
└──────────────────────────────────────────────────────────────┘
```

### Repository Configuration

```yaml
# airflow-repos.yaml
repositories:
  - name: company-workflows
    url: https://github.com/company/workflows
    branch: main
    auth_type: ssh_key
    sync_interval: 60s
    namespace: company
    validation:
      enabled: true
      security_scan: true

  - name: community-workflows
    url: https://github.com/Qubinode/airflow-dags
    branch: main
    auth_type: public
    sync_interval: 300s
    namespace: community
    validation:
      enabled: true
      security_scan: true

  - name: personal-workflows
    url: https://github.com/user/my-dags
    branch: develop
    auth_type: oauth_token
    sync_interval: 30s
    namespace: personal
    validation:
      enabled: true
      security_scan: true
      auto_deploy: false  # Require manual approval
```

## Positive Consequences

- **GitOps Workflow**: Standard Git workflow for DAG management
- **Version Control**: Full Git history for all DAGs
- **Collaboration**: Teams can collaborate through Pull Requests
- **Automation**: Webhook-based instant updates
- **Security**: Centralized credential management
- **Validation**: Automatic DAG validation before deployment
- **Multi-Repo**: Support multiple repositories with namespace isolation
- **Rollback**: Easy rollback to previous versions
- **Audit Trail**: Complete history of all changes

## Negative Consequences

- **Complexity**: Additional components to manage
- **Credentials**: Secure storage and rotation required
- **Network**: Requires network access to Git providers
- **Sync Delays**: Polling-based sync has latency (mitigated by webhooks)
- **Storage**: Multiple repositories increase storage requirements
- **Conflicts**: Potential namespace conflicts between repositories

## Risks and Mitigations

| Risk                      | Impact   | Mitigation                                        |
| ------------------------- | -------- | ------------------------------------------------- |
| Credential exposure       | Critical | Use encrypted storage (Vault/Airflow Connections) |
| Malicious DAG injection   | Critical | Mandatory validation and security scanning        |
| Repository unavailability | High     | Cache last known good state, retry logic          |
| Sync conflicts            | Medium   | Namespace isolation, clear precedence rules       |
| Webhook failures          | Medium   | Fallback to polling, retry mechanism              |
| Large repository size     | Medium   | Sparse checkout, shallow clone                    |

## Alternatives Considered

### Git-Sync Sidecar Only

- **Pros:** Simple, Kubernetes-native, proven solution
- **Cons:** No validation, no UI, limited credential management
- **Verdict:** Rejected - lacks intelligence and user experience

### Built-in Git Client Only

- **Pros:** Single component, full control
- **Cons:** Reinventing wheel, more maintenance
- **Verdict:** Rejected - Git-Sync is battle-tested

### Manual Git Operations

- **Pros:** Simple, no automation needed
- **Cons:** Error-prone, no automation, poor UX
- **Verdict:** Rejected - doesn't meet automation requirements

### Airflow Git-Sync Plugin

- **Pros:** Native Airflow integration
- **Cons:** Limited features, no validation layer
- **Verdict:** Rejected - insufficient for our needs

## Implementation Plan

### Phase 1: Core Git Integration (Weeks 1-2)

- [ ] Git repository manager service
- [ ] Credential storage (Airflow Connections)
- [ ] Basic clone and sync functionality
- [ ] Repository configuration file support
- [ ] Namespace isolation

### Phase 2: Validation & Security (Weeks 3-4)

- [ ] DAG syntax validation
- [ ] Security scanning (hardcoded credentials, dangerous operations)
- [ ] Dependency checking
- [ ] Pre-deployment testing
- [ ] Validation reporting

### Phase 3: Webhook Integration (Week 5)

- [ ] Webhook receiver endpoint
- [ ] GitHub webhook integration
- [ ] GitLab webhook integration
- [ ] Bitbucket webhook integration
- [ ] Instant sync on push events

### Phase 4: User Interface (Week 6)

- [ ] Repository management UI
- [ ] Add/remove repositories
- [ ] Sync status monitoring
- [ ] Validation results display
- [ ] Chat interface integration

### Phase 5: Advanced Features (Weeks 7-8)

- [ ] Multi-repository support
- [ ] Version control and rollback
- [ ] A/B testing capability
- [ ] Performance monitoring
- [ ] Analytics and reporting

## Success Metrics

| Metric                  | Target            | Measurement           |
| ----------------------- | ----------------- | --------------------- |
| Repository sync time    | \<30 seconds      | Webhook latency       |
| Validation success rate | >95%              | Pre-deployment checks |
| Security scan coverage  | 100%              | All DAGs scanned      |
| User adoption           | 80% use Git repos | Usage analytics       |
| Sync reliability        | >99.5% uptime     | Monitoring            |
| Credential security     | Zero exposures    | Security audits       |

## Security Considerations

### Credential Management

```python
# Secure credential storage
class SecureCredentialStore:
    def store_credential(self, repo_url: str, credential_type: str, value: str):
        """
        Store credentials in Airflow Connections (encrypted)
        """
        connection = Connection(
            conn_id=f"git_{hash(repo_url)}",
            conn_type="git",
            login=credential_type,
            password=encrypt(value),  # Fernet encryption
            extra=json.dumps({"repo_url": repo_url})
        )
        session.add(connection)
        session.commit()
```

### DAG Validation

```python
# Security scanning before deployment
class DAGSecurityScanner:
    def scan(self, dag_file: str) -> dict:
        """
        Scan DAG for security issues
        """
        issues = []

        # Check for hardcoded credentials
        if self.has_hardcoded_credentials(dag_file):
            issues.append({
                'severity': 'critical',
                'type': 'hardcoded_credentials',
                'message': 'Found hardcoded credentials'
            })

        # Check for dangerous operations
        if self.has_dangerous_operations(dag_file):
            issues.append({
                'severity': 'high',
                'type': 'dangerous_operation',
                'message': 'Found potentially dangerous operations'
            })

        return {
            'passed': len(issues) == 0,
            'issues': issues
        }
```

## Chat Interface Integration

```
User: "Add my workflows repository"
AI: "I'll help you add a Git repository. Please provide:
     1. Repository URL
     2. Branch (default: main)
     3. Authentication type (ssh_key, oauth_token, or public)

     Example: https://github.com/youruser/workflows"

User: "https://github.com/mycompany/dags, branch: develop, use SSH key"
AI: "Adding repository...
     ✅ Repository validated
     ✅ SSH key configured
     ✅ Initial sync complete
     ✅ Found 5 DAGs

     All DAGs passed validation and are now available in Airflow!
     Namespace: mycompany

     Would you like to enable automatic sync on push events?"

User: "Yes"
AI: "✅ Webhook configured
     Your DAGs will now update automatically when you push to GitHub.
     Webhook URL: https://your-domain.com/webhooks/github"
```

## Configuration Examples

### Docker Compose with Git-Sync

```yaml
version: '3.8'

services:
  airflow-webserver:
    image: apache/airflow:2.8.0
    volumes:
      - dags:/opt/airflow/dags
    depends_on:
      - git-sync

  git-sync:
    image: k8s.gcr.io/git-sync:v3.6.3
    environment:
      GIT_SYNC_REPO: https://github.com/user/workflows
      GIT_SYNC_BRANCH: main
      GIT_SYNC_ROOT: /git
      GIT_SYNC_DEST: dags
      GIT_SYNC_PERIOD: 60s
      GIT_SYNC_ONE_TIME: false
    volumes:
      - dags:/git
    secrets:
      - git_credentials

volumes:
  dags:

secrets:
  git_credentials:
    file: ./git-credentials
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: airflow-with-git-sync
spec:
  template:
    spec:
      containers:
      - name: airflow-webserver
        image: apache/airflow:2.8.0
        volumeMounts:
        - name: dags
          mountPath: /opt/airflow/dags

      - name: git-sync
        image: k8s.gcr.io/git-sync:v3.6.3
        env:
        - name: GIT_SYNC_REPO
          value: "https://github.com/user/workflows"
        - name: GIT_SYNC_BRANCH
          value: "main"
        - name: GIT_SYNC_PERIOD
          value: "60s"
        volumeMounts:
        - name: dags
          mountPath: /git

      volumes:
      - name: dags
        emptyDir: {}
```

## References

- [Git-Sync Documentation](https://github.com/kubernetes/git-sync)
- [Airflow Git-Sync Guide](https://airflow.apache.org/docs/helm-chart/stable/manage-dags-files.html#mounting-dags-using-git-sync-sidecar)
- [GitHub Webhooks](https://docs.github.com/en/developers/webhooks-and-events/webhooks)
- [GitLab Webhooks](https://docs.gitlab.com/ee/user/project/integrations/webhooks.html)
- ADR-0036: Apache Airflow Workflow Orchestration Integration
- [DAG Deployment Workflows](../reference/airflow-dag-deployment-workflows.md)

## Decision Log

- **2025-11-15:** Initial proposal created
- **Status:** Awaiting team review and approval
- **Next Review:** 2025-11-22

______________________________________________________________________

**This ADR enables GitOps workflow for Airflow DAGs, making deployment as simple as `git push`! 🚀**
