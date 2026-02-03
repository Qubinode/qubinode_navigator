"""
Airflow DAG: FreeIPA Identity Management Server Deployment
ADR-0039: FreeIPA and VyOS Airflow DAG Integration
ADR-0043: Airflow Container Host Network Access

This DAG automates the complete deployment of FreeIPA including:
- VM provisioning via kcli
- FreeIPA server installation via Ansible
- DNS configuration
- Service validation

Follows the kcli-pipelines and freeipa-workshop-deployer patterns.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import BranchPythonOperator
from airflow.providers.ssh.operators.ssh import SSHOperator

# Import user-configurable helpers for portable DAGs
from dag_helpers import (
    get_ssh_key_path,
    get_inventory_dir,
    get_ssh_conn_id,
    get_kcli_prefix,
    get_sudo_prefix,
)

# Get kcli prefix (sudo or empty) based on SSH user configuration
# This is evaluated at DAG parse time and auto-detects if sudo is needed
KCLI = get_kcli_prefix()

# Get sudo prefix for privileged operations (mkdir /opt, /etc/hosts)
# Auto-detects: returns "sudo " if SSH user is not root
SUDO = get_sudo_prefix()

# Default arguments
default_args = {
    "owner": "qubinode",
    "depends_on_past": False,
    "start_date": datetime(2025, 11, 27),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

# DAG definition
dag = DAG(
    "freeipa_deployment",
    default_args=default_args,
    description="Deploy FreeIPA Identity Management Server via kcli and Ansible",
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=["qubinode", "freeipa", "identity", "infrastructure", "kcli-pipelines"],
    params={
        "action": "create",  # create or destroy
        "community_version": "true",  # true for CentOS, false for RHEL
        "os_version": "9",  # 8 or 9
        "domain": "example.com",
        "idm_hostname": "idm",
        "dns_forwarder": "8.8.8.8",
        "run_ansible_install": "true",  # Run Ansible to install FreeIPA
    },
)

# Paths - using host paths since we run with host network (ADR-0043)
FREEIPA_DEPLOYER = "/opt/freeipa-workshop-deployer"
QUBINODE_NAV = "/opt/qubinode_navigator"

# User-configurable paths (used in commands, not for string concatenation)
# SSH connection is managed by Airflow SSHOperator via get_ssh_conn_id()
SSH_KEY_PATH = get_ssh_key_path()
INVENTORY_BASE_DIR = get_inventory_dir()


def decide_action(**context):
    """Branch based on action parameter (create or destroy)."""
    action = context["params"].get("action", "create")
    if action == "destroy":
        return "destroy_freeipa"
    return "validate_environment"


# Task: Decide action
decide_action_task = BranchPythonOperator(
    task_id="decide_action",
    python_callable=decide_action,
    dag=dag,
)

# =============================================================================
# CREATE WORKFLOW
# =============================================================================

# Task: Validate environment
# Using SSHOperator instead of BashOperator + manual SSH
validate_environment = SSHOperator(
    task_id="validate_environment",
    ssh_conn_id=get_ssh_conn_id(),
    command=f"""
    echo "========================================"
    echo "Validating FreeIPA Deployment Environment"
    echo "========================================"

    COMMUNITY_VERSION="{{{{ params.community_version }}}}"
    OS_VERSION="{{{{ params.os_version }}}}"

    echo "Community Version: $COMMUNITY_VERSION"
    echo "OS Version: $OS_VERSION"

    if [ "$COMMUNITY_VERSION" == "true" ]; then
        [ "$OS_VERSION" == "9" ] && IMAGE_NAME=centos9stream || IMAGE_NAME=centos8stream
    else
        [ "$OS_VERSION" == "9" ] && IMAGE_NAME=rhel9 || IMAGE_NAME=rhel8
    fi
    echo "Image: $IMAGE_NAME"

    if ! command -v kcli &> /dev/null; then
        echo "[ERROR] kcli not installed"
        exit 1
    fi
    echo "[OK] kcli installed: $({KCLI}kcli --version 2>&1 | head -1)"

    if {KCLI}kcli list images | grep -q "$IMAGE_NAME"; then
        echo "[OK] Image $IMAGE_NAME available"
    else
        echo "[WARN] Image $IMAGE_NAME not found, will download during VM creation"
    fi

    VAULT_FILE=/opt/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml
    if [ -f "$VAULT_FILE" ]; then
        echo "[OK] vault.yml found"
    else
        echo "[ERROR] vault.yml not found at $VAULT_FILE"
        exit 1
    fi

    if [ -d /opt/freeipa-workshop-deployer ]; then
        echo "[OK] freeipa-workshop-deployer found"
    else
        echo "[WARN] Cloning freeipa-workshop-deployer..."
        git clone https://github.com/tosin2013/freeipa-workshop-deployer.git /opt/freeipa-workshop-deployer
    fi

    echo ""
    echo "[OK] Environment validation complete"
    """,
    dag=dag,
)

# Task: Create FreeIPA VM
# Using SSHOperator instead of BashOperator + manual SSH
create_freeipa_vm = SSHOperator(
    task_id="create_freeipa_vm",
    ssh_conn_id=get_ssh_conn_id(),
    command=f"""
    echo "========================================"
    echo "Creating FreeIPA VM"
    echo "========================================"

    COMMUNITY_VERSION="{{{{ params.community_version }}}}"
    OS_VERSION="{{{{ params.os_version }}}}"

    if [ "$COMMUNITY_VERSION" == "true" ]; then
        [ "$OS_VERSION" == "9" ] && IMAGE_NAME=centos9stream || IMAGE_NAME=centos8stream
    else
        [ "$OS_VERSION" == "9" ] && IMAGE_NAME=rhel9 || IMAGE_NAME=rhel8
    fi

    VM_NAME=freeipa

    if {KCLI}kcli info vm $VM_NAME &>/dev/null; then
        echo "[WARN] VM $VM_NAME already exists"
        {KCLI}kcli info vm $VM_NAME
        exit 0
    fi

    echo "Creating VM: $VM_NAME"
    echo "  Image: $IMAGE_NAME"
    echo "  Memory: 4096 MB"
    echo "  CPUs: 2"
    echo "  Disk: 50 GB"

    {KCLI}kcli create vm $VM_NAME \
        -i $IMAGE_NAME \
        -P memory=4096 \
        -P numcpus=2 \
        -P disks=[50] \
        -P nets=[default] \
        --wait < /dev/null || {{
        echo "[ERROR] Failed to create VM"
        exit 1
    }}

    echo ""
    echo "[OK] VM created successfully"
    {KCLI}kcli info vm $VM_NAME
    """,
    cmd_timeout=600,
    dag=dag,
)

# Task: Wait for VM and get IP
# Using SSHOperator instead of BashOperator + manual SSH
wait_for_vm = SSHOperator(
    task_id="wait_for_vm",
    ssh_conn_id=get_ssh_conn_id(),
    command=f"""
    echo "========================================"
    echo "Waiting for FreeIPA VM to be Ready"
    echo "========================================"

    VM_NAME=freeipa
    MAX_ATTEMPTS=60

    echo "Waiting for VM to get IP address..."

    for i in $(seq 1 $MAX_ATTEMPTS); do
        VM_INFO=$({KCLI}kcli info vm $VM_NAME 2>/dev/null)
        IP=$(echo "$VM_INFO" | grep "^ip:" | awk "{{print \\$2}}")

        if [ -n "$IP" ] && [ "$IP" != "None" ] && [ "$IP" != "" ]; then
            echo "[OK] VM IP: $IP"

            echo "Waiting for SSH..."
            for j in $(seq 1 30); do
                if nc -z -w5 $IP 22 2>/dev/null; then
                    echo "[OK] SSH is available"

                    echo ""
                    echo "========================================"
                    echo "FreeIPA VM Ready"
                    echo "========================================"
                    echo "VM Name: $VM_NAME"
                    echo "IP Address: $IP"
                    echo "SSH: ssh cloud-user@$IP"
                    exit 0
                fi
                echo "  Attempt $j/30: SSH not ready..."
                sleep 5
            done

            echo "[WARN] SSH not available after 30 attempts"
            exit 0
        fi

        echo "  Attempt $i/$MAX_ATTEMPTS: Waiting for IP..."
        sleep 5
    done

    echo "[ERROR] Failed to get VM IP after $MAX_ATTEMPTS attempts"
    exit 1
    """,
    cmd_timeout=600,
    dag=dag,
)

# Task: Prepare Ansible Inventory
# Using SSHOperator instead of BashOperator + manual SSH
prepare_ansible = SSHOperator(
    task_id="prepare_ansible",
    ssh_conn_id=get_ssh_conn_id(),
    command=f"""
    echo "========================================"
    echo "Preparing Ansible for FreeIPA Installation"
    echo "========================================"

    DOMAIN="{{{{ params.domain }}}}"
    IDM_HOSTNAME="{{{{ params.idm_hostname }}}}"
    DNS_FORWARDER="{{{{ params.dns_forwarder }}}}"
    COMMUNITY_VERSION="{{{{ params.community_version }}}}"

    # Get IP via kcli on host
    VM_NAME="freeipa"
    IP=$({KCLI}kcli info vm $VM_NAME 2>/dev/null | grep "^ip:" | awk "{{print \\$2}}")

    if [ -z "$IP" ] || [ "$IP" == "None" ]; then
        echo "[ERROR] Could not get VM IP"
        exit 1
    fi

    echo "VM IP: $IP"
    echo "Domain: $DOMAIN"
    echo "IDM Hostname: $IDM_HOSTNAME"

    # Determine login user
    [ "$COMMUNITY_VERSION" == "true" ] && LOGIN_USER="cloud-user" || LOGIN_USER="cloud-user"

    # Create inventory directory
    # Uses get_inventory_dir() default of /opt/.generated (configurable via QUBINODE_INVENTORY_DIR)
    # SUDO prefix handles non-root users who need sudo for /opt/ access
    INVENTORY_DIR="{INVENTORY_BASE_DIR}/.$IDM_HOSTNAME.$DOMAIN"
    {SUDO}mkdir -p "$INVENTORY_DIR"

    # Create Ansible inventory
    # Note: ansible_host MUST be on the hostname line, not in [all:vars]
    cat > "$INVENTORY_DIR/inventory" << INVENTORY_EOF
[idm]
$IDM_HOSTNAME ansible_host=$IP

[all:vars]
ansible_ssh_private_key_file={SSH_KEY_PATH}
ansible_ssh_user=$LOGIN_USER
ansible_ssh_common_args=-o StrictHostKeyChecking=no
ansible_internal_private_ip=$IP
INVENTORY_EOF

    echo "[OK] Inventory created at $INVENTORY_DIR/inventory"
    cat "$INVENTORY_DIR/inventory"

    # Update /etc/hosts (requires root/sudo)
    grep -v "$IDM_HOSTNAME" /etc/hosts > /tmp/hosts.tmp || true
    echo "$IP $IDM_HOSTNAME.$DOMAIN $IDM_HOSTNAME" >> /tmp/hosts.tmp
    {SUDO}cp /tmp/hosts.tmp /etc/hosts
    echo "[OK] Updated /etc/hosts"

    # Test SSH connectivity
    echo ""
    echo "Testing SSH connectivity..."
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $LOGIN_USER@$IP "hostname" || {{
        echo "[WARN] SSH test failed - may need to wait longer"
    }}

    # Install Ansible collections
    echo ""
    echo "Installing Ansible collections..."
    cd /opt/freeipa-workshop-deployer
    if [ -f "2_ansible_config/collections/requirements.yaml" ]; then
        ansible-galaxy install --force -r /opt/freeipa-workshop-deployer/2_ansible_config/collections/requirements.yaml 2>/dev/null || true
        ansible-galaxy collection install freeipa.ansible_freeipa 2>/dev/null || true
    fi

    echo ""
    echo "[OK] Ansible preparation complete"
    """,
    cmd_timeout=600,  # 10 minutes for ansible-galaxy collection install
    dag=dag,
)

# Task: Install FreeIPA via Ansible
# Using SSHOperator instead of BashOperator + manual SSH
install_freeipa = SSHOperator(
    task_id="install_freeipa",
    ssh_conn_id=get_ssh_conn_id(),
    command=f"""
    echo "========================================"
    echo "Installing FreeIPA via Ansible"
    echo "========================================"

    RUN_ANSIBLE="{{{{ params.run_ansible_install }}}}"

    if [ "$RUN_ANSIBLE" != "true" ]; then
        echo "[SKIP] Ansible installation skipped"
        exit 0
    fi

    set -e
    DOMAIN="{{{{ params.domain }}}}"
    IDM_HOSTNAME="{{{{ params.idm_hostname }}}}"
    DNS_FORWARDER="{{{{ params.dns_forwarder }}}}"

    VM_NAME="freeipa"
    IP=$({KCLI}kcli info vm $VM_NAME 2>/dev/null | grep "^ip:" | awk "{{print \\$2}}")

    if [ -z "$IP" ]; then
        echo "[ERROR] Could not get VM IP"
        exit 1
    fi

    # Use same inventory path as prepare_ansible task
    INVENTORY_DIR="{INVENTORY_BASE_DIR}/.$IDM_HOSTNAME.$DOMAIN"
    PLAYBOOK_DIR="/opt/freeipa-workshop-deployer"

    echo "Running Ansible playbook..."
    echo "  Inventory: $INVENTORY_DIR/inventory"
    echo "  Playbook: $PLAYBOOK_DIR/2_ansible_config/deploy_idm.yaml"
    echo "  Domain: $DOMAIN"
    echo "  IDM Hostname: $IDM_HOSTNAME"
    echo "  DNS Forwarder: $DNS_FORWARDER"
    echo "  VM IP: $IP"

    cd $PLAYBOOK_DIR
    ANSIBLE_HOST_KEY_CHECKING=False \
    ansible-playbook \
        -i $INVENTORY_DIR/inventory \
        --extra-vars "idm_hostname=$IDM_HOSTNAME" \
        --extra-vars "private_ip=$IP" \
        --extra-vars "domain=$DOMAIN" \
        --extra-vars "dns_forwarder=$DNS_FORWARDER" \
        2_ansible_config/deploy_idm.yaml \
        -v

    echo ""
    echo "========================================"
    echo "FreeIPA Installation Complete!"
    echo "========================================"
    echo "FreeIPA Web UI: https://$IDM_HOSTNAME.$DOMAIN"
    echo "IP Address: $IP"
    echo "Username: admin"
    """,
    cmd_timeout=1800,
    dag=dag,
)

# Task: Validate FreeIPA Installation
# Using SSHOperator instead of BashOperator + manual SSH
validate_freeipa = SSHOperator(
    task_id="validate_freeipa",
    ssh_conn_id=get_ssh_conn_id(),
    command=f"""
    echo "========================================"
    echo "Validating FreeIPA Installation"
    echo "========================================"

    DOMAIN="{{{{ params.domain }}}}"
    IDM_HOSTNAME="{{{{ params.idm_hostname }}}}"
    RUN_ANSIBLE="{{{{ params.run_ansible_install }}}}"

    VM_NAME="freeipa"
    IP=$({KCLI}kcli info vm $VM_NAME 2>/dev/null | grep "^ip:" | awk "{{print \\$2}}")

    echo "Checking FreeIPA services on $IP..."

    if [ "$RUN_ANSIBLE" == "true" ]; then
        ssh -o StrictHostKeyChecking=no cloud-user@$IP "sudo ipactl status" 2>/dev/null || echo "[WARN] Could not verify FreeIPA services yet"
    else
        echo "[INFO] Ansible installation was skipped"
    fi

    echo ""
    echo "========================================"
    echo "FreeIPA Deployment Summary"
    echo "========================================"
    echo "VM Name: $VM_NAME"
    echo "IP Address: $IP"
    echo "FQDN: ${{IDM_HOSTNAME}}.${{DOMAIN}}"
    echo ""
    echo "Access:"
    echo "  SSH: ssh cloud-user@$IP"
    echo "  Web UI: https://${{IDM_HOSTNAME}}.${{DOMAIN}}"
    echo "  Username: admin"
    """,
    dag=dag,
)

# =============================================================================
# DESTROY WORKFLOW
# =============================================================================

destroy_freeipa = SSHOperator(
    task_id="destroy_freeipa",
    ssh_conn_id=get_ssh_conn_id(),
    command=f"""
    echo "========================================"
    echo "Destroying FreeIPA VM"
    echo "========================================"

    VM_NAME=freeipa

    if {KCLI}kcli info vm $VM_NAME &>/dev/null; then
        echo "Deleting VM: $VM_NAME"
        {KCLI}kcli delete vm $VM_NAME -y
        echo "[OK] VM deleted"
    else
        echo "[WARN] VM $VM_NAME does not exist"
    fi

    DOMAIN="{{{{ params.domain }}}}"
    IDM_HOSTNAME="{{{{ params.idm_hostname }}}}"
    {SUDO}rm -rf {INVENTORY_BASE_DIR}/.${{IDM_HOSTNAME}}.${{DOMAIN}} 2>/dev/null || true

    grep -v "${{IDM_HOSTNAME}}" /etc/hosts > /tmp/hosts.tmp 2>/dev/null || true
    {SUDO}cp /tmp/hosts.tmp /etc/hosts 2>/dev/null || true

    echo ""
    echo "[OK] FreeIPA cleanup complete"
    """,
    dag=dag,
)

# =============================================================================
# DAG WORKFLOW
# =============================================================================

# Create workflow
(decide_action_task >> validate_environment >> create_freeipa_vm >> wait_for_vm >> prepare_ansible >> install_freeipa >> validate_freeipa)

# Destroy workflow
decide_action_task >> destroy_freeipa

# DAG documentation
dag.doc_md = """
# FreeIPA Deployment DAG

This DAG automates the complete deployment of FreeIPA Identity Management Server.

## Workflow

### Create (action=create)
1. **validate_environment** - Check kcli, images, vault.yml
2. **create_freeipa_vm** - Create VM via kcli
3. **wait_for_vm** - Wait for IP and SSH
4. **prepare_ansible** - Create inventory, install collections
5. **install_freeipa** - Run Ansible playbook to install FreeIPA
6. **validate_freeipa** - Verify services are running

### Destroy (action=destroy)
1. **destroy_freeipa** - Delete VM and cleanup

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| action | create | create or destroy |
| community_version | true | true=CentOS, false=RHEL |
| os_version | 9 | 8 or 9 |
| domain | example.com | Domain name |
| idm_hostname | idm | Hostname for FreeIPA |
| dns_forwarder | 8.8.8.8 | DNS forwarder |
| run_ansible_install | true | Run Ansible to install FreeIPA |

## Prerequisites

- vault.yml with freeipa_server_admin_password
- kcli configured with libvirt
- Base OS image (centos9stream or rhel9)

## Related ADRs

- ADR-0039: FreeIPA and VyOS Airflow DAG Integration
- ADR-0042: FreeIPA Base OS Upgrade to RHEL 9
- ADR-0043: Airflow Container Host Network Access
"""
