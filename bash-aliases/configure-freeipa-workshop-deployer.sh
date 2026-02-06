#!/bin/bash

# =============================================================================
# FreeIPA Workshop Deployer - The "Identity Management Specialist"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script deploys and configures FreeIPA identity management server with DNS
# services using the freeipa-workshop-deployer project. It provides centralized
# authentication, authorization, and DNS services for enterprise environments.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements FreeIPA deployment:
# 1. [PHASE 1]: Repository Management - Clones or updates freeipa-workshop-deployer
# 2. [PHASE 2]: Configuration Generation - Creates environment-specific configuration
# 3. [PHASE 3]: Variable Substitution - Updates configuration with domain and DNS settings
# 4. [PHASE 4]: Platform Configuration - Configures for kcli virtualization platform
# 5. [PHASE 5]: Service Deployment - Deploys FreeIPA server with DNS integration
# 6. [PHASE 6]: DNS Management - Configures dynamic DNS for workshop services
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Identity Management]: Provides centralized authentication for infrastructure
# - [DNS Services]: Offers DNS resolution for workshop and lab environments
# - [Workshop Integration]: Supports educational and training deployments
# - [Virtualization Integration]: Works with kcli and KVM virtualization
# - [Domain Management]: Manages domain names and DNS records
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Workshop-Focused]: Designed for educational and training environments
# - [DNS Integration]: Provides both identity management and DNS services
# - [Platform-Agnostic]: Supports multiple infrastructure providers (kcli, AWS)
# - [Dynamic Configuration]: Adapts to different domain and network configurations
# - [Cleanup-Capable]: Includes destruction and cleanup capabilities
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [FreeIPA Updates]: Update for new FreeIPA versions or features
# - [Platform Support]: Add support for new virtualization platforms
# - [DNS Enhancements]: Add support for new DNS providers or configurations
# - [Workshop Features]: Add new workshop services or integrations
# - [Security Updates]: Implement new security configurations or hardening
#
# 🚨 IMPORTANT FOR LLMs: This script deploys identity management infrastructure
# that affects authentication and DNS for the entire environment. It requires
# network configuration and may impact existing DNS settings.

#github-action genshdoc
# @ file Setup freeipa-workshop-deployer https://github.com/tosin2013/freeipa-workshop-deployer
# @ brief This script will setup the freeipa-workshop-deployer

# FreeIPA Deployment Manager - The "Identity Infrastructure Deployer"
function deploy_freeipa(){
# 🎯 FOR LLMs: This function deploys FreeIPA identity management server with
# DNS services, configured for workshop and educational environments.
# 🔄 WORKFLOW:
# 1. Sets up environment variables and dependencies
# 2. Clones or updates freeipa-workshop-deployer repository
# 3. Configures deployment variables for current environment
# 4. Adapts configuration for kcli virtualization platform
# 5. Executes total deployment process
# 📊 INPUTS/OUTPUTS:
# - INPUT: Environment variables and system configuration
# - OUTPUT: Deployed FreeIPA server with DNS services
# ⚠️  SIDE EFFECTS: Creates virtual machines, modifies DNS configuration, requires network access
    set_variables
    dependency_check

    # FreeIPA Ansible content is now vendored in the Qubinode Navigator repo
    FREEIPA_PLAYBOOK_DIR="/opt/qubinode_navigator/ansible/playbooks/freeipa"
    if [ ! -f "$FREEIPA_PLAYBOOK_DIR/deploy_idm.yaml" ]; then
        echo "[ERROR] Vendored FreeIPA playbook not found at $FREEIPA_PLAYBOOK_DIR"
        echo "  Ensure qubinode_navigator repo is up to date"
        return 1
    fi

    if [ -d /opt/qubinode_navigator/kcli-plan-samples ]; then
        echo "kcli-plan-samples folder  already exists"
    else
        update_profiles_file
    fi

    echo "[INFO] FreeIPA deployment now uses the Airflow DAG (freeipa_deployment)"
    echo "  Trigger via: curl -X POST -u admin:admin http://localhost:8888/api/v1/dags/freeipa_deployment/dagRuns -H 'Content-Type: application/json' -d '{\"conf\": {}}'"
    echo "  Or via Airflow UI: http://localhost:8888"
}

# FreeIPA Destruction Manager - The "Infrastructure Cleanup Specialist"
function destroy_freeipa(){
# 🎯 FOR LLMs: This function safely destroys FreeIPA infrastructure and cleans up
# DNS records to return the environment to its original state.
# 🔄 WORKFLOW:
# 1. Destroys FreeIPA virtual machines using kcli
# 2. Retrieves IP address information for DNS cleanup
# 3. Removes dynamic DNS records for workshop services
# 4. Returns to home directory for cleanup completion
# 📊 INPUTS/OUTPUTS:
# - INPUT: Existing FreeIPA deployment and DNS records
# - OUTPUT: Cleaned environment with removed infrastructure and DNS records
# ⚠️  SIDE EFFECTS: Destroys virtual machines, removes DNS records, requires network access
    echo "[INFO] FreeIPA destruction now uses the Airflow DAG (freeipa_deployment with action=destroy)"
    echo "  Trigger via: curl -X POST -u admin:admin http://localhost:8888/api/v1/dags/freeipa_deployment/dagRuns -H 'Content-Type: application/json' -d '{\"conf\": {\"action\": \"destroy\"}}'"
    echo "  Or via Airflow UI: http://localhost:8888"
}
