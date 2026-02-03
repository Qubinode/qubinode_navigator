"""
Dynamic DAG registry for intent classification and entity extraction.

Scans airflow/dags/ at import time and builds:
1. Service keywords for the classifier (deploy <service> -> DAG_TRIGGER)
2. Service-to-DAG-ID mapping for the entity extractor

This means adding a new DAG file with proper tags/description automatically
makes it discoverable by the intent parser — no code changes needed.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("intent-parser.dag-registry")

# Words that are too generic to use as service keywords
_GENERIC_WORDS = frozenset({
    "qubinode", "infrastructure", "deployment", "deploy", "kcli-pipelines",
    "ocp4-disconnected-helper", "disconnected", "utility", "workflow",
    "master", "ci", "openlineage", "adr-0054", "adr-0055", "adr-0049",
    "enterprise", "kcli", "pipelines",
})

# Minimum tag/keyword length to avoid noise
_MIN_KEYWORD_LEN = 2


def _find_dags_path() -> Path:
    """Locate the airflow/dags directory."""
    # Try multiple known locations
    candidates = [
        os.getenv("AIRFLOW_DAGS_PATH", ""),
        "/app/airflow/dags",  # Inside container
        str(Path(__file__).parent.parent / "airflow" / "dags"),  # Relative to repo root
        "/opt/qubinode_navigator/airflow/dags",
    ]
    for c in candidates:
        if c and Path(c).is_dir():
            return Path(c)
    return Path("/app/airflow/dags")  # Default, may not exist


def _parse_dag_metadata(file_path: Path) -> dict:
    """Parse a DAG file and extract dag_id, tags, and description."""
    try:
        content = file_path.read_text()
    except Exception:
        return {}

    dag_id_m = re.search(r'DAG\s*\(\s*["\']([^"\']+)["\']', content)
    if not dag_id_m:
        dag_id_m = re.search(r'dag_id\s*=\s*["\']([^"\']+)["\']', content)
    if not dag_id_m:
        return {}

    dag_id = dag_id_m.group(1)

    tags_m = re.search(r"tags\s*=\s*\[([^\]]+)\]", content)
    tags = []
    if tags_m:
        tags = re.findall(r'["\']([^"\']+)["\']', tags_m.group(1))

    desc_m = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
    description = desc_m.group(1) if desc_m else ""

    return {
        "dag_id": dag_id,
        "tags": tags,
        "description": description,
    }


def scan_dags() -> List[dict]:
    """Scan all DAG files and return metadata list."""
    dags_path = _find_dags_path()
    if not dags_path.exists():
        logger.warning(f"DAGs path not found: {dags_path}")
        return []

    skip_files = {"dag_factory.py", "dag_helpers.py", "dag_loader.py", "dag_logging_mixin.py"}
    results = []

    for dag_file in sorted(dags_path.glob("*.py")):
        if dag_file.name.startswith("_") or dag_file.name in skip_files:
            continue
        meta = _parse_dag_metadata(dag_file)
        if meta:
            results.append(meta)

    logger.info(f"DAG registry scanned {len(results)} DAGs from {dags_path}")
    return results


def _extract_service_keywords(dag: dict) -> Set[str]:
    """
    Extract meaningful service keywords from a DAG's tags and description.

    These are words specific enough to identify this DAG when a user says
    "deploy <keyword>".
    """
    keywords = set()

    # From tags
    for tag in dag.get("tags", []):
        tag_clean = tag.lower().strip()
        if tag_clean not in _GENERIC_WORDS and len(tag_clean) >= _MIN_KEYWORD_LEN:
            keywords.add(tag_clean)

    # From dag_id: split on _ and take meaningful parts
    dag_id = dag.get("dag_id", "")
    for part in dag_id.lower().split("_"):
        if part not in _GENERIC_WORDS and len(part) >= 3 and part not in {"the", "and", "for"}:
            keywords.add(part)

    return keywords


def build_service_dag_map() -> Dict[str, str]:
    """
    Build a keyword -> dag_id mapping from all discovered DAGs.

    Example output:
        {
            "freeipa": "freeipa_deployment",
            "identity": "freeipa_deployment",
            "harbor": "harbor_deployment",
            "vyos": "vyos_router_deployment",
            "router": "vyos_router_deployment",
            ...
        }

    Priority: keywords from dag_id parts take precedence over tag-only keywords.
    This ensures "freeipa" maps to freeipa_deployment (not dns_management which
    merely has "freeipa" as a tag).
    """
    dags = scan_dags()
    mapping: Dict[str, str] = {}

    # Two passes: first dag_id-derived keywords (strong signal), then tag keywords
    # Pass 1: keywords that appear in the dag_id itself
    for dag in sorted(dags, key=lambda d: d["dag_id"]):
        dag_id = dag["dag_id"]
        dag_id_parts = set()
        for part in dag_id.lower().split("_"):
            if part not in _GENERIC_WORDS and len(part) >= 3 and part not in {"the", "and", "for"}:
                dag_id_parts.add(part)

        for kw in dag_id_parts:
            if kw not in mapping:
                mapping[kw] = dag_id

    # Pass 2: keywords from tags (only if not already claimed by a dag_id match)
    for dag in sorted(dags, key=lambda d: d["dag_id"]):
        dag_id = dag["dag_id"]
        for tag in dag.get("tags", []):
            tag_clean = tag.lower().strip()
            if tag_clean not in _GENERIC_WORDS and len(tag_clean) >= _MIN_KEYWORD_LEN:
                if tag_clean not in mapping:
                    mapping[tag_clean] = dag_id

    logger.info(f"DAG registry built {len(mapping)} service keyword mappings")
    return mapping


def build_deploy_keywords() -> List[str]:
    """
    Build a list of service keywords that should trigger DAG_TRIGGER
    when preceded by "deploy".

    Used by the classifier to add dynamic keywords like:
        _kw("deploy", "freeipa")
        _kw("deploy", "harbor")
        _kw("deploy", "vyos")
    """
    service_map = build_service_dag_map()
    # Return unique keywords (some may map to the same DAG)
    return sorted(service_map.keys())


# Module-level cache (built once at import time)
_service_dag_map: Dict[str, str] = {}
_deploy_keywords: List[str] = []


def get_service_dag_map() -> Dict[str, str]:
    """Get the cached service-to-DAG mapping."""
    global _service_dag_map
    if not _service_dag_map:
        _service_dag_map = build_service_dag_map()
    return _service_dag_map


def get_deploy_keywords() -> List[str]:
    """Get the cached list of deploy keywords."""
    global _deploy_keywords
    if not _deploy_keywords:
        _deploy_keywords = build_deploy_keywords()
    return _deploy_keywords
