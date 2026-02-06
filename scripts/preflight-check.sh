#!/bin/bash
# =============================================================================
# preflight-check.sh - Pre-flight Validation for Qubinode Navigator
# =============================================================================
#
# Validates all prerequisites before deployment to catch issues early.
# Run this BEFORE deploy-qubinode-with-airflow.sh
#
# Usage:
#   ./scripts/preflight-check.sh [--fix]
#
# Options:
#   --fix    Attempt to fix missing dependencies automatically
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FIX_MODE="${1:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASS=0
FAIL=0
WARN=0
FIXED=0

# =============================================================================
# Helper Functions
# =============================================================================

check_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARN++))
}

check_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

check_fixed() {
    echo -e "${GREEN}[FIXED]${NC} $1"
    ((FIXED++))
}

section() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
}

# =============================================================================
# System Checks
# =============================================================================

check_os() {
    section "Operating System"

    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        echo "Detected: $NAME $VERSION_ID"

        case "$ID" in
            rhel|centos|rocky|almalinux)
                if [[ "${VERSION_ID%%.*}" -ge 9 ]]; then
                    check_pass "OS version supported (RHEL/CentOS 9+)"
                else
                    check_warn "OS version $VERSION_ID may have issues (recommend 9+)"
                fi
                ;;
            fedora)
                check_pass "Fedora detected"
                ;;
            *)
                check_warn "Untested OS: $ID - may work but not guaranteed"
                ;;
        esac
    else
        check_fail "Cannot detect OS"
    fi
}

check_virtualization() {
    section "Virtualization Support"

    # Check CPU virtualization
    if grep -qE '(vmx|svm)' /proc/cpuinfo 2>/dev/null; then
        check_pass "CPU virtualization enabled (VT-x/AMD-V)"
    else
        check_fail "CPU virtualization not detected - KVM will not work"
    fi

    # Check KVM module
    if lsmod | grep -q kvm; then
        check_pass "KVM kernel module loaded"
    else
        check_warn "KVM module not loaded - will be loaded during deployment"
    fi

    # Check libvirt
    if systemctl is-active --quiet libvirtd 2>/dev/null; then
        check_pass "libvirtd service running"
    elif command -v libvirtd &>/dev/null; then
        check_warn "libvirtd installed but not running"
    else
        check_warn "libvirtd not installed - will be installed during deployment"
    fi
}

check_containers() {
    section "Container Runtime"

    # Check podman
    if command -v podman &>/dev/null; then
        local version
        version=$(podman --version 2>/dev/null | awk '{print $3}')
        check_pass "Podman installed: $version"
    else
        check_warn "Podman not installed - will be installed during deployment"
    fi

    # Check podman-compose
    if command -v podman-compose &>/dev/null; then
        check_pass "podman-compose installed"
    else
        check_warn "podman-compose not installed - will be installed"
    fi
}

check_network() {
    section "Network Connectivity"

    # Check internet
    if curl -s --connect-timeout 5 https://github.com &>/dev/null; then
        check_pass "Internet connectivity (github.com)"
    else
        check_fail "Cannot reach github.com - required for repo cloning"
    fi

    # Check quay.io
    if curl -s --connect-timeout 5 https://quay.io &>/dev/null; then
        check_pass "Container registry (quay.io)"
    else
        check_warn "Cannot reach quay.io - may affect container pulls"
    fi
}

# =============================================================================
# External Repository Checks
# =============================================================================

check_external_repos() {
    section "External Repositories"

    local repos=(
        "/opt/kcli-pipelines|https://github.com/Qubinode/kcli-pipelines.git"
    )

    for repo_info in "${repos[@]}"; do
        local path="${repo_info%%|*}"
        local url="${repo_info##*|}"
        local name="$(basename "$path")"

        if [[ -d "$path/.git" ]]; then
            check_pass "$name exists at $path"
        elif [[ -d "$path" ]]; then
            check_warn "$name exists but not a git repo: $path"
        else
            if [[ "$FIX_MODE" == "--fix" ]]; then
                check_info "Cloning $name..."
                if git clone "$url" "$path" 2>/dev/null; then
                    check_fixed "$name cloned to $path"
                else
                    check_fail "$name missing - clone failed"
                fi
            else
                check_fail "$name missing at $path"
                echo "       Fix: git clone $url $path"
            fi
        fi
    done
}

# =============================================================================
# Configuration Checks
# =============================================================================

check_vault_password() {
    section "Vault Configuration"

    local vault_file="$HOME/.vault_password"

    if [[ -f "$vault_file" ]]; then
        if [[ -s "$vault_file" ]]; then
            check_pass "Vault password file exists: $vault_file"
        else
            check_fail "Vault password file is empty: $vault_file"
        fi
    else
        check_warn "Vault password not set - will be created during deployment"
    fi

    # Check symlinks
    local symlink_targets=(
        "/opt/kcli-pipelines/.vault_password"
    )

    for target in "${symlink_targets[@]}"; do
        local dir="$(dirname "$target")"
        if [[ -d "$dir" ]]; then
            if [[ -L "$target" ]]; then
                check_pass "Vault symlink exists: $target"
            elif [[ -f "$vault_file" && "$FIX_MODE" == "--fix" ]]; then
                ln -sf "$vault_file" "$target" 2>/dev/null && \
                    check_fixed "Created vault symlink: $target" || \
                    check_warn "Could not create symlink: $target"
            else
                check_warn "Vault symlink missing: $target"
            fi
        fi
    done
}

check_ssh_config() {
    section "SSH Configuration"

    # Check SSH key exists
    if [[ -f "$HOME/.ssh/id_rsa" ]]; then
        check_pass "SSH private key exists"
    else
        check_warn "SSH key not found - will be generated during deployment"
    fi

    # Check authorized_keys for localhost access
    if [[ -f "$HOME/.ssh/authorized_keys" ]]; then
        if [[ -f "$HOME/.ssh/id_rsa.pub" ]]; then
            local pubkey
            pubkey=$(cat "$HOME/.ssh/id_rsa.pub" 2>/dev/null)
            if grep -qF "$pubkey" "$HOME/.ssh/authorized_keys" 2>/dev/null; then
                check_pass "SSH key in authorized_keys (localhost access)"
            else
                check_warn "SSH key not in authorized_keys - container→host SSH may fail"
            fi
        fi
    else
        check_warn "No authorized_keys file"
    fi

    # Test localhost SSH
    if ssh -o BatchMode=yes -o ConnectTimeout=5 localhost true 2>/dev/null; then
        check_pass "SSH to localhost works"
    else
        check_warn "SSH to localhost failed - may need configuration"
    fi
}

check_inventory() {
    section "Inventory Configuration"

    local inventories=("localhost" "dev")

    for inv in "${inventories[@]}"; do
        local vault_yml="$PROJECT_ROOT/inventories/$inv/group_vars/control/vault.yml"
        if [[ -f "$vault_yml" ]]; then
            check_pass "vault.yml exists for inventory: $inv"
        else
            check_info "vault.yml not found for inventory: $inv (optional)"
        fi
    done
}

# =============================================================================
# Disk Space Check
# =============================================================================

check_disk_space() {
    section "Disk Space"

    local required_gb=50
    local available_gb
    available_gb=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')

    echo "Available: ${available_gb}GB (recommended: ${required_gb}GB)"

    if [[ "$available_gb" -ge "$required_gb" ]]; then
        check_pass "Sufficient disk space"
    elif [[ "$available_gb" -ge 30 ]]; then
        check_warn "Low disk space - may run out during deployment"
    else
        check_fail "Insufficient disk space (need at least 30GB)"
    fi
}

check_memory() {
    section "Memory"

    local required_gb=8
    local total_gb
    total_gb=$(free -g | awk '/^Mem:/ {print $2}')

    echo "Available: ${total_gb}GB RAM (recommended: ${required_gb}GB)"

    if [[ "$total_gb" -ge "$required_gb" ]]; then
        check_pass "Sufficient memory"
    elif [[ "$total_gb" -ge 4 ]]; then
        check_warn "Low memory - may affect VM deployments"
    else
        check_fail "Insufficient memory (need at least 4GB)"
    fi
}

# =============================================================================
# Airflow Specific Checks
# =============================================================================

check_airflow_prerequisites() {
    section "Airflow Prerequisites"

    # Check if Airflow directory exists
    if [[ -d "$PROJECT_ROOT/airflow" ]]; then
        check_pass "Airflow directory exists"
    else
        check_fail "Airflow directory missing"
    fi

    # Check docker-compose.yml
    if [[ -f "$PROJECT_ROOT/airflow/docker-compose.yml" ]]; then
        check_pass "docker-compose.yml exists"
    else
        check_fail "docker-compose.yml missing"
    fi

    # Check DAGs directory
    local dag_count
    dag_count=$(find "$PROJECT_ROOT/airflow/dags" -name "*.py" 2>/dev/null | wc -l)
    if [[ "$dag_count" -gt 0 ]]; then
        check_pass "Found $dag_count DAG files"
    else
        check_warn "No DAG files found"
    fi

    # Check port availability
    for port in 8888 5432; do
        if ! ss -tuln | grep -q ":$port "; then
            check_pass "Port $port available"
        else
            check_warn "Port $port in use - may conflict with Airflow"
        fi
    done
}

# =============================================================================
# Summary
# =============================================================================

print_summary() {
    section "Pre-flight Summary"

    echo ""
    echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, ${YELLOW}$WARN warnings${NC}"

    if [[ "$FIXED" -gt 0 ]]; then
        echo -e "         ${GREEN}$FIXED issues auto-fixed${NC}"
    fi

    echo ""

    if [[ "$FAIL" -eq 0 ]]; then
        echo -e "${GREEN}Pre-flight checks passed!${NC}"
        echo ""
        echo "You can proceed with deployment:"
        echo "  ./deploy-qubinode-with-airflow.sh"
        return 0
    else
        echo -e "${RED}Pre-flight checks failed!${NC}"
        echo ""
        echo "Fix the issues above before proceeding."
        if [[ "$FIX_MODE" != "--fix" ]]; then
            echo ""
            echo "TIP: Run with --fix to auto-fix some issues:"
            echo "  ./scripts/preflight-check.sh --fix"
        fi
        return 1
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "========================================"
    echo "Qubinode Navigator Pre-flight Check"
    echo "========================================"
    echo ""
    echo "Checking prerequisites for deployment..."

    if [[ "$FIX_MODE" == "--fix" ]]; then
        echo -e "${YELLOW}Running in FIX mode - will attempt to fix issues${NC}"
    fi

    check_os
    check_virtualization
    check_containers
    check_network
    check_disk_space
    check_memory
    check_external_repos
    check_vault_password
    check_ssh_config
    check_inventory
    check_airflow_prerequisites

    print_summary
}

main "$@"
