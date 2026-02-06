"""
Tests for the entity extractor.

Covers parameter extraction for VMs, DAGs, RAG queries,
numeric values, and domain names.
"""

from intent_parser.entity_extractor import extract
from intent_parser.models import IntentCategory


class TestVMEntityExtraction:
    """Test VM parameter extraction."""

    def test_vm_name_with_named(self):
        params = extract("create vm named test01", IntentCategory.VM_CREATE)
        assert params["name"] == "test01"

    def test_vm_name_with_called(self):
        params = extract("create vm called web-server", IntentCategory.VM_CREATE)
        assert params["name"] == "web-server"

    def test_vm_name_after_vm(self):
        params = extract("delete vm old-box", IntentCategory.VM_DELETE)
        assert params["name"] == "old-box"

    def test_vm_name_info(self):
        params = extract("info about vm prod-db", IntentCategory.VM_INFO)
        assert params["name"] == "prod-db"

    def test_vm_memory_gb(self):
        params = extract("create vm named test01 with 4GB RAM", IntentCategory.VM_CREATE)
        assert params["memory"] == 4096

    def test_vm_memory_gb_lowercase(self):
        params = extract("create vm named test01 4g memory", IntentCategory.VM_CREATE)
        assert params["memory"] == 4096

    def test_vm_memory_mb(self):
        params = extract("create vm named test01 8192mb memory", IntentCategory.VM_CREATE)
        assert params["memory"] == 8192

    def test_vm_cpus(self):
        params = extract("create vm named test01 with 4 cpus", IntentCategory.VM_CREATE)
        assert params["cpus"] == 4

    def test_vm_cores(self):
        params = extract("create vm named test01 2 cores", IntentCategory.VM_CREATE)
        assert params["cpus"] == 2

    def test_vm_disk(self):
        params = extract("create vm named test01 50GB disk", IntentCategory.VM_CREATE)
        assert params["disk_size"] == 50

    def test_vm_disk_plain(self):
        params = extract("create vm named test01 disk 100", IntentCategory.VM_CREATE)
        assert params["disk_size"] == 100

    def test_vm_image(self):
        params = extract("create vm named test01 with image rhel9", IntentCategory.VM_CREATE)
        assert params["image"] == "rhel9"

    def test_vm_image_using(self):
        params = extract("create vm named test01 using centos10stream image", IntentCategory.VM_CREATE)
        assert params["image"] == "centos10stream"

    def test_vm_full_params(self):
        params = extract(
            "create a vm named prod-web with 8GB RAM 4 cpus 100GB disk image rhel9",
            IntentCategory.VM_CREATE,
        )
        assert params["name"] == "prod-web"
        assert params["memory"] == 8192
        assert params["cpus"] == 4
        assert params["disk_size"] == 100
        assert params["image"] == "rhel9"


class TestDAGEntityExtraction:
    """Test DAG parameter extraction."""

    def test_dag_id_from_info(self):
        params = extract("dag info freeipa_deploy", IntentCategory.DAG_INFO)
        assert params["dag_id"] == "freeipa_deploy"

    def test_dag_id_from_trigger(self):
        params = extract("trigger dag vm_creation", IntentCategory.DAG_TRIGGER)
        assert params["dag_id"] == "vm_creation"

    def test_dag_id_trigger_reverse(self):
        params = extract("trigger freeipa_deploy dag", IntentCategory.DAG_TRIGGER)
        assert params["dag_id"] == "freeipa_deploy"

    def test_dag_id_run(self):
        params = extract("run dag openshift_deploy", IntentCategory.DAG_TRIGGER)
        assert params["dag_id"] == "openshift_deploy"

    def test_dag_list_no_params(self):
        params = extract("list all dags", IntentCategory.DAG_LIST)
        assert "dag_id" not in params


class TestRAGEntityExtraction:
    """Test RAG query parameter extraction."""

    def test_rag_query_extraction(self):
        params = extract("search rag for DNS configuration", IntentCategory.RAG_QUERY)
        assert params.get("query") == "DNS configuration"

    def test_rag_query_knowledge_base(self):
        params = extract("query the knowledge base for FreeIPA setup", IntentCategory.RAG_QUERY)
        assert "FreeIPA setup" in params.get("query", "")

    def test_rag_query_how_to(self):
        params = extract("how do I configure DNS", IntentCategory.RAG_QUERY)
        assert "configure DNS" in params.get("query", "")

    def test_rag_limit(self):
        params = extract("search rag for errors limit=10", IntentCategory.RAG_QUERY)
        assert params["limit"] == 10

    def test_rag_threshold(self):
        params = extract("search rag for errors threshold=0.5", IntentCategory.RAG_QUERY)
        assert params["threshold"] == 0.5


class TestTroubleshootEntityExtraction:
    """Test troubleshooting parameter extraction."""

    def test_component_vm(self):
        params = extract("diagnose vm not starting", IntentCategory.TROUBLESHOOT_DIAGNOSE)
        assert params.get("component") == "vm"

    def test_component_dag(self):
        params = extract("troubleshoot airflow dag failure", IntentCategory.TROUBLESHOOT_DIAGNOSE)
        assert params.get("component") == "dag"

    def test_component_network(self):
        params = extract("diagnose DNS resolution failure", IntentCategory.TROUBLESHOOT_DIAGNOSE)
        assert params.get("component") == "network"

    def test_component_freeipa(self):
        params = extract("troubleshoot freeipa enrollment", IntentCategory.TROUBLESHOOT_DIAGNOSE)
        assert params.get("component") == "freeipa"

    def test_symptom_extraction(self):
        params = extract("diagnose vm won't boot", IntentCategory.TROUBLESHOOT_DIAGNOSE)
        assert "vm won't boot" in params.get("symptom", "")

    def test_error_message_quoted(self):
        params = extract('diagnose error "connection refused"', IntentCategory.TROUBLESHOOT_DIAGNOSE)
        assert params.get("error_message") == "connection refused"

    def test_affected_resource(self):
        params = extract(
            "troubleshoot vm web-server-01 not responding",
            IntentCategory.TROUBLESHOOT_DIAGNOSE,
        )
        assert params.get("affected_resource") == "web-server-01"

    def test_history_successful_only(self):
        params = extract(
            "show successful only troubleshooting history",
            IntentCategory.TROUBLESHOOT_HISTORY,
        )
        assert params.get("only_successful") is True


class TestLineageEntityExtraction:
    """Test lineage parameter extraction."""

    def test_lineage_dag_id(self):
        params = extract("lineage for dag freeipa_deploy", IntentCategory.LINEAGE_DAG)
        assert params.get("dag_id") == "freeipa_deploy"

    def test_lineage_depth(self):
        params = extract("lineage for dag freeipa_deploy depth=3", IntentCategory.LINEAGE_DAG)
        assert params.get("depth") == 3

    def test_blast_radius_dag_id(self):
        params = extract("blast radius for dag vm_creation", IntentCategory.LINEAGE_BLAST_RADIUS)
        assert params.get("dag_id") == "vm_creation"

    def test_blast_radius_task_id(self):
        params = extract(
            "blast radius for dag vm_creation task create_step",
            IntentCategory.LINEAGE_BLAST_RADIUS,
        )
        assert params.get("task_id") == "create_step"


class TestDestroyActionExtraction:
    """Test destroy action extraction for DAG triggers."""

    def test_destroy_sets_action(self):
        params = extract("destroy freeipa", IntentCategory.DAG_TRIGGER)
        assert params.get("dag_id") == "freeipa_deployment"
        assert params.get("conf", {}).get("action") == "destroy"

    def test_delete_sets_action(self):
        params = extract("delete harbor", IntentCategory.DAG_TRIGGER)
        assert params.get("dag_id") == "harbor_deployment"
        assert params.get("conf", {}).get("action") == "destroy"

    def test_remove_sets_action(self):
        params = extract("remove the jumpserver", IntentCategory.DAG_TRIGGER)
        assert params.get("dag_id") == "jumpserver_deployment"
        assert params.get("conf", {}).get("action") == "destroy"

    def test_teardown_sets_action(self):
        params = extract("teardown vyos", IntentCategory.DAG_TRIGGER)
        assert params.get("dag_id") == "vyos_router_deployment"
        assert params.get("conf", {}).get("action") == "destroy"

    def test_deploy_no_action(self):
        params = extract("deploy freeipa", IntentCategory.DAG_TRIGGER)
        assert params.get("dag_id") == "freeipa_deployment"
        assert "action" not in params.get("conf", {})

    def test_destroy_with_domain(self):
        params = extract("destroy freeipa with domain example.com", IntentCategory.DAG_TRIGGER)
        assert params.get("dag_id") == "freeipa_deployment"
        assert params.get("conf", {}).get("action") == "destroy"
        assert params.get("conf", {}).get("domain") == "example.com"


class TestKeyValueExtraction:
    """Test explicit key=value parameter extraction."""

    def test_simple_key_value(self):
        params = extract("create vm name=test01 memory=4096", IntentCategory.VM_CREATE)
        assert params["name"] == "test01"
        assert params["memory"] == 4096

    def test_quoted_key_value(self):
        params = extract('create vm name="my-test-vm"', IntentCategory.VM_CREATE)
        assert params["name"] == "my-test-vm"

    def test_numeric_conversion(self):
        params = extract("memory=8192 cpus=4 disk_size=100", IntentCategory.VM_CREATE)
        assert params["memory"] == 8192
        assert isinstance(params["memory"], int)

    def test_string_values_preserved(self):
        params = extract("image=rhel9", IntentCategory.VM_CREATE)
        assert params["image"] == "rhel9"
        assert isinstance(params["image"], str)
