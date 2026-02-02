#!/bin/bash

# =============================================================================
# Qubinode Navigator Setup (Modernized) - The "Plugin-Powered Mission Control"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This is the modernized entry point script that orchestrates Qubinode Navigator
# deployment using the new plugin framework (ADR-0028). It replaces monolithic
# OS-specific scripts with intelligent plugin orchestration.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script follows the new plugin-based deployment workflow:
# 1. [PHASE 1]: Environment Detection - Enhanced OS detection including RHEL 10/CentOS 10
# 2. [PHASE 2]: Plugin Framework Setup - Initializes the plugin system
# 3. [PHASE 3]: Intelligent Plugin Selection - Auto-selects appropriate plugins
# 4. [PHASE 4]: Plugin Orchestration - Executes plugins in dependency order
# 5. [PHASE 5]: Validation & Next Steps - Provides intelligent guidance
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Plugin Framework Integration]: Uses qubinode_cli.py for plugin orchestration
# - [Intelligent OS Detection]: Enhanced detection for all supported OS versions
# - [Backward Compatibility]: Maintains compatibility with existing workflows
# - [Modern Architecture]: Implements ADR-0028 plugin framework
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Plugin-First Approach]: Uses modular plugins instead of monolithic scripts
# - [Intelligent Detection]: Auto-detects OS, cloud provider, and environment
# - [Idempotent Operations]: All operations are safely repeatable
# - [Comprehensive Coverage]: Supports RHEL 8/9/10, Rocky Linux, CentOS Stream 10
# - [Cloud-Aware]: Detects and optimizes for Hetzner, Equinix, and other providers

set -e

# QUBINODE_HOME Setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_QUBINODE_HOME="/opt/qubinode_navigator"
QUBINODE_HOME="${QUBINODE_HOME:-$DEFAULT_QUBINODE_HOME}"
export QUBINODE_HOME

# Ensure uv is available for fast Python package management
ensure_uv() {
    if ! command -v uv &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

# 📊 GLOBAL VARIABLES
export ANSIBLE_SAFE_VERSION="0.0.14"
export GIT_REPO="https://github.com/Qubinode/qubinode_navigator.git"
export PLUGIN_FRAMEWORK_VERSION="1.0.0"

if [ -z "$CICD_PIPELINE" ]; then
  export CICD_PIPELINE="false"
  export INVENTORY="localhost"
fi

# Enhanced OS Detection Engine - The "Modern System Scanner"
function get_os_version() {
    echo "🔍 Detecting operating system..."

    if cat /etc/redhat-release 2>/dev/null | grep -q "Red Hat Enterprise Linux release 10"; then
        export BASE_OS="RHEL10"
        export PLUGIN_SELECTION="RHEL10Plugin"
    elif cat /etc/redhat-release 2>/dev/null | grep -q "Red Hat Enterprise Linux release 9"; then
        export BASE_OS="RHEL9"
        export PLUGIN_SELECTION="RHEL9Plugin"
    elif cat /etc/redhat-release 2>/dev/null | grep -q "Red Hat Enterprise Linux release 8"; then
        export BASE_OS="RHEL8"
        export PLUGIN_SELECTION="RHEL8Plugin"
    elif cat /etc/redhat-release 2>/dev/null | grep -q "CentOS Stream release 10"; then
        export BASE_OS="CENTOS10"
        export PLUGIN_SELECTION="CentOSStream10Plugin"
    elif cat /etc/redhat-release 2>/dev/null | grep -q "CentOS Stream release 9"; then
        export BASE_OS="CENTOS9"
        export PLUGIN_SELECTION="RHEL9Plugin"  # Use RHEL9 plugin for CentOS 9
    elif cat /etc/redhat-release 2>/dev/null | grep -q "Rocky Linux release 9"; then
        export BASE_OS="ROCKY9"
        export PLUGIN_SELECTION="RockyLinuxPlugin"
    elif cat /etc/redhat-release 2>/dev/null | grep -q "Rocky Linux release 8"; then
        export BASE_OS="ROCKY8"
        export PLUGIN_SELECTION="RockyLinuxPlugin"
    elif cat /etc/redhat-release 2>/dev/null | grep -q "Fedora"; then
        export BASE_OS="FEDORA"
        export PLUGIN_SELECTION="RHEL9Plugin"  # Use RHEL9 plugin as fallback
    else
        echo "❌ Operating System not supported by plugin framework"
        echo "📋 Supported OS: RHEL 8/9/10, CentOS Stream 9/10, Rocky Linux 8/9, Fedora"
        echo "🔧 Consider contributing a plugin for your OS"
        exit 1
    fi

    echo "✅ Detected: ${BASE_OS}"
    echo "🔌 Selected Plugin: ${PLUGIN_SELECTION}"
}

# Cloud Provider Detection - The "Environment Intelligence"
function detect_cloud_provider() {
    echo "🌐 Detecting cloud provider..."

    export CLOUD_PLUGINS=""

    # Detect Hetzner Cloud
    if curl -s --max-time 3 "http://169.254.169.254/hetzner/v1/metadata" >/dev/null 2>&1; then
        export CLOUD_PROVIDER="HETZNER"
        export CLOUD_PLUGINS="HetznerPlugin"
        echo "✅ Detected: Hetzner Cloud"
    # Detect Equinix Metal
    elif curl -s --max-time 3 "https://metadata.platformequinix.com/metadata" >/dev/null 2>&1; then
        export CLOUD_PROVIDER="EQUINIX"
        export CLOUD_PLUGINS="EquinixPlugin"
        echo "✅ Detected: Equinix Metal"
    # Check for demo environments
    elif [ -f "/tmp/config.yml" ] || [ -f "notouch.env" ]; then
        if grep -q "hetzner\|Hetzner" /etc/hostname 2>/dev/null || ip addr | grep -q "eth0.*10\.0\."; then
            export CLOUD_PROVIDER="HETZNER_DEMO"
            export CLOUD_PLUGINS="HetznerDeploymentPlugin"
            echo "✅ Detected: Hetzner Demo Environment"
        else
            export CLOUD_PROVIDER="REDHAT_DEMO"
            export CLOUD_PLUGINS="RedHatDemoPlugin EquinixPlugin"
            echo "✅ Detected: Red Hat Demo Environment"
        fi
    else
        export CLOUD_PROVIDER="BARE_METAL"
        echo "✅ Detected: Bare Metal / Local Environment"
    fi
}

# Plugin Framework Setup - The "Modern Infrastructure Initializer"
function setup_plugin_framework() {
    echo "🔧 Setting up plugin framework..."

    # Ensure we're in the right directory
    if [ ! -d "${QUBINODE_HOME}" ]; then
        echo "📥 Cloning Qubinode Navigator to ${QUBINODE_HOME}..."
        mkdir -p "$(dirname ${QUBINODE_HOME})"
        git clone ${GIT_REPO} "${QUBINODE_HOME}"
        cd "${QUBINODE_HOME}"
    else
        echo "📂 Using existing Qubinode Navigator installation at ${QUBINODE_HOME}"
        cd "${QUBINODE_HOME}"
        git pull origin main || true
    fi

    # Install Python dependencies for plugin framework
    echo "🐍 Installing Python dependencies..."
    if command -v dnf >/dev/null 2>&1; then
        dnf install -y python3 python3-pip python3-pyyaml
    elif command -v yum >/dev/null 2>&1; then
        yum install -y python3 python3-pip python3-pyyaml
    fi

    # Install plugin framework dependencies
    ensure_uv
    uv pip install pyyaml requests hvac python-dotenv

    echo "✅ Plugin framework ready"
}

# Plugin Selection Intelligence - The "Smart Orchestrator"
function select_plugins() {
    echo "🧠 Selecting appropriate plugins..."

    export SELECTED_PLUGINS="${PLUGIN_SELECTION}"

    # Add cloud plugins if detected
    if [ -n "$CLOUD_PLUGINS" ]; then
        export SELECTED_PLUGINS="${SELECTED_PLUGINS} ${CLOUD_PLUGINS}"
    fi

    # Add service plugins based on configuration
    if [ -f "/tmp/config.yml" ] && grep -q "vault\|VAULT" /tmp/config.yml 2>/dev/null; then
        export SELECTED_PLUGINS="${SELECTED_PLUGINS} VaultIntegrationPlugin"
    fi

    echo "🔌 Selected Plugins: ${SELECTED_PLUGINS}"
}

# Plugin Execution - The "Orchestrated Deployment"
function execute_plugins() {
    echo "🚀 Executing plugin-based deployment..."

    # Update plugin configuration to enable selected plugins
    python3 -c "
import yaml
import sys

config_file = 'config/plugins.yml'
try:
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    # Update enabled plugins
    plugins = '${SELECTED_PLUGINS}'.split()
    config['plugins']['enabled'] = plugins

    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)

    print(f'✅ Updated plugin configuration: {plugins}')
except Exception as e:
    print(f'❌ Failed to update plugin configuration: {e}')
    sys.exit(1)
"

    # Execute plugins using the CLI
    echo "🔄 Running plugin orchestration..."
    python3 qubinode_cli.py execute

    if [ $? -eq 0 ]; then
        echo "✅ Plugin execution completed successfully"
    else
        echo "❌ Plugin execution failed"
        return 1
    fi
}

# Compatibility Bridge - The "Legacy Integration Layer"
function provide_compatibility_info() {
    echo ""
    echo "🔄 Migration Information"
    echo "======================="
    echo "📋 This modernized setup replaces the following legacy scripts:"
    echo "   • rhel8-linux-hypervisor.sh → RHEL8Plugin"
    echo "   • rhel9-linux-hypervisor.sh → RHEL9Plugin"
    echo "   • rocky-linux-hetzner.sh → RockyLinuxPlugin + HetznerPlugin"
    echo "   • setup-vault-integration.sh → VaultIntegrationPlugin"
    echo ""
    echo "🎯 Benefits of Plugin Framework:"
    echo "   ✅ Idempotent operations (safe to re-run)"
    echo "   ✅ Intelligent environment detection"
    echo "   ✅ Modular and extensible architecture"
    echo "   ✅ Comprehensive logging and error handling"
    echo "   ✅ Support for latest OS versions (RHEL 10, CentOS Stream 10)"
}

# Next Steps Guide - The "Intelligent Assistant"
function provide_next_steps() {
    echo ""
    echo "🎯 Next Steps"
    echo "============="

    case $CLOUD_PROVIDER in
        "HETZNER_DEMO")
            echo "🔧 Hetzner Deployment Detected:"
            echo "   1. Switch to lab-user: sudo su - lab-user"
            echo "   2. Source environment: source notouch.env"
            echo "   3. Verify config: cat /tmp/config.yml"
            echo "   4. Continue with deployment"
            ;;
        "REDHAT_DEMO")
            echo "🔧 Red Hat Demo Environment Detected:"
            echo "   1. Verify RHSM credentials in /tmp/config.yml"
            echo "   2. Switch to lab-user: sudo su - lab-user"
            echo "   3. Continue with Qubinode Navigator deployment"
            ;;
        *)
            echo "🔧 Standard Deployment:"
            echo "   1. Review plugin execution results above"
            echo "   2. Check system status: python3 qubinode_cli.py status"
            echo "   3. Continue with Ansible playbook execution"
            ;;
    esac

    echo ""
    echo "📚 For more information:"
    echo "   • Plugin Status: python3 qubinode_cli.py status"
    echo "   • Available Plugins: python3 qubinode_cli.py list"
    echo "   • Documentation: https://tosin2013.github.io/qubinode_navigator"
}

# Main Execution Flow
function main() {
    echo "🚀 Qubinode Navigator Setup (Plugin Framework v${PLUGIN_FRAMEWORK_VERSION})"
    echo "========================================================================="

    # Phase 1: Detection
    get_os_version
    detect_cloud_provider

    # Phase 2: Setup
    setup_plugin_framework

    # Phase 3: Intelligence
    select_plugins

    # Phase 4: Execution
    execute_plugins

    # Phase 5: Guidance
    provide_compatibility_info
    provide_next_steps

    echo ""
    echo "🎉 Qubinode Navigator setup completed successfully!"
    echo "🔌 Plugin framework is ready for deployment"
}

# Script execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
