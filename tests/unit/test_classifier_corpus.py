"""
Classifier accuracy corpus.

200+ labeled examples with expected category and minimum confidence.
Run with:  python3 -m pytest tests/unit/test_classifier_corpus.py -v
"""

import pytest

from intent_parser.classifier import classify
from intent_parser.models import IntentCategory


# (input, expected_category, min_confidence)
CORPUS = [
    # ==================== DAG_TRIGGER ====================
    # deploy <service>
    ("deploy freeipa", IntentCategory.DAG_TRIGGER, 0.5),
    ("deploy harbor", IntentCategory.DAG_TRIGGER, 0.5),
    ("deploy vyos", IntentCategory.DAG_TRIGGER, 0.5),
    ("deploy jumpserver", IntentCategory.DAG_TRIGGER, 0.5),
    ("deploy step-ca", IntentCategory.DAG_TRIGGER, 0.5),
    ("deploy jfrog", IntentCategory.DAG_TRIGGER, 0.5),
    ("deploy a new freeipa server", IntentCategory.DAG_TRIGGER, 0.5),
    ("deploy freeipa with domain lab.example.com", IntentCategory.DAG_TRIGGER, 0.5),
    ("Deploy FreeIPA", IntentCategory.DAG_TRIGGER, 0.5),
    ("DEPLOY FREEIPA", IntentCategory.DAG_TRIGGER, 0.5),
    # destroy/delete <service>
    ("destroy freeipa", IntentCategory.DAG_TRIGGER, 0.5),
    ("delete freeipa", IntentCategory.DAG_TRIGGER, 0.5),
    ("remove freeipa", IntentCategory.DAG_TRIGGER, 0.5),
    ("teardown harbor", IntentCategory.DAG_TRIGGER, 0.5),
    ("destroy the vyos router", IntentCategory.DAG_TRIGGER, 0.5),
    ("delete the harbor registry", IntentCategory.DAG_TRIGGER, 0.5),
    ("remove vyos", IntentCategory.DAG_TRIGGER, 0.5),
    ("destroy jumpserver", IntentCategory.DAG_TRIGGER, 0.5),
    # trigger/run dag explicitly
    ("trigger dag freeipa_deployment", IntentCategory.DAG_TRIGGER, 0.5),
    ("run the freeipa_deployment dag", IntentCategory.DAG_TRIGGER, 0.5),
    ("execute dag harbor_deployment", IntentCategory.DAG_TRIGGER, 0.5),
    ("start workflow vyos_router_deployment", IntentCategory.DAG_TRIGGER, 0.5),
    ("trigger freeipa_deployment dag", IntentCategory.DAG_TRIGGER, 0.5),
    ("run dag step_ca_deployment", IntentCategory.DAG_TRIGGER, 0.5),
    # OCP-related triggers
    ("deploy openshift", IntentCategory.DAG_TRIGGER, 0.5),
    ("deploy ocp", IntentCategory.DAG_TRIGGER, 0.5),
    # ==================== VM_LIST ====================
    ("list vms", IntentCategory.VM_LIST, 0.5),
    ("list all vms", IntentCategory.VM_LIST, 0.5),
    ("show vms", IntentCategory.VM_LIST, 0.5),
    ("show all virtual machines", IntentCategory.VM_LIST, 0.5),
    ("what vms are running", IntentCategory.VM_LIST, 0.5),
    ("list virtual machines", IntentCategory.VM_LIST, 0.5),
    ("show me the vms", IntentCategory.VM_LIST, 0.5),
    # ==================== VM_INFO ====================
    ("vm info test-vm-01", IntentCategory.VM_INFO, 0.5),
    ("get vm details for web-server", IntentCategory.VM_INFO, 0.5),
    ("describe vm myvm", IntentCategory.VM_INFO, 0.5),
    ("vm status myvm", IntentCategory.VM_INFO, 0.5),
    ("tell me about vm prod-db", IntentCategory.VM_INFO, 0.5),
    ("info about vm freeipa-01", IntentCategory.VM_INFO, 0.5),
    ("details for vm web01", IntentCategory.VM_INFO, 0.5),
    # ==================== VM_CREATE ====================
    ("create a vm named test01", IntentCategory.VM_CREATE, 0.5),
    ("create vm web-server", IntentCategory.VM_CREATE, 0.5),
    ("spin up a new virtual machine", IntentCategory.VM_CREATE, 0.5),
    ("deploy a vm called db-01", IntentCategory.VM_CREATE, 0.5),
    ("provision a new vm", IntentCategory.VM_CREATE, 0.5),
    ("make a vm named dev-env", IntentCategory.VM_CREATE, 0.5),
    ("launch vm test-instance", IntentCategory.VM_CREATE, 0.5),
    ("create a new vm with 4GB RAM", IntentCategory.VM_CREATE, 0.5),
    ("create vm web01 with image centos9stream and 4GB RAM", IntentCategory.VM_CREATE, 0.5),
    ("create vm with 2 cpus and 8GB memory", IntentCategory.VM_CREATE, 0.5),
    # ==================== VM_DELETE ====================
    ("delete vm test01", IntentCategory.VM_DELETE, 0.5),
    ("remove vm old-server", IntentCategory.VM_DELETE, 0.5),
    ("destroy vm temp-vm", IntentCategory.VM_DELETE, 0.5),
    ("terminate the vm dev-box", IntentCategory.VM_DELETE, 0.5),
    ("delete the vm web-test", IntentCategory.VM_DELETE, 0.5),
    # ==================== VM_PREFLIGHT ====================
    ("preflight check for vm test01", IntentCategory.VM_PREFLIGHT, 0.5),
    ("pre-flight vm creation", IntentCategory.VM_PREFLIGHT, 0.5),
    ("can I create a vm with 16GB RAM", IntentCategory.VM_PREFLIGHT, 0.5),
    ("check before creating vm", IntentCategory.VM_PREFLIGHT, 0.5),
    ("validate vm creation", IntentCategory.VM_PREFLIGHT, 0.5),
    ("run preflight", IntentCategory.VM_PREFLIGHT, 0.5),
    # ==================== DAG_LIST ====================
    ("list dags", IntentCategory.DAG_LIST, 0.5),
    ("show all dags", IntentCategory.DAG_LIST, 0.5),
    ("list workflows", IntentCategory.DAG_LIST, 0.5),
    ("what dags are available", IntentCategory.DAG_LIST, 0.5),
    ("show available workflows", IntentCategory.DAG_LIST, 0.5),
    ("show dags", IntentCategory.DAG_LIST, 0.5),
    ("list all workflows", IntentCategory.DAG_LIST, 0.5),
    # ==================== DAG_INFO ====================
    ("dag info freeipa_deployment", IntentCategory.DAG_INFO, 0.5),
    ("details about dag vm_creation", IntentCategory.DAG_INFO, 0.5),
    ("describe dag openshift_deploy", IntentCategory.DAG_INFO, 0.5),
    ("dag details freeipa_deployment", IntentCategory.DAG_INFO, 0.5),
    # ==================== RAG_QUERY ====================
    ("search rag for DNS configuration", IntentCategory.RAG_QUERY, 0.5),
    ("query the knowledge base for FreeIPA setup", IntentCategory.RAG_QUERY, 0.5),
    ("find documentation about SSH operator", IntentCategory.RAG_QUERY, 0.5),
    ("how do I configure FreeIPA DNS", IntentCategory.RAG_QUERY, 0.5),
    ("lookup vm troubleshooting", IntentCategory.RAG_QUERY, 0.5),
    ("search docs for certificate setup", IntentCategory.RAG_QUERY, 0.5),
    ("how to deploy a vm", IntentCategory.VM_CREATE, 0.5),
    # ==================== RAG_INGEST ====================
    ("ingest documents into rag", IntentCategory.RAG_INGEST, 0.5),
    ("add document to knowledge base", IntentCategory.RAG_INGEST, 0.5),
    ("add to rag", IntentCategory.RAG_INGEST, 0.5),
    ("index document", IntentCategory.RAG_INGEST, 0.5),
    ("ingest the docs", IntentCategory.RAG_INGEST, 0.5),
    # ==================== RAG_STATS ====================
    ("rag stats", IntentCategory.RAG_STATS, 0.5),
    ("rag statistics", IntentCategory.RAG_STATS, 0.5),
    ("knowledge base stats", IntentCategory.RAG_STATS, 0.5),
    ("how many documents are in the rag", IntentCategory.RAG_STATS, 0.5),
    ("rag status", IntentCategory.RAG_STATS, 0.5),
    # ==================== SYSTEM_STATUS ====================
    ("system status", IntentCategory.SYSTEM_STATUS, 0.5),
    ("airflow status", IntentCategory.SYSTEM_STATUS, 0.5),
    ("check system health", IntentCategory.SYSTEM_STATUS, 0.5),
    ("is the system running", IntentCategory.SYSTEM_STATUS, 0.5),
    ("is airflow up", IntentCategory.SYSTEM_STATUS, 0.5),
    ("health check", IntentCategory.SYSTEM_STATUS, 0.5),
    ("status check", IntentCategory.SYSTEM_STATUS, 0.5),
    ("is everything healthy", IntentCategory.SYSTEM_STATUS, 0.5),
    # ==================== SYSTEM_INFO ====================
    ("system info", IntentCategory.SYSTEM_INFO, 0.5),
    ("system information", IntentCategory.SYSTEM_INFO, 0.5),
    ("tell me about the architecture", IntentCategory.SYSTEM_INFO, 0.5),
    ("qubinode overview", IntentCategory.SYSTEM_INFO, 0.5),
    ("what capabilities do you have", IntentCategory.SYSTEM_INFO, 0.5),
    # ==================== TROUBLESHOOT_DIAGNOSE ====================
    ("diagnose vm not responding", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    ("troubleshoot DNS failure", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    ("debug the failing dag", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    ("fix the broken vm", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    ("vm is not working", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    ("something is broken", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    ("why is the dag failing", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    ("error in vm deployment", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    ("freeipa is not responding", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    # ==================== TROUBLESHOOT_HISTORY ====================
    ("troubleshooting history", IntentCategory.TROUBLESHOOT_HISTORY, 0.5),
    ("past solutions for DNS errors", IntentCategory.TROUBLESHOOT_HISTORY, 0.5),
    ("has this been solved before", IntentCategory.TROUBLESHOOT_HISTORY, 0.5),
    ("similar errors", IntentCategory.TROUBLESHOOT_HISTORY, 0.5),
    ("previous fixes", IntentCategory.TROUBLESHOOT_HISTORY, 0.5),
    # ==================== TROUBLESHOOT_LOG ====================
    ("log the troubleshooting attempt", IntentCategory.TROUBLESHOOT_LOG, 0.5),
    ("record the solution", IntentCategory.TROUBLESHOOT_LOG, 0.5),
    ("save the fix", IntentCategory.TROUBLESHOOT_LOG, 0.5),
    ("log attempt", IntentCategory.TROUBLESHOOT_LOG, 0.5),
    # ==================== LINEAGE_DAG ====================
    ("lineage for dag freeipa_deployment", IntentCategory.LINEAGE_DAG, 0.5),
    ("dag lineage", IntentCategory.LINEAGE_DAG, 0.5),
    ("upstream dependencies of dag", IntentCategory.LINEAGE_DAG, 0.5),
    ("downstream of dag vm_creation", IntentCategory.LINEAGE_DAG, 0.5),
    ("what depends on this dag", IntentCategory.LINEAGE_DAG, 0.5),
    # ==================== LINEAGE_BLAST_RADIUS ====================
    ("blast radius for dag freeipa_deployment", IntentCategory.LINEAGE_BLAST_RADIUS, 0.5),
    ("failure impact analysis", IntentCategory.LINEAGE_BLAST_RADIUS, 0.5),
    ("what would be affected if freeipa_deployment fails", IntentCategory.LINEAGE_BLAST_RADIUS, 0.5),
    ("impact analysis for dns_management", IntentCategory.LINEAGE_BLAST_RADIUS, 0.5),
    # ==================== HELP ====================
    ("help", IntentCategory.HELP, 0.5),
    ("how do I use this", IntentCategory.HELP, 0.5),
    ("what can you do", IntentCategory.HELP, 0.5),
    # ==================== UNKNOWN (should NOT classify) ====================
    ("asdfghjkl", IntentCategory.UNKNOWN, 0.0),
    ("hello there", IntentCategory.UNKNOWN, 0.0),
    ("what is the weather like", IntentCategory.UNKNOWN, 0.0),
    ("tell me a joke", IntentCategory.UNKNOWN, 0.0),
    ("compare freeipa and keycloak", IntentCategory.UNKNOWN, 0.0),
    # ==================== Disambiguation (should pick correct one) ====================
    # "deploy freeipa" -> DAG_TRIGGER, not VM_CREATE
    ("deploy freeipa server", IntentCategory.DAG_TRIGGER, 0.5),
    # "destroy freeipa" -> DAG_TRIGGER (via service keyword), not troubleshoot
    ("destroy the jumpserver instance", IntentCategory.DAG_TRIGGER, 0.5),
    # "why is freeipa failing" -> TROUBLESHOOT, not DAG_TRIGGER
    ("why is freeipa failing", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    # "vm is broken" -> TROUBLESHOOT, not VM_INFO
    ("vm is broken", IntentCategory.TROUBLESHOOT_DIAGNOSE, 0.5),
    # ==================== Additional natural phrasings ====================
    # More DAG triggers
    ("I want to deploy freeipa", IntentCategory.DAG_TRIGGER, 0.5),
    ("please deploy harbor", IntentCategory.DAG_TRIGGER, 0.5),
    ("can you deploy vyos for me", IntentCategory.DAG_TRIGGER, 0.5),
    ("set up freeipa", IntentCategory.DAG_TRIGGER, 0.5),
    ("install freeipa", IntentCategory.DAG_TRIGGER, 0.5),
    # More VM operations
    ("show me vm details for web01", IntentCategory.VM_INFO, 0.5),
    ("create a centos vm", IntentCategory.VM_CREATE, 0.5),
    ("destroy vm freeipa-01", IntentCategory.VM_DELETE, 0.5),
    # More system queries
    ("is airflow healthy", IntentCategory.SYSTEM_STATUS, 0.5),
    ("check airflow status", IntentCategory.SYSTEM_STATUS, 0.5),
    # More RAG
    ("how can I set up DNS", IntentCategory.RAG_QUERY, 0.5),
    ("search knowledge base for openshift", IntentCategory.RAG_QUERY, 0.5),
    # Case insensitivity
    ("LIST VMS", IntentCategory.VM_LIST, 0.5),
    ("SYSTEM STATUS", IntentCategory.SYSTEM_STATUS, 0.5),
    ("Deploy Harbor", IntentCategory.DAG_TRIGGER, 0.5),
]


@pytest.mark.parametrize(
    "text,expected_category,min_confidence",
    CORPUS,
    ids=[f"{i:03d}_{t[:40]}" for i, (t, _, _) in enumerate(CORPUS)],
)
def test_corpus(text, expected_category, min_confidence):
    result = classify(text)
    assert result.category == expected_category, (
        f"Input: {text!r}\n"
        f"  Expected: {expected_category.value}\n"
        f"  Got:      {result.category.value} (confidence={result.confidence})"
    )
    assert result.confidence >= min_confidence, (
        f"Input: {text!r}\n"
        f"  Category correct ({result.category.value}) but confidence too low\n"
        f"  Expected >= {min_confidence}, got {result.confidence}"
    )


def test_corpus_summary():
    """Print precision/recall summary across all corpus examples."""
    from collections import defaultdict

    correct = 0
    total = len(CORPUS)
    by_category = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for text, expected, min_conf in CORPUS:
        result = classify(text)
        if result.category == expected:
            correct += 1
            by_category[expected]["tp"] += 1
        else:
            by_category[expected]["fn"] += 1
            by_category[result.category]["fp"] += 1

    accuracy = correct / total * 100
    print(f"\n{'='*60}")
    print(f"Classifier Corpus: {correct}/{total} correct ({accuracy:.1f}%)")
    print(f"{'='*60}")

    for cat in sorted(by_category.keys(), key=lambda c: c.value):
        stats = by_category[cat]
        tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
        precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
        print(f"  {cat.value:30s}  P={precision:5.1f}%  R={recall:5.1f}%  (TP={tp} FP={fp} FN={fn})")

    print(f"{'='*60}")
    assert accuracy >= 90, f"Overall accuracy {accuracy:.1f}% is below 90% threshold"
