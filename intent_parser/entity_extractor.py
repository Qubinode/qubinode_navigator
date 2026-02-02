"""
Category-aware entity and parameter extraction from natural language.

Uses regex patterns to extract structured parameters from user input
based on the classified intent category.
"""

import re
from typing import Dict, Any

from .models import IntentCategory


def extract(text: str, category: IntentCategory) -> Dict[str, Any]:
    """
    Extract entities and parameters from text based on intent category.

    Returns a dict of extracted parameter names to values.
    """
    # Category-specific extraction first
    extractors = {
        IntentCategory.VM_LIST: _extract_vm_list,
        IntentCategory.VM_INFO: _extract_vm_params,
        IntentCategory.VM_CREATE: _extract_vm_create,
        IntentCategory.VM_DELETE: _extract_vm_params,
        IntentCategory.VM_PREFLIGHT: _extract_vm_create,
        IntentCategory.DAG_LIST: _extract_noop,
        IntentCategory.DAG_INFO: _extract_dag_params,
        IntentCategory.DAG_TRIGGER: _extract_dag_trigger,
        IntentCategory.RAG_QUERY: _extract_rag_query,
        IntentCategory.RAG_INGEST: _extract_rag_ingest,
        IntentCategory.RAG_STATS: _extract_noop,
        IntentCategory.SYSTEM_STATUS: _extract_noop,
        IntentCategory.SYSTEM_INFO: _extract_noop,
        IntentCategory.TROUBLESHOOT_DIAGNOSE: _extract_troubleshoot,
        IntentCategory.TROUBLESHOOT_HISTORY: _extract_troubleshoot_history,
        IntentCategory.TROUBLESHOOT_LOG: _extract_troubleshoot_log,
        IntentCategory.LINEAGE_DAG: _extract_lineage,
        IntentCategory.LINEAGE_BLAST_RADIUS: _extract_blast_radius,
        IntentCategory.HELP: _extract_noop,
        IntentCategory.UNKNOWN: _extract_noop,
    }

    extractor = extractors.get(category, _extract_noop)
    params = extractor(text)

    # Explicit key=value pairs override category extraction
    kv_params = _extract_key_value_pairs(text)
    params.update(kv_params)

    return params


def _extract_key_value_pairs(text: str) -> Dict[str, Any]:
    """Extract explicit key=value pairs from text."""
    params = {}
    # Match: key=value or key="value with spaces"
    for match in re.finditer(r'\b(\w+)\s*=\s*(?:"([^"]+)"|(\S+))', text):
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else match.group(3)
        # Try to convert numeric values
        params[key] = _try_numeric(value)
    return params


def _try_numeric(value: str) -> Any:
    """Try to convert a string to int or float."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _extract_noop(text: str) -> Dict[str, Any]:
    return {}


def _extract_vm_list(text: str) -> Dict[str, Any]:
    return {}


def _extract_vm_params(text: str) -> Dict[str, Any]:
    """Extract VM name from text."""
    params = {}

    # "vm named X" / "vm called X"
    m = re.search(
        r"\bvm\s+(?:named|called)\s+[\"']?([a-zA-Z][a-zA-Z0-9._-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        params["name"] = m.group(1).strip("\"'")
        return params

    # "info/details/status/delete vm <name>"
    m = re.search(
        r"\b(?:info|details?|status|describe|delete|remove|destroy|terminate)\s+" r"(?:about\s+|for\s+|of\s+)?(?:the\s+)?(?:vm|virtual\s+machine)\s+" r"[\"']?([a-zA-Z][a-zA-Z0-9._-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        params["name"] = m.group(1).strip("\"'")
        return params

    # "vm info/status/details <name>" pattern
    m = re.search(
        r"\bvm\s+(?:info|details?|status)\s+[\"']?([a-zA-Z][a-zA-Z0-9._-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        params["name"] = m.group(1).strip("\"'")
        return params

    # "<action> <name> vm"
    m = re.search(
        r"\b(?:delete|remove|destroy|terminate)\s+[\"']?([a-zA-Z][a-zA-Z0-9._-]*)[\"']?\s+vm\b",
        text,
        re.I,
    )
    if m:
        params["name"] = m.group(1).strip("\"'")
        return params

    # Last word that looks like a VM name after "vm"
    m = re.search(
        r"\bvm\s+[\"']?([a-zA-Z][a-zA-Z0-9._-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        name = m.group(1).strip("\"'")
        # Filter out common non-name words
        if name.lower() not in {
            "info",
            "details",
            "status",
            "list",
            "create",
            "delete",
            "named",
            "called",
            "is",
            "the",
            "a",
            "an",
            "with",
            "name",
            "image",
            "memory",
            "cpus",
            "disk",
        }:
            params["name"] = name

    return params


def _extract_vm_create(text: str) -> Dict[str, Any]:
    """Extract VM creation parameters."""
    params = _extract_vm_params(text)

    # Image: "with image X" / "using X image" / "image=X"
    m = re.search(
        r"\b(?:with\s+)?image\s+[\"']?([a-zA-Z][a-zA-Z0-9._-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        params["image"] = m.group(1)

    m = re.search(
        r"\busing\s+[\"']?([a-zA-Z][a-zA-Z0-9._-]*)[\"']?\s+image\b",
        text,
        re.I,
    )
    if m:
        params["image"] = m.group(1)

    # Memory: "4GB RAM" / "4096MB memory" / "4g memory" / "memory 4096"
    m = re.search(r"\b(\d+)\s*(?:gb|g)\s*(?:ram|memory|mem)?\b", text, re.I)
    if m:
        params["memory"] = int(m.group(1)) * 1024  # Convert GB to MB

    m = re.search(r"\b(\d{3,})\s*(?:mb)?\s*(?:ram|memory|mem)\b", text, re.I)
    if m:
        params["memory"] = int(m.group(1))

    m = re.search(r"\bmemory\s+(\d+)\b", text, re.I)
    if m and "memory" not in params:
        val = int(m.group(1))
        params["memory"] = val if val >= 512 else val * 1024

    # CPUs: "2 cpus" / "4 cores" / "cpus 2"
    m = re.search(r"\b(\d+)\s*(?:cpus?|cores?|vcpus?)\b", text, re.I)
    if m:
        params["cpus"] = int(m.group(1))

    m = re.search(r"\bcpus?\s+(\d+)\b", text, re.I)
    if m and "cpus" not in params:
        params["cpus"] = int(m.group(1))

    # Disk: "50GB disk" / "disk 50" / "50g disk"
    m = re.search(r"\b(\d+)\s*(?:gb|g)?\s*disk\b", text, re.I)
    if m:
        params["disk_size"] = int(m.group(1))

    m = re.search(r"\bdisk\s*(?:size)?\s+(\d+)\b", text, re.I)
    if m and "disk_size" not in params:
        params["disk_size"] = int(m.group(1))

    return params


def _extract_dag_params(text: str) -> Dict[str, Any]:
    """Extract DAG ID from text."""
    params = {}

    _skip_words = {
        "info",
        "details",
        "status",
        "list",
        "trigger",
        "run",
        "named",
        "called",
        "the",
        "a",
        "execute",
        "start",
        "describe",
    }

    # "dag info/details/status <dag_id>" - command word then dag_id
    m = re.search(
        r"\b(?:dag|workflow)\s+(?:info|details?|status|describe)\s+" r"[\"']?([a-zA-Z][a-zA-Z0-9_-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        dag_id = m.group(1).strip("\"'")
        if dag_id.lower() not in _skip_words:
            params["dag_id"] = dag_id
            return params

    # "info/details about dag <dag_id>"
    m = re.search(
        r"\b(?:info|details?|describe)\s+(?:about\s+|for\s+|of\s+)?(?:dag|workflow)\s+" r"[\"']?([a-zA-Z][a-zA-Z0-9_-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        dag_id = m.group(1).strip("\"'")
        if dag_id.lower() not in _skip_words:
            params["dag_id"] = dag_id
            return params

    # "dag <dag_id>" / "dag named <dag_id>" / "workflow <dag_id>"
    m = re.search(
        r"\b(?:dag|workflow)\s+(?:named|called|id)?\s*[\"']?([a-zA-Z][a-zA-Z0-9_-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        dag_id = m.group(1).strip("\"'")
        if dag_id.lower() not in _skip_words:
            params["dag_id"] = dag_id

    return params


def _extract_dag_trigger(text: str) -> Dict[str, Any]:
    """Extract DAG trigger parameters."""
    params = {}

    _skip_words = {"dag", "workflow", "the", "a"}

    # "trigger/run/execute dag <dag_id>"
    m = re.search(
        r"\b(?:trigger|run|execute|start)\s+(?:the\s+)?(?:dag|workflow)\s+" r"[\"']?([a-zA-Z][a-zA-Z0-9_-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        dag_id = m.group(1).strip("\"'")
        if dag_id.lower() not in _skip_words:
            params["dag_id"] = dag_id

    # "trigger <dag_id>" (no "dag" keyword)
    if "dag_id" not in params:
        m = re.search(
            r"\b(?:trigger|run|execute|start)\s+(?:the\s+)?[\"']?([a-zA-Z][a-zA-Z0-9_-]*)[\"']?",
            text,
            re.I,
        )
        if m:
            dag_id = m.group(1).strip("\"'")
            if dag_id.lower() not in _skip_words:
                params["dag_id"] = dag_id

    # "trigger <name> dag"
    if "dag_id" not in params:
        m = re.search(
            r"\b(?:trigger|run|execute|start)\s+[\"']?([a-zA-Z][a-zA-Z0-9_-]*)[\"']?\s+(?:dag|workflow)\b",
            text,
            re.I,
        )
        if m:
            params["dag_id"] = m.group(1).strip("\"'")

    # Try to extract JSON conf: "with config {...}" or "conf={...}"
    m = re.search(r"\b(?:conf|config|configuration)\s*=?\s*(\{[^}]+\})", text, re.I)
    if m:
        import json

        try:
            params["conf"] = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    return params


def _extract_rag_query(text: str) -> Dict[str, Any]:
    """Extract RAG query parameters."""
    params = {}

    # The query is often the main text after removing the command prefix
    cleaned = re.sub(
        r"^(?:search|query|find|lookup)\s+(?:the\s+)?(?:rag|knowledge\s+base|docs?|documentation)\s*(?:for|about)?\s*",
        "",
        text,
        flags=re.I,
    ).strip()

    if cleaned and cleaned != text.strip():
        params["query"] = cleaned
    else:
        # "how do I ..." style questions become the query
        m = re.search(r"\bhow\s+(?:do|to|can)\s+(?:i|we)\s+(.+)", text, re.I)
        if m:
            params["query"] = m.group(1).strip("?").strip()

    # doc_types filter
    m = re.search(r"\b(?:type|doc_type)\s*=\s*\[?([^\]]+)\]?", text, re.I)
    if m:
        types = [t.strip().strip("'\"") for t in m.group(1).split(",")]
        params["doc_types"] = types

    # limit
    m = re.search(r"\blimit\s*=?\s*(\d+)\b", text, re.I)
    if m:
        params["limit"] = int(m.group(1))

    # threshold
    m = re.search(r"\bthreshold\s*=?\s*([\d.]+)\b", text, re.I)
    if m:
        params["threshold"] = float(m.group(1))

    return params


def _extract_rag_ingest(text: str) -> Dict[str, Any]:
    """Extract RAG ingest parameters."""
    params = {}

    # doc_type
    m = re.search(
        r"\b(?:type|doc_type)\s*=?\s*[\"']?(\w+)[\"']?",
        text,
        re.I,
    )
    if m:
        params["doc_type"] = m.group(1)

    # source path
    m = re.search(r"\bsource\s*=?\s*[\"']?(/[^\s\"']+)[\"']?", text, re.I)
    if m:
        params["source"] = m.group(1)

    return params


def _extract_troubleshoot(text: str) -> Dict[str, Any]:
    """Extract troubleshooting/diagnostic parameters."""
    params = {}

    # Component detection - ordered from most specific to most generic
    # to prevent generic keywords from matching first
    components = [
        ("freeipa", ["freeipa", "ipa-server", "idm", "identity management"]),
        ("openshift", ["openshift", "ocp", "kubernetes", "k8s"]),
        ("vm", ["vm", "virtual machine", "virsh", "kcli"]),
        ("dag", ["dag", "airflow", "workflow"]),
        ("storage", ["disk", "storage", "space", "full"]),
        ("network", ["dns", "network", "connect", "resolve", "hostname"]),
    ]

    text_lower = text.lower()
    for component, keywords in components:
        if any(kw in text_lower for kw in keywords):
            params["component"] = component
            break

    # Extract symptom - the main description after the command word
    cleaned = re.sub(r"^(?:diagnose|troubleshoot|debug|fix)\s+", "", text, flags=re.I).strip()
    if cleaned and cleaned != text.strip():
        params["symptom"] = cleaned

    # Extract quoted error messages
    m = re.search(r'["\']([^"\']+)["\']', text)
    if m:
        params["error_message"] = m.group(1)

    # Extract resource names
    m = re.search(
        r"\b(?:vm|dag|resource)\s+[\"']?([a-zA-Z][a-zA-Z0-9._-]*)[\"']?",
        text,
        re.I,
    )
    if m:
        name = m.group(1)
        if name.lower() not in {"is", "not", "the", "a", "named", "called"}:
            params["affected_resource"] = name

    return params


def _extract_troubleshoot_history(text: str) -> Dict[str, Any]:
    """Extract troubleshoot history query parameters."""
    params = {}

    # error_pattern from quoted text or after "for"
    m = re.search(r'["\']([^"\']+)["\']', text)
    if m:
        params["error_pattern"] = m.group(1)
    else:
        m = re.search(r"\bfor\s+(.+?)(?:\s+(?:in|from|limit)\b|$)", text, re.I)
        if m:
            params["error_pattern"] = m.group(1).strip()

    # component
    m = re.search(r"\bcomponent\s*=?\s*[\"']?(\w+)[\"']?", text, re.I)
    if m:
        params["component"] = m.group(1)

    # only_successful
    if re.search(r"\b(?:successful|success|solved|fixed)\s+only\b", text, re.I) or re.search(r"\bonly\s+(?:successful|success|solved|fixed)\b", text, re.I):
        params["only_successful"] = True

    return params


def _extract_troubleshoot_log(text: str) -> Dict[str, Any]:
    """Extract parameters for logging a troubleshooting attempt."""
    params = {}

    # result: success/failed/partial
    if re.search(r"\bsuccess(?:ful)?\b", text, re.I):
        params["result"] = "success"
    elif re.search(r"\bfail(?:ed|ure)?\b", text, re.I):
        params["result"] = "failed"
    elif re.search(r"\bpartial\b", text, re.I):
        params["result"] = "partial"

    return params


def _extract_lineage(text: str) -> Dict[str, Any]:
    """Extract lineage query parameters."""
    params = _extract_dag_params(text)

    # depth
    m = re.search(r"\bdepth\s*=?\s*(\d+)\b", text, re.I)
    if m:
        params["depth"] = int(m.group(1))

    return params


def _extract_blast_radius(text: str) -> Dict[str, Any]:
    """Extract blast radius parameters."""
    params = _extract_dag_params(text)

    # task_id
    m = re.search(r"\btask\s+(?:id\s+)?[\"']?([a-zA-Z][a-zA-Z0-9_-]*)[\"']?", text, re.I)
    if m:
        task_id = m.group(1)
        if task_id.lower() not in {"id", "the", "a"}:
            params["task_id"] = task_id

    return params
