"""
Tests for the intent classifier.

Covers all 20 intent categories with parametrized test cases,
ambiguous inputs, and edge cases.
"""

import pytest

from intent_parser.classifier import classify
from intent_parser.models import IntentCategory


class TestVMClassification:
    """Test VM-related intent classification."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("list vms", IntentCategory.VM_LIST),
            ("list all vms", IntentCategory.VM_LIST),
            ("show vms", IntentCategory.VM_LIST),
            ("show all virtual machines", IntentCategory.VM_LIST),
            ("what vms are running", IntentCategory.VM_LIST),
            ("list virtual machines", IntentCategory.VM_LIST),
        ],
    )
    def test_vm_list(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("vm info test-vm-01", IntentCategory.VM_INFO),
            ("get vm details for web-server", IntentCategory.VM_INFO),
            ("describe vm myvm", IntentCategory.VM_INFO),
            ("vm status myvm", IntentCategory.VM_INFO),
            ("tell me about vm prod-db", IntentCategory.VM_INFO),
        ],
    )
    def test_vm_info(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("create a vm named test01", IntentCategory.VM_CREATE),
            ("create vm web-server", IntentCategory.VM_CREATE),
            ("spin up a new virtual machine", IntentCategory.VM_CREATE),
            ("deploy a vm called db-01", IntentCategory.VM_CREATE),
            ("provision a new vm", IntentCategory.VM_CREATE),
            ("make a vm named dev-env", IntentCategory.VM_CREATE),
            ("launch vm test-instance", IntentCategory.VM_CREATE),
            ("create a new vm with 4GB RAM", IntentCategory.VM_CREATE),
        ],
    )
    def test_vm_create(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("delete vm test01", IntentCategory.VM_DELETE),
            ("remove vm old-server", IntentCategory.VM_DELETE),
            ("destroy vm temp-vm", IntentCategory.VM_DELETE),
            ("terminate the vm dev-box", IntentCategory.VM_DELETE),
        ],
    )
    def test_vm_delete(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("preflight check for vm test01", IntentCategory.VM_PREFLIGHT),
            ("pre-flight vm creation", IntentCategory.VM_PREFLIGHT),
            ("can I create a vm with 16GB RAM", IntentCategory.VM_PREFLIGHT),
            ("check before creating vm", IntentCategory.VM_PREFLIGHT),
            ("validate vm creation", IntentCategory.VM_PREFLIGHT),
        ],
    )
    def test_vm_preflight(self, text, expected):
        result = classify(text)
        assert result.category == expected


class TestDAGClassification:
    """Test DAG-related intent classification."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("list dags", IntentCategory.DAG_LIST),
            ("show all dags", IntentCategory.DAG_LIST),
            ("list workflows", IntentCategory.DAG_LIST),
            ("what dags are available", IntentCategory.DAG_LIST),
            ("show available workflows", IntentCategory.DAG_LIST),
        ],
    )
    def test_dag_list(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("dag info freeipa_deploy", IntentCategory.DAG_INFO),
            ("details about dag vm_creation", IntentCategory.DAG_INFO),
            ("describe dag openshift_deploy", IntentCategory.DAG_INFO),
        ],
    )
    def test_dag_info(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("trigger dag freeipa_deploy", IntentCategory.DAG_TRIGGER),
            ("run the vm_creation dag", IntentCategory.DAG_TRIGGER),
            ("execute dag openshift_deploy", IntentCategory.DAG_TRIGGER),
            ("start workflow freeipa_deploy", IntentCategory.DAG_TRIGGER),
            ("trigger freeipa_deploy dag", IntentCategory.DAG_TRIGGER),
        ],
    )
    def test_dag_trigger(self, text, expected):
        result = classify(text)
        assert result.category == expected


class TestRAGClassification:
    """Test RAG-related intent classification."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("search rag for DNS configuration", IntentCategory.RAG_QUERY),
            ("query the knowledge base for FreeIPA setup", IntentCategory.RAG_QUERY),
            ("find documentation about SSH operator", IntentCategory.RAG_QUERY),
            ("how do I configure FreeIPA DNS", IntentCategory.RAG_QUERY),
            ("how can we deploy OpenShift", IntentCategory.DAG_TRIGGER),
            ("lookup vm troubleshooting", IntentCategory.RAG_QUERY),
        ],
    )
    def test_rag_query(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("ingest documents into rag", IntentCategory.RAG_INGEST),
            ("add document to knowledge base", IntentCategory.RAG_INGEST),
            ("add to rag", IntentCategory.RAG_INGEST),
            ("index document", IntentCategory.RAG_INGEST),
        ],
    )
    def test_rag_ingest(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("rag stats", IntentCategory.RAG_STATS),
            ("rag statistics", IntentCategory.RAG_STATS),
            ("knowledge base stats", IntentCategory.RAG_STATS),
            ("how many documents are in the rag", IntentCategory.RAG_STATS),
        ],
    )
    def test_rag_stats(self, text, expected):
        result = classify(text)
        assert result.category == expected


class TestSystemClassification:
    """Test system-related intent classification."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("system status", IntentCategory.SYSTEM_STATUS),
            ("airflow status", IntentCategory.SYSTEM_STATUS),
            ("check system health", IntentCategory.SYSTEM_STATUS),
            ("is the system running", IntentCategory.SYSTEM_STATUS),
            ("is airflow up", IntentCategory.SYSTEM_STATUS),
            ("health check", IntentCategory.SYSTEM_STATUS),
            ("status check", IntentCategory.SYSTEM_STATUS),
        ],
    )
    def test_system_status(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("system info", IntentCategory.SYSTEM_INFO),
            ("system information", IntentCategory.SYSTEM_INFO),
            ("tell me about the architecture", IntentCategory.SYSTEM_INFO),
            ("qubinode overview", IntentCategory.SYSTEM_INFO),
        ],
    )
    def test_system_info(self, text, expected):
        result = classify(text)
        assert result.category == expected


class TestTroubleshootClassification:
    """Test troubleshooting-related intent classification."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("diagnose vm not responding", IntentCategory.TROUBLESHOOT_DIAGNOSE),
            ("troubleshoot DNS failure", IntentCategory.TROUBLESHOOT_DIAGNOSE),
            ("debug the failing dag", IntentCategory.TROUBLESHOOT_DIAGNOSE),
            ("fix the broken vm", IntentCategory.TROUBLESHOOT_DIAGNOSE),
            ("vm is not working", IntentCategory.TROUBLESHOOT_DIAGNOSE),
            ("something is broken", IntentCategory.TROUBLESHOOT_DIAGNOSE),
            ("why is the dag failing", IntentCategory.TROUBLESHOOT_DIAGNOSE),
            ("error in vm deployment", IntentCategory.TROUBLESHOOT_DIAGNOSE),
        ],
    )
    def test_troubleshoot_diagnose(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("troubleshooting history", IntentCategory.TROUBLESHOOT_HISTORY),
            ("past solutions for DNS errors", IntentCategory.TROUBLESHOOT_HISTORY),
            ("has this been solved before", IntentCategory.TROUBLESHOOT_HISTORY),
            ("similar errors", IntentCategory.TROUBLESHOOT_HISTORY),
            ("previous fixes", IntentCategory.TROUBLESHOOT_HISTORY),
        ],
    )
    def test_troubleshoot_history(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("log the troubleshooting attempt", IntentCategory.TROUBLESHOOT_LOG),
            ("record the solution", IntentCategory.TROUBLESHOOT_LOG),
            ("save the fix", IntentCategory.TROUBLESHOOT_LOG),
            ("log attempt", IntentCategory.TROUBLESHOOT_LOG),
        ],
    )
    def test_troubleshoot_log(self, text, expected):
        result = classify(text)
        assert result.category == expected


class TestLineageClassification:
    """Test lineage-related intent classification."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("lineage for dag freeipa_deploy", IntentCategory.LINEAGE_DAG),
            ("dag lineage", IntentCategory.LINEAGE_DAG),
            ("upstream dependencies of dag", IntentCategory.LINEAGE_DAG),
            ("downstream of dag vm_creation", IntentCategory.LINEAGE_DAG),
            ("what depends on this dag", IntentCategory.LINEAGE_DAG),
        ],
    )
    def test_lineage_dag(self, text, expected):
        result = classify(text)
        assert result.category == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("blast radius for dag freeipa_deploy", IntentCategory.LINEAGE_BLAST_RADIUS),
            ("failure impact analysis", IntentCategory.LINEAGE_BLAST_RADIUS),
            ("what would be affected if freeipa_deploy fails", IntentCategory.LINEAGE_BLAST_RADIUS),
        ],
    )
    def test_lineage_blast_radius(self, text, expected):
        result = classify(text)
        assert result.category == expected


class TestHelpClassification:
    """Test help intent classification."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("help", IntentCategory.HELP),
            ("how do I use this", IntentCategory.HELP),
            ("what can you do", IntentCategory.HELP),
        ],
    )
    def test_help(self, text, expected):
        result = classify(text)
        assert result.category == expected


class TestEdgeCases:
    """Test edge cases and ambiguous inputs."""

    def test_empty_string(self):
        result = classify("")
        assert result.category == IntentCategory.UNKNOWN
        assert result.confidence == 0.0

    def test_whitespace_only(self):
        result = classify("   ")
        assert result.category == IntentCategory.UNKNOWN

    def test_none_input(self):
        result = classify(None)
        assert result.category == IntentCategory.UNKNOWN

    def test_gibberish(self):
        result = classify("asdfghjkl")
        assert result.category == IntentCategory.UNKNOWN

    def test_confidence_is_positive(self):
        result = classify("list vms")
        assert result.confidence > 0

    def test_confidence_bounded(self):
        result = classify("list all vms and show every virtual machine")
        assert 0.0 <= result.confidence <= 1.0

    def test_raw_input_preserved(self):
        text = "  list vms  "
        result = classify(text)
        assert result.raw_input == text.strip()
