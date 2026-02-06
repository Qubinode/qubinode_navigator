#!/bin/bash
# =============================================================================
# Qubinode Navigator One-Shot Deployment Script
# =============================================================================
#
# 🎯 PURPOSE: Deploy complete Qubinode Navigator solution on modern RHEL-based machines
# 🖥️  SUPPORTED: RHEL 9/10, CentOS Stream 9/10, Rocky Linux 9, AlmaLinux 9
# 🤖 AI HELP: Integrated AI Assistant for troubleshooting and guidance
# 🔗 INTEGRATION: Uses existing setup.sh and rhel9-linux-hypervisor.sh architecture
# 📜 ADR: Based on ADR-0001 One-Shot Deployment Script Consolidation
#
# USAGE:
#   1. Configure environment variables in .env file or export them
#   2. Run: ./deploy-qubinode.sh
#   3. If issues occur, the AI Assistant will be available for help
#
# =============================================================================

set -euo pipefail

# Script metadata
SCRIPT_VERSION="1.1.0"
SCRIPT_NAME="Qubinode Navigator One-Shot Deployment"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Calculate repository root - the script is at scripts/development/deploy-qubinode.sh
# so we go up two levels to get to the repository root
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# =============================================================================
# QUBINODE_HOME Setup and Migration
# =============================================================================
# Canonical location: /opt/qubinode_navigator
# Auto-migrate from $HOME/qubinode_navigator if needed

setup_qubinode_home() {
    local default_path="/opt/qubinode_navigator"
    local home_path="$HOME/qubinode_navigator"

    # Use environment variable if set, otherwise use default
    QUBINODE_HOME="${QUBINODE_HOME:-$default_path}"

    # If canonical location doesn't exist, check for migration opportunity
    if [[ ! -d "$QUBINODE_HOME" ]] && [[ "$QUBINODE_HOME" == "$default_path" ]]; then
        if [[ -d "$home_path" ]]; then
            echo "[INFO] Migrating qubinode_navigator from $home_path to $QUBINODE_HOME..."
            sudo mkdir -p "$QUBINODE_HOME"
            sudo cp -r "$home_path"/* "$QUBINODE_HOME"/
            sudo chown -R root:users "$QUBINODE_HOME" 2>/dev/null || sudo chown -R root:root "$QUBINODE_HOME"
            sudo chmod -R g+w "$QUBINODE_HOME"
            echo "[INFO] Migration complete. Original preserved at $home_path"
        elif [[ -d "$REPO_ROOT" ]]; then
            # Running from git clone - use repo root
            QUBINODE_HOME="$REPO_ROOT"
        fi
    fi

    export QUBINODE_HOME
    export REPO_ROOT="$QUBINODE_HOME"  # Backward compatibility alias
}

setup_qubinode_home

# Ensure uv is available for fast Python package management
ensure_uv() {
    if ! command -v uv &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

# Validate we're in the right repository
if [[ ! -d "$QUBINODE_HOME/airflow" ]] || [[ ! -d "$QUBINODE_HOME/ai-assistant" ]]; then
    echo "ERROR: Cannot find qubinode_navigator repository root"
    echo "Expected to find airflow/ and ai-assistant/ directories at: $QUBINODE_HOME"
    echo "Please run this script from within the qubinode_navigator repository"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Constants
readonly MIN_USER_UID=1000  # Minimum UID for regular users
readonly MAX_USER_UID=65534  # Maximum UID for regular users (excludes nobody/nogroup)

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

log_ai() {
    echo -e "${CYAN}[AI ASSISTANT]${NC} $1"
}

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================

# Load environment variables from .env file if it exists
# Check both repository root and script directory
# Security Note: Only source .env files that you control. Do not source untrusted files.
if [[ -f "$REPO_ROOT/.env" ]]; then
    log_info "Loading configuration from $REPO_ROOT/.env..."
    set -a  # Automatically export all variables
    source "$REPO_ROOT/.env"
    set +a
elif [[ -f "$SCRIPT_DIR/.env" ]]; then
    log_info "Loading configuration from $SCRIPT_DIR/.env..."
    set -a  # Automatically export all variables
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Required Environment Variables (with defaults)
export QUBINODE_DOMAIN="${QUBINODE_DOMAIN:-example.com}"

# Auto-detect admin user with better defaults
# Priority: 1. QUBINODE_ADMIN_USER env var, 2. SUDO_USER (when using sudo), 3. SSH_USER, 4. Current USER
if [[ -z "${QUBINODE_ADMIN_USER:-}" ]]; then
    if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
        DEFAULT_USER="$SUDO_USER"
    elif [[ -n "${SSH_USER:-}" && "${SSH_USER}" != "root" ]]; then
        DEFAULT_USER="$SSH_USER"
    elif [[ -n "${USER:-}" && "${USER}" != "root" ]]; then
        DEFAULT_USER="$USER"
    else
        DEFAULT_USER="lab-user"  # Common default for lab environments
    fi
    export QUBINODE_ADMIN_USER="$DEFAULT_USER"
fi

export QUBINODE_CLUSTER_NAME="${QUBINODE_CLUSTER_NAME:-qubinode}"
export QUBINODE_DEPLOYMENT_MODE="${QUBINODE_DEPLOYMENT_MODE:-production}"

# Integration with existing Qubinode Navigator architecture
export GIT_REPO="https://github.com/Qubinode/qubinode_navigator.git"
export CICD_PIPELINE="${CICD_PIPELINE:-false}"
export INVENTORY="${INVENTORY:-localhost}"
export USE_HASHICORP_VAULT="${USE_HASHICORP_VAULT:-false}"
export USE_HASHICORP_CLOUD="${USE_HASHICORP_CLOUD:-false}"
export SSH_USER="${SSH_USER:-${QUBINODE_ADMIN_USER:-lab-user}}"
export ANSIBLE_SAFE_VERSION="0.0.14"

# Optional Environment Variables
export QUBINODE_ENABLE_AI_ASSISTANT="${QUBINODE_ENABLE_AI_ASSISTANT:-true}"

# AI Assistant Configuration
export AI_ASSISTANT_PORT="${AI_ASSISTANT_PORT:-8080}"
export AI_ASSISTANT_VERSION="${AI_ASSISTANT_VERSION:-latest}"
# Build AI Assistant from source (includes PydanticAI + Smart Pipeline)
# Set to true for E2E testing or when using latest development features
export BUILD_AI_ASSISTANT_FROM_SOURCE="${BUILD_AI_ASSISTANT_FROM_SOURCE:-false}"

# PydanticAI Model Configuration (ADR-0049/ADR-0063)
# Explicitly export model variables to ensure they're passed to container
# Default to Google Gemini 2.0 Flash (fast, cheap, capable)
export MANAGER_MODEL="${MANAGER_MODEL:-google-gla:gemini-2.0-flash}"
export DEVELOPER_MODEL="${DEVELOPER_MODEL:-google-gla:gemini-2.0-flash}"
export PYDANTICAI_MODEL="${PYDANTICAI_MODEL:-${MANAGER_MODEL}}"

# Airflow Orchestration Configuration (Core Infrastructure)
export QUBINODE_ENABLE_AIRFLOW="${QUBINODE_ENABLE_AIRFLOW:-true}"
export AIRFLOW_PORT="${AIRFLOW_PORT:-8888}"
export AIRFLOW_VERSION="${AIRFLOW_VERSION:-2.10.4-python3.12}"
export AIRFLOW_NETWORK="${AIRFLOW_NETWORK:-airflow_default}"
export QUBINODE_ENABLE_NGINX_PROXY="${QUBINODE_ENABLE_NGINX_PROXY:-false}"
export NGINX_PORT="${NGINX_PORT:-80}"

# ADR-0050: Host AI Services Configuration (Hybrid Architecture)
# These services run on the host for better performance and smaller containers
export QUBINODE_ENABLE_AI_SERVICES="${QUBINODE_ENABLE_AI_SERVICES:-false}"
export EMBEDDING_SERVICE_PORT="${EMBEDDING_SERVICE_PORT:-8891}"
export LITELLM_PROXY_PORT="${LITELLM_PROXY_PORT:-4000}"

# Internal variables
DEPLOYMENT_LOG="/tmp/qubinode-deployment-$(date +%Y%m%d-%H%M%S).log"
AI_ASSISTANT_CONTAINER=""
DEPLOYMENT_FAILED=false

# Set working directory - use repository root calculated earlier
# MY_DIR is the parent of the repository (where qubinode_navigator folder lives)
MY_DIR="$(dirname "$REPO_ROOT")"

# Export REPO_ROOT for use in functions
export REPO_ROOT

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
    ╔═════════════════════════════════════════════════════════════════════╗
    ║                                                                     ║
    ║   ██████  ██    ██ ██████  ██ ███    ██  ██████  ██████  ███████    ║
    ║  ██    ██ ██    ██ ██   ██ ██ ████   ██ ██    ██ ██   ██ ██         ║
    ║  ██    ██ ██    ██ ██████  ██ ██ ██  ██ ██    ██ ██   ██ █████      ║
    ║  ██ ▄▄ ██ ██    ██ ██   ██ ██ ██  ██ ██ ██    ██ ██   ██ ██         ║
    ║   ██████   ██████  ██████  ██ ██   ████  ██████  ██████  ███████    ║
    ║      ▀▀                                                             ║
    ║                                                                     ║
    ║                NAVIGATOR ONE-SHOT DEPLOYMENT                        ║
    ║                                                                     ║
    ╚═════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo -e "${BLUE}Version: ${SCRIPT_VERSION}${NC}"
    echo -e "${BLUE}Target: RHEL-based systems (RHEL, CentOS, Rocky Linux)${NC}"
    echo -e "${BLUE}Mode: ${QUBINODE_DEPLOYMENT_MODE}${NC}"
    echo ""
}

# OS Detection Engine - Refactored from setup.sh with modern OS support
get_rhel_version() {
    log_info "Detecting operating system..."

    if [[ ! -f /etc/redhat-release ]]; then
        log_error "This script requires a RHEL-based operating system"
        return 1
    fi

    local os_info=$(cat /etc/redhat-release)
    log_info "Detected OS: $os_info"

    # Modern RHEL-based OS detection (removes RHEL 8, adds RHEL 10/CentOS 10)
    if [[ $os_info =~ "Red Hat Enterprise Linux release 10" ]]; then
        export BASE_OS="RHEL10"
        export OS_TYPE="rhel"
        export OS_VERSION="10"
    elif [[ $os_info =~ "Red Hat Enterprise Linux release 9" ]]; then
        export BASE_OS="RHEL9"
        export OS_TYPE="rhel"
        export OS_VERSION="9"
    elif [[ $os_info =~ "CentOS Stream release 10" ]]; then
        export BASE_OS="CENTOS10"
        export OS_TYPE="centos"
        export OS_VERSION="10"
    elif [[ $os_info =~ "CentOS Stream release 9" ]]; then
        export BASE_OS="CENTOS9"
        export OS_TYPE="centos"
        export OS_VERSION="9"
    elif [[ $os_info =~ "Rocky Linux release 9" ]]; then
        export BASE_OS="ROCKY9"
        export OS_TYPE="rocky"
        export OS_VERSION="9"
    elif [[ $os_info =~ "AlmaLinux release 9" ]]; then
        export BASE_OS="ALMA9"
        export OS_TYPE="alma"
        export OS_VERSION="9"
    elif [[ $os_info =~ "Red Hat Enterprise Linux release 8" ]]; then
        log_error "RHEL 8 is no longer supported. Please upgrade to RHEL 9 or 10."
        log_error "Migration guide: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/upgrading_from_rhel_8_to_rhel_9/index"
        ask_ai_for_help "rhel8_unsupported" "RHEL 8 detected but no longer supported. Need upgrade guidance."
        return 1
    else
        log_error "Unsupported operating system: $os_info"
        log_error "Supported OS versions:"
        log_error "  - RHEL 9.x or 10.x"
        log_error "  - CentOS Stream 9 or 10"
        log_error "  - Rocky Linux 9.x"
        log_error "  - AlmaLinux 9.x"
        ask_ai_for_help "unsupported_os" "Unsupported OS detected: $os_info"
        return 1
    fi

    log_success "OS Detection: $BASE_OS (Type: $OS_TYPE, Version: $OS_VERSION)"
    return 0
}

# Deployment Target Detection - Based on research of existing patterns
detect_deployment_target() {
    log_info "Detecting deployment target and configuration..."

    # Check for existing deployment configurations
    if [[ -f "$SCRIPT_DIR/notouch.env" ]]; then
        log_info "Found existing notouch.env configuration"
        source "$SCRIPT_DIR/notouch.env" || {
            log_warning "Failed to source notouch.env, continuing..."
        }
    fi

    # Detect deployment target based on environment or domain
    local deployment_target="unknown"

    if [[ "$QUBINODE_DOMAIN" =~ "hetzner" || "$QUBINODE_DOMAIN" =~ "qubinodelab.io" || "$INVENTORY" == "hetzner" ]]; then
        deployment_target="hetzner"
        export DEPLOYMENT_TARGET="hetzner"
        export INVENTORY="${INVENTORY:-hetzner}"
        export FORWARDER="${FORWARDER:-1.1.1.1}"
        export INTERFACE="${INTERFACE:-bond0}"
        log_info "Detected Hetzner Cloud deployment target"
    elif [[ "$QUBINODE_DOMAIN" =~ "opentlc.com" || "$QUBINODE_DOMAIN" =~ "redhat.com" || "$INVENTORY" == "rhel9-equinix" ]]; then
        deployment_target="equinix"
        export DEPLOYMENT_TARGET="equinix"
        export INVENTORY="${INVENTORY:-rhel9-equinix}"
        # Auto-detect forwarder from /etc/resolv.conf for Equinix
        export FORWARDER="${FORWARDER:-$(awk '/^nameserver/ {print $2}' /etc/resolv.conf | head -1)}"
        export INTERFACE="${INTERFACE:-bond0}"
        log_info "Detected Red Hat Demo System (Equinix) deployment target"
    elif [[ "$QUBINODE_DOMAIN" =~ "dev.local" || "$INVENTORY" == "localhost" ]]; then
        deployment_target="local"
        export DEPLOYMENT_TARGET="local"
        export INVENTORY="${INVENTORY:-localhost}"
        export FORWARDER="${FORWARDER:-8.8.8.8}"
        export INTERFACE="${INTERFACE:-$(ip route | grep default | awk '{print $5}' | head -1)}"
        log_info "Detected local development deployment target"
    else
        deployment_target="custom"
        export DEPLOYMENT_TARGET="custom"
        export INVENTORY="${INVENTORY:-localhost}"
        export FORWARDER="${FORWARDER:-8.8.8.8}"
        export INTERFACE="${INTERFACE:-$(ip route | grep default | awk '{print $5}' | head -1)}"
        log_info "Using custom deployment configuration"
    fi

    # Set deployment-specific defaults
    export CICD_PIPELINE="${CICD_PIPELINE:-true}"
    export ENV_USERNAME="${ENV_USERNAME:-$SSH_USER}"
    export KVM_VERSION="${KVM_VERSION:-latest}"
    export CICD_ENVIORNMENT="${CICD_ENVIORNMENT:-gitlab}"
    export ACTIVE_BRIDGE="${ACTIVE_BRIDGE:-false}"
    export USE_ROUTE53="${USE_ROUTE53:-false}"
    export DISK="${DISK:-skip}"  # Default to skip disk selection for automated deployment

    log_success "Deployment target: $deployment_target (Inventory: $INVENTORY)"
    log_info "Network configuration: Interface=$INTERFACE, Forwarder=$FORWARDER"

    return 0
}

check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check if running as root (skip in CI/CD pipeline environments)
    if [[ $EUID -ne 0 ]]; then
        if [[ "${CICD_PIPELINE:-false}" == "true" ]]; then
            log_warning "Running as non-root user in CI/CD pipeline mode"
        else
            log_error "This script must be run as root"
            log_info "Tip: Set CICD_PIPELINE=true to run in CI/CD mode without root"
            return 1
        fi
    fi

    # Check system resources
    local mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    local disk_gb=$(df / | awk 'NR==2{print int($4/1024/1024)}')

    log_info "System Resources:"
    log_info "  Memory: ${mem_gb}GB"
    log_info "  Disk Space: ${disk_gb}GB available"

    if [[ $mem_gb -lt 8 ]]; then
        log_warning "Minimum 8GB RAM recommended (found ${mem_gb}GB)"
    fi

    if [[ $disk_gb -lt 50 ]]; then
        log_warning "Minimum 50GB disk space recommended (found ${disk_gb}GB available)"
    fi

    # Check network connectivity
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        log_error "No internet connectivity detected"
        return 1
    fi

    log_success "Prerequisites check completed"
    return 0
}

validate_configuration() {
    log_step "Validating configuration..."

    # Check required variables
    local required_vars=(
        "QUBINODE_DOMAIN"
        "QUBINODE_ADMIN_USER"
        "QUBINODE_CLUSTER_NAME"
    )

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            return 1
        fi
    done

    # Validate domain format (supports subdomains like e2e.qubinode.local)
    if [[ ! $QUBINODE_DOMAIN =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)+$ ]]; then
        log_error "Invalid domain format: $QUBINODE_DOMAIN"
        return 1
    fi

    # Validate that admin user exists on the system
    if ! id "$QUBINODE_ADMIN_USER" &>/dev/null; then
        log_error "User '$QUBINODE_ADMIN_USER' does not exist on this system"
        log_error "Available non-root users:"
        getent passwd | awk -F: -v min="$MIN_USER_UID" -v max="$MAX_USER_UID" \
            '$3 >= min && $3 < max {print "  - " $1}' || true
        log_error ""
        log_error "To fix this issue:"
        log_error "  1. Set QUBINODE_ADMIN_USER in .env to an existing user"
        log_error "  2. Or create the user: sudo useradd -m $QUBINODE_ADMIN_USER"
        log_error "  3. Or run the script as the target user (it will be auto-detected)"
        return 1
    fi

    log_success "Configuration validation completed"
    log_info "Using admin user: $QUBINODE_ADMIN_USER"
    return 0
}

# =============================================================================
# AI ASSISTANT INTEGRATION
# =============================================================================

start_ai_assistant() {
    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" != "true" ]]; then
        log_info "AI Assistant disabled, skipping..."
        return 0
    fi

    log_step "Starting AI Assistant for troubleshooting support..."

    # Check if podman is available
    if ! command -v podman &> /dev/null; then
        log_info "Podman not found, installing for AI Assistant..."
        if ! dnf install -y podman; then
            log_warning "Failed to install podman, AI Assistant will not be available"
            return 1
        fi
        log_success "Podman installed successfully"
    fi

    # Check if AI Assistant container is already running
    if podman ps --format "{{.Names}}" | grep -q "^qubinode-ai-assistant$"; then
        log_info "AI Assistant container is already running"
        # Verify it's accessible
        if curl -s http://localhost:${AI_ASSISTANT_PORT}/health &> /dev/null; then
            log_success "AI Assistant is ready at http://localhost:${AI_ASSISTANT_PORT}"
            AI_ASSISTANT_CONTAINER="qubinode-ai-assistant"
            log_ai "I'm already running and ready to help with deployment issues!"
            return 0
        else
            log_warning "AI Assistant container exists but not responding, restarting..."
            podman stop qubinode-ai-assistant &> /dev/null || true
            podman rm qubinode-ai-assistant &> /dev/null || true
        fi
    fi

    # Create required directories for bind mounts
    # These directories are excluded by .gitignore but required for container operation
    log_info "Creating required directories for AI Assistant..."
    mkdir -p "${REPO_ROOT}/ai-assistant/data/rag-docs"
    mkdir -p "${REPO_ROOT}/ai-assistant/data/vector-db"

    # Set ownership to match container user (UID 1001, GID 0 per Dockerfile)
    # This ensures the container can read/write to mounted directories
    if command -v chown &> /dev/null; then
        chown -R 1001:0 "${REPO_ROOT}/ai-assistant/data" 2>/dev/null || {
            log_warning "Could not set ownership on data directory, container will use SELinux context or existing permissions"
        }
    fi

    log_success "Data directories created successfully"

    # Validate and log model configuration
    log_info "AI Model Configuration:"
    log_info "  Manager Model: ${MANAGER_MODEL}"
    log_info "  Developer Model: ${DEVELOPER_MODEL}"
    log_info "  Deployment Model: ${PYDANTICAI_MODEL}"
    if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
        log_info "  OpenRouter API Key: [SET]"
    fi
    if [[ -n "${GEMINI_API_KEY:-}" ]]; then
        log_info "  Gemini API Key: [SET]"
    fi
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        log_info "  Anthropic API Key: [SET]"
    fi
    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        log_info "  OpenAI API Key: [SET]"
    fi

    # Determine image source: build from source or pull from registry
    local ai_image=""

    if [[ "$BUILD_AI_ASSISTANT_FROM_SOURCE" == "true" ]]; then
        log_info "Building AI Assistant from source (includes PydanticAI + Smart Pipeline)..."
        build_ai_assistant_from_source || {
            log_warning "Failed to build from source, falling back to registry image"
            BUILD_AI_ASSISTANT_FROM_SOURCE="false"
        }
        ai_image="localhost/qubinode-ai-assistant:latest"
    fi

    if [[ "$BUILD_AI_ASSISTANT_FROM_SOURCE" != "true" ]]; then
        # Pull from registry
        log_info "Pulling AI Assistant container from registry..."
        if podman pull quay.io/takinosh/qubinode-ai-assistant:${AI_ASSISTANT_VERSION}; then
            ai_image="quay.io/takinosh/qubinode-ai-assistant:${AI_ASSISTANT_VERSION}"
        else
            log_warning "Failed to pull AI Assistant container, continuing without AI support"
            return 1
        fi
    fi

    # Start the container
    log_info "Starting AI Assistant container..."
    # Mount directories for:
    # - /app/data: RAG data, embeddings, cache
    # - /app/airflow/dags: DAG discovery for PydanticAI orchestrator (ADR-0066)
    # - /app/docs/adrs: ADR files for context
    # Note: AIRFLOW_USER/AIRFLOW_PASSWORD will be updated after orchestrator user is created
    AI_ASSISTANT_CONTAINER=$(podman run -d \
        --name qubinode-ai-assistant \
        -p ${AI_ASSISTANT_PORT}:8080 \
        -e DEPLOYMENT_MODE=${QUBINODE_DEPLOYMENT_MODE} \
        -e LOG_LEVEL=INFO \
        -e MARQUEZ_API_URL=http://host.containers.internal:5001 \
        -e AIRFLOW_API_URL=http://host.containers.internal:8888 \
        -e AIRFLOW_DAGS_PATH=/app/airflow/dags \
        -e PROJECT_ROOT=/app \
        -e QUBINODE_MCP_URL=http://host.containers.internal:8889/sse \
        ${AIRFLOW_USER:+-e AIRFLOW_USER="${AIRFLOW_USER}"} \
        ${AIRFLOW_PASSWORD:+-e AIRFLOW_PASSWORD="${AIRFLOW_PASSWORD}"} \
        ${OPENROUTER_API_KEY:+-e OPENROUTER_API_KEY="${OPENROUTER_API_KEY}"} \
        ${GEMINI_API_KEY:+-e GEMINI_API_KEY="${GEMINI_API_KEY}"} \
        ${ANTHROPIC_API_KEY:+-e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"} \
        ${OPENAI_API_KEY:+-e OPENAI_API_KEY="${OPENAI_API_KEY}"} \
        ${MANAGER_MODEL:+-e MANAGER_MODEL="${MANAGER_MODEL}"} \
        ${DEVELOPER_MODEL:+-e DEVELOPER_MODEL="${DEVELOPER_MODEL}"} \
        ${PYDANTICAI_MODEL:+-e PYDANTICAI_MODEL="${PYDANTICAI_MODEL}"} \
        -v "${REPO_ROOT}/ai-assistant/data:/app/data:z" \
        -v "${REPO_ROOT}/ai-assistant/src:/app/src:ro,z" \
        -v "${REPO_ROOT}/airflow/dags:/app/airflow/dags:ro,z" \
        -v "${REPO_ROOT}/docs/adrs:/app/docs/adrs:ro,z" \
        -v "${REPO_ROOT}/intent_parser:/app/intent_parser:ro,z" \
        "$ai_image")

    # Wait for AI Assistant to be ready
    # Initial startup can take time for:
    # - Model initialization (if USE_LOCAL_MODEL=true)
    # - RAG service setup and document loading
    # - PydanticAI agent context initialization
    log_info "Waiting for AI Assistant to be ready (may take up to 2 minutes for initial startup)..."
    local max_attempts=60  # 2 minutes with 2-second intervals
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:${AI_ASSISTANT_PORT}/health &> /dev/null; then
            log_success "AI Assistant is ready at http://localhost:${AI_ASSISTANT_PORT}"
            log_ai "You can ask me for help if you encounter any issues during deployment!"
            return 0
        fi

        # Show progress every 10 seconds
        if [ $((attempt % 5)) -eq 0 ]; then
            log_info "Still waiting... (attempt $attempt/$max_attempts)"
        fi

        sleep 2
        attempt=$((attempt + 1))
    done

    log_warning "AI Assistant started but health check failed after $((max_attempts * 2)) seconds"
    log_warning "Container may still be starting up. Check logs with: podman logs qubinode-ai-assistant"
    log_warning "To troubleshoot: curl -v http://localhost:${AI_ASSISTANT_PORT}/health"

    # Non-fatal: allow deployment to continue even if AI Assistant isn't ready yet
    return 1
}

# Build AI Assistant container from source with all dependencies
# This includes PydanticAI, Smart Pipeline, OpenLineage integration
build_ai_assistant_from_source() {
    log_step "Building AI Assistant from source..."

    local ai_assistant_dir="$REPO_ROOT/ai-assistant"

    if [[ ! -d "$ai_assistant_dir" ]]; then
        log_error "AI Assistant directory not found: $ai_assistant_dir"
        return 1
    fi

    cd "$ai_assistant_dir" || return 1

    # Ensure build script exists
    if [[ ! -f "scripts/build.sh" ]]; then
        log_error "Build script not found: scripts/build.sh"
        return 1
    fi

    # Run the build script
    # Use --no-cache in CI/CD to ensure fresh source files are used
    log_info "Running AI Assistant build script..."
    local build_args="--no-test"
    if [[ "$CICD_PIPELINE" == "true" ]]; then
        log_info "CI/CD mode detected - building without cache"
        build_args="--no-test --no-cache"
    fi
    if bash scripts/build.sh $build_args; then
        log_success "AI Assistant container built successfully"

        # Verify image exists
        if podman images localhost/qubinode-ai-assistant:latest --format "{{.Repository}}" | grep -q "qubinode-ai-assistant"; then
            log_success "AI Assistant image verified: localhost/qubinode-ai-assistant:latest"
            return 0
        else
            log_error "AI Assistant image not found after build"
            return 1
        fi
    else
        log_error "AI Assistant build failed"
        return 1
    fi
}

ask_ai_for_help() {
    local error_context="$1"
    local error_message="$2"
    local lifecycle_stage="${3:-deployment}" # Default to 'deployment' (Strict SRE)

    if [[ -z "$AI_ASSISTANT_CONTAINER" ]]; then
        log_warning "AI Assistant not available for troubleshooting"
        return 1
    fi

    log_ai "Consulting AI Assistant (Persona: $lifecycle_stage)..."

    # 1. Define Prompt based on Lifecycle Stage
    local system_prompt=""

    if [[ "$lifecycle_stage" == "operational" ]] || [[ "${DEVELOPMENT_MODE:-false}" == "true" ]]; then
        # === MODE: DEVELOPER / ARCHITECT ===
        system_prompt="ROLE: Qubinode System Architect.
STATUS: System is RUNNING.
GOAL: Add features, refactor code, and optimize workflows.
CONTEXT: The user has a working system and wants to extend it."
    else
        # === MODE: STRICT SRE (Default for Installer) ===
        system_prompt="ROLE: Site Reliability Engineer (SRE).
STATUS: Deployment in progress (Critical Phase).
RULES:
1. NO Code Refactoring: Do not rewrite 'deploy-qubinode.sh' or core Python files.
2. Fix Environment: Focus on DNS, Disk, Permissions, and Packages.
3. Create Issues: If code is broken, generate a GitHub Issue link.
4. Unlock: If the user explicitly says 'The system is running', you may switch to Developer mode."
    fi

    # Prepare context for AI Assistant
    local context_data=$(cat << EOF
{
    "lifecycle_stage": "$lifecycle_stage",
    "deployment_context": {
        "os_type": "$OS_TYPE",
        "os_version": "$OS_VERSION",
        "deployment_mode": "$QUBINODE_DEPLOYMENT_MODE",
        "cluster_name": "$QUBINODE_CLUSTER_NAME",
        "domain": "$QUBINODE_DOMAIN",
        "development_mode": "${DEVELOPMENT_MODE:-false}"
    },
    "error_context": "$error_context",
    "error_message": "$error_message",
    "system_info": {
        "memory_gb": $(free -g | awk '/^Mem:/{print $2}'),
        "disk_space_gb": $(df / | awk 'NR==2{print int($4/1024/1024)}'),
        "timestamp": "$(date -Iseconds)"
    }
}
EOF
    )

    # Query AI Assistant for help
    # Properly escape the context data for JSON
    local escaped_context=$(echo "$context_data" | jq -R -s .)
    local ai_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$system_prompt\n\nCONTEXT: $escaped_context\", \"max_tokens\": 800}" \
        http://localhost:${AI_ASSISTANT_PORT}/chat 2>/dev/null)

    if [[ $? -eq 0 ]] && [[ -n "$ai_response" ]]; then
        # Format header with proper padding for variable lifecycle_stage length
        local mode_text="AI GUIDANCE ($lifecycle_stage mode)"
        local padding_length=$((62 - ${#mode_text}))
        local padding=$(printf '%*s' $padding_length '')

        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║   ${mode_text}${padding}║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo "$ai_response" | jq -r '.text // .message // .' 2>/dev/null || echo "$ai_response"
        echo ""
        echo -e "${CYAN}For more help, visit: http://localhost:${AI_ASSISTANT_PORT}${NC}"
        return 0
    else
        log_warning "Could not get AI assistance at this time"
        return 1
    fi
}

# =============================================================================
# AIRFLOW ORCHESTRATION INTEGRATION
# =============================================================================

# Create orchestrator service account for AI Assistant PydanticAI integration
# This dedicated user has 'Op' role (can trigger DAGs but not admin access)
create_orchestrator_user() {
    log_info "Creating Airflow orchestrator service account..."

    # Generate a random password
    local orchestrator_password
    orchestrator_password=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)

    # Check if user already exists
    if podman exec airflow_airflow-webserver_1 airflow users list 2>/dev/null | grep -q orchestrator; then
        log_info "Orchestrator user already exists, updating password..."
        podman exec airflow_airflow-webserver_1 airflow users reset-password \
            --username orchestrator \
            --password "$orchestrator_password" 2>/dev/null || {
            log_warning "Could not update orchestrator password"
            return 1
        }
    else
        # Create new user with Op role
        podman exec airflow_airflow-webserver_1 airflow users create \
            --username orchestrator \
            --password "$orchestrator_password" \
            --firstname PydanticAI \
            --lastname Orchestrator \
            --email orchestrator@qubinode.local \
            --role Op 2>/dev/null || {
            log_warning "Could not create orchestrator user"
            return 1
        }
    fi

    # Store credentials securely
    local creds_dir="$REPO_ROOT/.credentials"
    mkdir -p "$creds_dir"
    chmod 700 "$creds_dir"

    local creds_file="$creds_dir/airflow-orchestrator.env"
    cat > "$creds_file" << EOF
# Airflow Orchestrator Service Account
# Generated: $(date -Iseconds)
# Used by: AI Assistant PydanticAI Orchestrator
AIRFLOW_USER=orchestrator
AIRFLOW_PASSWORD=$orchestrator_password
EOF
    chmod 600 "$creds_file"

    # Export for current session (used by AI Assistant startup)
    export AIRFLOW_USER=orchestrator
    export AIRFLOW_PASSWORD="$orchestrator_password"

    # Update .env if it exists
    if [[ -f "$REPO_ROOT/.env" ]]; then
        sed -i '/^AIRFLOW_USER=/d' "$REPO_ROOT/.env"
        sed -i '/^AIRFLOW_PASSWORD=/d' "$REPO_ROOT/.env"
        echo "" >> "$REPO_ROOT/.env"
        echo "# Airflow Orchestrator Credentials (auto-generated)" >> "$REPO_ROOT/.env"
        echo "AIRFLOW_USER=orchestrator" >> "$REPO_ROOT/.env"
        echo "AIRFLOW_PASSWORD=$orchestrator_password" >> "$REPO_ROOT/.env"
    fi

    log_success "Orchestrator service account created (credentials: $creds_file)"
    return 0
}

# Restart AI Assistant container with orchestrator credentials
# Called after Airflow orchestrator user is created
restart_ai_assistant_with_credentials() {
    log_info "Stopping AI Assistant to update credentials..."
    podman stop qubinode-ai-assistant &>/dev/null || true
    podman rm qubinode-ai-assistant &>/dev/null || true

    # Determine image to use
    local ai_image
    if podman images localhost/qubinode-ai-assistant:latest --format "{{.Repository}}" 2>/dev/null | grep -q "qubinode-ai-assistant"; then
        ai_image="localhost/qubinode-ai-assistant:latest"
    else
        ai_image="quay.io/takinosh/qubinode-ai-assistant:${AI_ASSISTANT_VERSION:-latest}"
    fi

    log_info "Starting AI Assistant with orchestrator credentials..."
    # USE_LOCAL_MODEL controls whether to start llama.cpp + Granite model
    # Default: false (cloud-only mode for faster CI startup)
    local use_local_model="${USE_LOCAL_MODEL:-false}"
    log_info "USE_LOCAL_MODEL=${use_local_model}"
    AI_ASSISTANT_CONTAINER=$(podman run -d \
        --name qubinode-ai-assistant \
        --network host \
        -e DEPLOYMENT_MODE=${QUBINODE_DEPLOYMENT_MODE:-production} \
        -e LOG_LEVEL=INFO \
        -e USE_LOCAL_MODEL="${use_local_model}" \
        -e MARQUEZ_API_URL=http://localhost:5001 \
        -e AIRFLOW_API_URL=http://localhost:8888 \
        -e AIRFLOW_DAGS_PATH=/app/airflow/dags \
        -e PROJECT_ROOT=/app \
        -e QUBINODE_MCP_URL=http://localhost:8889/sse \
        -e AIRFLOW_USER="${AIRFLOW_USER}" \
        -e AIRFLOW_PASSWORD="${AIRFLOW_PASSWORD}" \
        ${OPENROUTER_API_KEY:+-e OPENROUTER_API_KEY="${OPENROUTER_API_KEY}"} \
        ${GEMINI_API_KEY:+-e GEMINI_API_KEY="${GEMINI_API_KEY}"} \
        ${ANTHROPIC_API_KEY:+-e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"} \
        ${OPENAI_API_KEY:+-e OPENAI_API_KEY="${OPENAI_API_KEY}"} \
        ${MANAGER_MODEL:+-e MANAGER_MODEL="${MANAGER_MODEL}"} \
        ${DEVELOPER_MODEL:+-e DEVELOPER_MODEL="${DEVELOPER_MODEL}"} \
        ${PYDANTICAI_MODEL:+-e PYDANTICAI_MODEL="${PYDANTICAI_MODEL}"} \
        -v "${REPO_ROOT}/ai-assistant/data:/app/data:z" \
        -v "${REPO_ROOT}/ai-assistant/src:/app/src:ro,z" \
        -v "${REPO_ROOT}/airflow/dags:/app/airflow/dags:ro,z" \
        -v "${REPO_ROOT}/docs/adrs:/app/docs/adrs:ro,z" \
        -v "${REPO_ROOT}/intent_parser:/app/intent_parser:ro,z" \
        "$ai_image")

    # Wait for AI Assistant to be ready using podman health check + endpoint verification
    # With USE_LOCAL_MODEL=false, startup is fast (no model download)
    # With USE_LOCAL_MODEL=true, may take 2-5 minutes for model download
    if [[ "$use_local_model" == "true" ]]; then
        log_info "Waiting for AI Assistant to be ready (model download may take 2-5 minutes)..."
    else
        log_info "Waiting for AI Assistant to be ready (cloud-only mode, should be fast)..."
    fi
    local port=${AI_ASSISTANT_PORT:-8080}
    local max_wait=360  # 6 minutes
    local check_interval=5
    local elapsed=0
    local last_status=""
    local progress_shown=false

    while [[ $elapsed -lt $max_wait ]]; do
        # Check if container is still running
        if ! podman ps --format "{{.Names}}" 2>/dev/null | grep -q "^qubinode-ai-assistant$"; then
            log_error "Container stopped running during startup"
            log_info "Container logs:"
            podman logs qubinode-ai-assistant 2>&1 | tail -50 || true
            return 1
        fi

        # Get container health status via podman inspect
        local health_status
        health_status=$(podman inspect --format='{{.State.Health.Status}}' qubinode-ai-assistant 2>/dev/null || echo "unknown")

        case "$health_status" in
            "healthy")
                log_success "Container health check passed after ${elapsed}s"
                # Now verify orchestrator endpoint is available
                local orch_status
                orch_status=$(curl -s "http://localhost:${port}/orchestrator/status" 2>/dev/null)
                if echo "$orch_status" | grep -q '"available"'; then
                    log_success "AI Assistant restarted with orchestrator credentials"
                    log_info "Orchestrator status: $(echo "$orch_status" | jq -c '{available, api_keys: .api_keys_configured}' 2>/dev/null || echo 'OK')"
                    return 0
                else
                    log_warning "Health OK but orchestrator endpoint not available yet"
                    log_info "This may indicate an import error - checking logs..."
                    podman logs qubinode-ai-assistant 2>&1 | grep -v "GET /\|POST /" | tail -30 || true
                fi
                ;;
            "starting")
                # Container is still starting (model download in progress)
                if [[ $((elapsed % 30)) -eq 0 ]] && [[ $elapsed -gt 0 ]]; then
                    log_info "Container starting... (${elapsed}s elapsed)"
                    # Show download progress if available
                    podman logs qubinode-ai-assistant 2>&1 | grep -i "download progress\|downloading" | tail -1 || true
                fi
                ;;
            "unhealthy")
                log_error "Container health check failed"
                log_info "Container logs:"
                podman logs qubinode-ai-assistant 2>&1 | tail -100 || true
                return 1
                ;;
            *)
                # No health status yet or unknown - try endpoint directly
                local http_code
                http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}/health" 2>/dev/null || echo "000")
                if [[ "$http_code" == "200" ]]; then
                    log_success "Health endpoint responding (HTTP 200) after ${elapsed}s"
                    # Check orchestrator
                    local orch_status
                    orch_status=$(curl -s "http://localhost:${port}/orchestrator/status" 2>/dev/null)
                    if echo "$orch_status" | grep -q '"available"'; then
                        log_success "AI Assistant ready with orchestrator"
                        return 0
                    fi
                elif [[ "$http_code" == "503" ]] && [[ "$progress_shown" == "false" ]]; then
                    progress_shown=true
                    log_info "Service starting up (HTTP 503)..."
                fi
                ;;
        esac

        sleep "$check_interval"
        elapsed=$((elapsed + check_interval))
    done

    log_error "AI Assistant failed to start after ${max_wait}s"
    log_info "=== CONTAINER STATUS ==="
    podman inspect --format='Status: {{.State.Status}}, Health: {{.State.Health.Status}}' qubinode-ai-assistant 2>/dev/null || true
    log_info "=== CONTAINER LOGS (errors) ==="
    podman logs qubinode-ai-assistant 2>&1 | grep -iE "(error|exception|traceback|failed|cannot)" | head -30 || true
    log_info "=== FULL STARTUP LOGS ==="
    podman logs qubinode-ai-assistant 2>&1 | grep -v "GET /\|POST /" | head -100 || true
    return 1
}

deploy_airflow_services() {
    if [[ "$QUBINODE_ENABLE_AIRFLOW" != "true" ]]; then
        log_info "Airflow deployment disabled, skipping..."
        return 0
    fi

    log_step "Deploying Apache Airflow for workflow orchestration..."

    # Check if podman is available
    if ! command -v podman &> /dev/null; then
        log_warning "Podman not found, Airflow will not be available"
        return 1
    fi

    # Check if podman-compose is available
    if ! command -v podman-compose &> /dev/null; then
        log_info "Installing podman-compose for Airflow..."
        ensure_uv
        if ! uv pip install --system podman-compose; then
            log_warning "Failed to install podman-compose, skipping Airflow deployment"
            return 1
        fi
        log_success "podman-compose installed successfully"
    fi

    # Change to airflow directory - calculate relative to repo root
    # SCRIPT_DIR is /path/to/qubinode_navigator/scripts/development
    # repo_root is /path/to/qubinode_navigator (go up two levels from SCRIPT_DIR)
    local repo_root="$(dirname "$(dirname "$SCRIPT_DIR")")"
    local airflow_dir="$repo_root/airflow"
    if [[ ! -d "$airflow_dir" ]]; then
        log_warning "Airflow directory not found at $airflow_dir, skipping Airflow deployment"
        return 1
    fi

    cd "$airflow_dir" || {
        log_warning "Failed to change to airflow directory, skipping Airflow deployment"
        return 1
    }

    # Enable Airflow in configuration
    log_info "Enabling Airflow services..."
    export ENABLE_AIRFLOW="true"

    # Call the dedicated Airflow deployment script
    log_info "Starting Airflow services via deploy-airflow.sh..."
    if bash ./deploy-airflow.sh deploy; then
        log_success "Airflow deployment initiated successfully"

        # Wait for Airflow to be ready
        log_info "Waiting for Airflow webserver to be ready on port ${AIRFLOW_PORT}..."
        for i in {1..60}; do
            if curl -s http://localhost:${AIRFLOW_PORT}/health &> /dev/null; then
                log_success "Airflow webserver is ready at http://localhost:${AIRFLOW_PORT}"

                # Create orchestrator service account for AI Assistant (ADR-0066)
                create_orchestrator_user

                # Restart AI Assistant with orchestrator credentials if running
                if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]]; then
                    if podman ps --format "{{.Names}}" | grep -q "^qubinode-ai-assistant$"; then
                        log_info "Restarting AI Assistant with orchestrator credentials..."
                        restart_ai_assistant_with_credentials
                    else
                        log_warning "AI Assistant not running - start it with orchestrator credentials"
                    fi
                fi

                return 0
            fi
            sleep 2
        done

        log_warning "Airflow webserver health check did not complete in time, but services may still be running"
        return 0
    else
        log_error "Airflow deployment failed"
        ask_ai_for_help "airflow_deploy" "Airflow deployment via deploy-airflow.sh failed"
        return 1
    fi
}

# =============================================================================
# ADR-0050: HOST AI SERVICES (Hybrid Architecture)
# =============================================================================
# These services run on the host (not in containers) to:
# - Reduce container image size from 10.5GB to ~2-3GB
# - Allow GPU access for embedding models
# - Share services across multiple tools

deploy_host_ai_services() {
    if [[ "$QUBINODE_ENABLE_AI_SERVICES" != "true" ]]; then
        log_info "Host AI services disabled, skipping..."
        return 0
    fi

    log_step "Deploying Host AI Services (ADR-0050)..."

    # Check if the install script exists
    local install_script="$SCRIPT_DIR/airflow/host-services/install-host-services.sh"
    if [[ ! -f "$install_script" ]]; then
        log_error "Host services install script not found: $install_script"
        return 1
    fi

    # Run the install script
    log_info "Installing Embedding Service and LiteLLM Proxy..."
    if bash "$install_script"; then
        log_success "Host AI services installed successfully"
    else
        log_error "Host AI services installation failed"
        ask_ai_for_help "ai_services_install" "Host AI services installation failed"
        return 1
    fi

    # Verify services are running
    log_info "Verifying host AI services..."
    local services_ok=true

    # Check Embedding Service
    if systemctl is-active --quiet qubinode-embedding.service; then
        log_success "Embedding Service running on port ${EMBEDDING_SERVICE_PORT}"
    else
        log_warning "Embedding Service not running"
        services_ok=false
    fi

    # Check LiteLLM Proxy
    if systemctl is-active --quiet qubinode-litellm.service; then
        log_success "LiteLLM Proxy running on port ${LITELLM_PROXY_PORT}"
    else
        log_warning "LiteLLM Proxy not running"
        services_ok=false
    fi

    # Health checks
    sleep 5
    if curl -s http://localhost:${EMBEDDING_SERVICE_PORT}/health > /dev/null 2>&1; then
        log_success "Embedding Service health check passed"
    else
        log_warning "Embedding Service health check failed (may still be starting)"
    fi

    if curl -s http://localhost:${LITELLM_PROXY_PORT}/health > /dev/null 2>&1; then
        log_success "LiteLLM Proxy health check passed"
    else
        log_warning "LiteLLM Proxy health check failed (may still be starting)"
    fi

    if [[ "$services_ok" == "true" ]]; then
        log_success "All host AI services deployed successfully"
        return 0
    else
        log_warning "Some host AI services failed to start, but deployment continues"
        return 0  # Non-blocking
    fi
}

setup_nginx_reverse_proxy() {
    if [[ "$QUBINODE_ENABLE_AIRFLOW" != "true" ]]; then
        log_info "Airflow not enabled, skipping nginx reverse proxy setup..."
        return 0
    fi

    log_step "Setting up nginx reverse proxy for unified access..."

    # Install nginx if not present
    if ! command -v nginx &> /dev/null; then
        log_info "Installing nginx..."
        if ! dnf install -y nginx; then
            log_warning "Failed to install nginx, skipping reverse proxy setup"
            return 1
        fi
        log_success "nginx installed successfully"
    fi

    # Create nginx configuration for Airflow and AI Assistant
    log_info "Creating nginx reverse proxy configuration..."
    cat > /etc/nginx/conf.d/qubinode.conf << 'NGINX_CONF'
# Qubinode Navigator - Nginx Reverse Proxy
# Provides unified access to Airflow and AI Assistant

# Upstream definitions
upstream airflow_backend {
    server localhost:8888;
}

upstream ai_assistant_backend {
    server localhost:8080;
}

# HTTP server
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # Airflow UI at root
    location / {
        proxy_pass http://airflow_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for Airflow live updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # AI Assistant API at /ai/
    location /ai/ {
        proxy_pass http://ai_assistant_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://airflow_backend/health;
        access_log off;
    }
}
NGINX_CONF

    # Test nginx configuration
    log_info "Testing nginx configuration..."
    if ! nginx -t; then
        log_error "nginx configuration test failed"
        return 1
    fi
    log_success "nginx configuration is valid"

    # Enable and start nginx
    log_info "Starting nginx service..."
    if ! systemctl enable nginx; then
        log_warning "Failed to enable nginx for auto-start"
    fi

    if ! systemctl restart nginx; then
        log_error "Failed to start nginx"
        return 1
    fi

    if systemctl is-active --quiet nginx; then
        log_success "nginx reverse proxy is running"
    else
        log_error "nginx failed to start"
        return 1
    fi

    return 0
}

# =============================================================================
# DEPLOYMENT FUNCTIONS
# =============================================================================

# Package Installation Manager - Refactored from setup.sh
configure_os() {
    local base_os="$1"
    log_step "Configuring OS packages for $base_os..."

    # Update system first
    log_info "Updating system packages..."
    sudo dnf update -y || {
        log_error "Failed to update system packages"
        ask_ai_for_help "package_update" "dnf update failed for $base_os"
        return 1
    }

    # Install packages based on OS type
    case "$base_os" in
        "RHEL10")
            log_info "Installing RHEL 10 packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3 python3-pip python3-devel tar util-linux-user gcc podman ansible-core make sshpass || {
                log_error "Failed to install RHEL 10 packages"
                ask_ai_for_help "rhel10_packages" "Package installation failed for $base_os"
                return 1
            }
            log_info "Using Python 3.12 (default in RHEL 10)"
            ;;
        "RHEL9")
            log_info "Installing RHEL 9 packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3.11 python3.11-pip python3.11-devel tar util-linux-user gcc podman ansible-core make sshpass || {
                log_error "Failed to install RHEL 9 packages"
                ask_ai_for_help "rhel9_packages" "Package installation failed for $base_os"
                return 1
            }
            # Set Python 3.11 as default for ansible-navigator compatibility
            sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
            sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
            ;;
        "CENTOS10")
            log_info "Installing CentOS Stream 10 packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3 python3-pip python3-devel tar util-linux-user gcc podman ansible-core make sshpass || {
                log_error "Failed to install CentOS Stream 10 packages"
                ask_ai_for_help "centos10_packages" "Package installation failed for $base_os"
                return 1
            }
            log_info "Using Python 3.12 (default in CentOS Stream 10)"
            ;;
        "CENTOS9")
            log_info "Installing CentOS Stream 9 packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3.11 python3.11-pip python3.11-devel tar util-linux-user gcc podman ansible-core make sshpass || {
                log_error "Failed to install CentOS Stream 9 packages"
                ask_ai_for_help "centos9_packages" "Package installation failed for $base_os"
                return 1
            }
            # Set Python 3.11 as default for ansible-navigator compatibility
            sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
            sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
            ;;
        "ROCKY9"|"ALMA9")
            log_info "Installing Rocky/Alma Linux packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3-pip tar util-linux-user gcc python3-devel podman ansible-core make sshpass || {
                log_error "Failed to install Rocky/Alma packages"
                ask_ai_for_help "rocky_alma_packages" "Package installation failed for $base_os"
                return 1
            }
            ;;
        *)
            log_error "Unsupported OS for package configuration: $base_os"
            return 1
            ;;
    esac

    log_success "OS packages configured successfully for $base_os"
    return 0
}

# Enhanced package installation with development tools
install_packages() {
    log_step "Installing additional packages and development tools..."

    # Core packages required for containerized Ansible execution
    local core_packages=(
        "openssl-devel"
        "bzip2-devel"
        "libffi-devel"
        "wget"
        "vim"
        "podman"
        "ncurses-devel"
        "sqlite-devel"
        "firewalld"
        "make"
        "gcc"
        "git"
        "unzip"
        "sshpass"
        "lvm2"
        "python3"
        "python3-pip"
        "cockpit-leapp"
    )

    log_info "Installing core packages..."
    for package in "${core_packages[@]}"; do
        if rpm -q "$package" >/dev/null 2>&1; then
            log_info "Package $package already installed"
        else
            log_info "Installing package $package"
            sudo dnf install "$package" -y || {
                log_warning "Failed to install $package, continuing..."
            }
        fi
    done

    # Install Development Tools group
    if dnf group info "Development Tools" >/dev/null 2>&1; then
        log_info "Development Tools group already installed"
    else
        log_info "Installing Development Tools group..."
        sudo dnf groupinstall "Development Tools" -y || {
            log_warning "Failed to install Development Tools group"
        }
    fi

    log_success "Package installation completed"
    return 0
}

# SSH Configuration - Refactored from setup.sh
configure_ssh() {
    log_step "Configuring SSH..."

    # Determine the correct SSH key path based on admin user
    local ssh_dir ssh_key_path
    if [[ -n "${QUBINODE_ADMIN_USER:-}" && "${QUBINODE_ADMIN_USER}" != "root" ]]; then
        ssh_dir="/home/${QUBINODE_ADMIN_USER}/.ssh"
        ssh_key_path="${ssh_dir}/id_rsa"
    else
        ssh_dir="$HOME/.ssh"
        ssh_key_path="${ssh_dir}/id_rsa"
    fi

    # Ensure .ssh directory exists with correct permissions
    if [[ ! -d "$ssh_dir" ]]; then
        mkdir -p "$ssh_dir"
        chmod 700 "$ssh_dir"
        if [[ -n "${QUBINODE_ADMIN_USER:-}" && "${QUBINODE_ADMIN_USER}" != "root" ]]; then
            chown "${QUBINODE_ADMIN_USER}:${QUBINODE_ADMIN_USER}" "$ssh_dir"
        fi
    fi

    if [[ -f "$ssh_key_path" ]]; then
        log_info "SSH key already exists at $ssh_key_path"
    else
        log_info "Generating SSH key at $ssh_key_path..."
        local ip_address=$(hostname -I | awk '{print $1}')
        ssh-keygen -f "$ssh_key_path" -t rsa -N '' || {
            log_error "Failed to generate SSH key"
            ask_ai_for_help "ssh_keygen" "ssh-keygen failed"
            return 1
        }
        # Set correct ownership if generating for non-root user
        if [[ -n "${QUBINODE_ADMIN_USER:-}" && "${QUBINODE_ADMIN_USER}" != "root" ]]; then
            chown "${QUBINODE_ADMIN_USER}:${QUBINODE_ADMIN_USER}" "$ssh_key_path" "${ssh_key_path}.pub"
        fi

        # Configure SSH key for local access - use the specific key we generated
        if [[ "$CICD_PIPELINE" == "true" ]]; then
            if [[ "$EUID" -eq 0 ]]; then
                sshpass -p "$SSH_PASSWORD" ssh-copy-id -i "${ssh_key_path}.pub" -o StrictHostKeyChecking=no "$SSH_USER@${ip_address}" || {
                    log_warning "Failed to copy SSH key automatically"
                }
            else
                sshpass -p "$SSH_PASSWORD" ssh-copy-id -i "${ssh_key_path}.pub" -o StrictHostKeyChecking=no "$USER@${ip_address}" || {
                    log_warning "Failed to copy SSH key automatically"
                }
            fi
        else
            if [[ "$EUID" -eq 0 ]]; then
                log_info "Please manually copy SSH key to target user if needed"
                log_info "Command: ssh-copy-id -i ${ssh_key_path}.pub $SSH_USER@${ip_address}"
            else
                ssh-copy-id -i "${ssh_key_path}.pub" "$USER@${ip_address}" || {
                    log_warning "Failed to copy SSH key, you may need to do this manually"
                }
            fi
        fi
    fi

    # Sync SSH key to /root/.ssh/ for Airflow container access
    # The docker-compose.yml mounts /root/.ssh:/root/.ssh:ro into containers
    # So the key MUST be available at /root/.ssh/id_rsa for the container to use it
    if [[ -n "${QUBINODE_ADMIN_USER:-}" && "${QUBINODE_ADMIN_USER}" != "root" ]]; then
        log_info "Syncing SSH key to /root/.ssh for Airflow container access..."
        if [[ -f "$ssh_key_path" ]]; then
            mkdir -p /root/.ssh
            chmod 700 /root/.ssh
            # Only copy if not already in sync
            if [[ ! -f /root/.ssh/id_rsa ]] || ! diff -q "$ssh_key_path" /root/.ssh/id_rsa &>/dev/null; then
                cp "$ssh_key_path" /root/.ssh/id_rsa
                cp "${ssh_key_path}.pub" /root/.ssh/id_rsa.pub
                chmod 600 /root/.ssh/id_rsa
                chmod 644 /root/.ssh/id_rsa.pub
                log_info "SSH key copied to /root/.ssh/"
            fi
            # Also add to root's authorized_keys for container->host SSH
            touch /root/.ssh/authorized_keys
            chmod 600 /root/.ssh/authorized_keys
            local pub_key=$(cat "${ssh_key_path}.pub")
            if ! grep -qF "$pub_key" /root/.ssh/authorized_keys 2>/dev/null; then
                echo "$pub_key" >> /root/.ssh/authorized_keys
                log_info "SSH key added to /root/.ssh/authorized_keys"
            fi
        fi
    fi

    log_success "SSH configuration completed"
    return 0
}

# Firewall Configuration - Refactored from setup.sh
configure_firewalld() {
    log_step "Configuring firewalld..."

    if systemctl is-active --quiet firewalld; then
        log_info "firewalld is already active"
    else
        log_info "Starting firewalld..."
        sudo systemctl start firewalld || {
            log_error "Failed to start firewalld"
            ask_ai_for_help "firewalld_start" "systemctl start firewalld failed"
            return 1
        }
        sudo systemctl enable firewalld || {
            log_warning "Failed to enable firewalld"
        }
    fi

    # If Airflow is enabled, configure firewall for nginx proxy
    if [[ "$QUBINODE_ENABLE_AIRFLOW" == "true" ]]; then
        log_info "Configuring firewall for Airflow deployment..."

        # Close direct access to Airflow and AI Assistant ports (nginx will proxy them)
        log_info "Closing direct access to internal service ports..."
        firewall-cmd --permanent --remove-port=8888/tcp 2>/dev/null || log_info "Port 8888 already closed or not open"
        firewall-cmd --permanent --remove-port=8080/tcp 2>/dev/null || log_info "Port 8080 already closed or not open"

        # Open HTTP/HTTPS for nginx reverse proxy
        log_info "Opening HTTP/HTTPS ports for nginx..."
        firewall-cmd --permanent --add-service=http || log_warning "HTTP service already added"
        firewall-cmd --permanent --add-service=https || log_warning "HTTPS service already added"

        # Reload firewall rules
        log_info "Reloading firewall rules..."
        if firewall-cmd --reload; then
            log_success "Firewall rules updated for Airflow deployment"
        else
            log_warning "Failed to reload firewall, continuing anyway..."
        fi
    fi

    log_success "Firewall configuration completed"
    return 0
}

# Repository Manager - Refactored from setup.sh
get_qubinode_navigator() {
    local target_dir="$1"
    log_step "Setting up Qubinode Navigator repository..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        log_info "Qubinode Navigator already exists, updating..."
        git -C "$target_dir/qubinode_navigator" pull || {
            log_warning "Failed to update repository, continuing with current version"
        }
    else
        log_info "Cloning Qubinode Navigator repository..."
        cd "$target_dir" || return 1
        git clone "$GIT_REPO" || {
            log_error "Failed to clone Qubinode Navigator repository"
            ask_ai_for_help "git_clone" "Failed to clone $GIT_REPO"
            return 1
        }
    fi

    # Always ensure system-wide symlink exists (needed for Airflow DAGs)
    # DAGs reference /opt/qubinode_navigator for vault.yml and inventory resources
    # If a real directory exists (not a symlink), remove it first — ln -sf cannot overwrite directories
    if [[ -d /opt/qubinode_navigator && ! -L /opt/qubinode_navigator ]]; then
        log_info "Removing stale /opt/qubinode_navigator directory (replacing with symlink)"
        sudo rm -rf /opt/qubinode_navigator
    fi
    if [[ ! -L /opt/qubinode_navigator ]] || [[ "$(readlink -f /opt/qubinode_navigator 2>/dev/null)" != "$(readlink -f "$target_dir/qubinode_navigator" 2>/dev/null)" ]]; then
        log_info "Creating/updating system symlink: /opt/qubinode_navigator -> $target_dir/qubinode_navigator"
        sudo ln -sf "$target_dir/qubinode_navigator" /opt/qubinode_navigator || {
            log_warning "Failed to create system symlink"
        }
    else
        log_info "System symlink /opt/qubinode_navigator already correct"
    fi

    # Set proper permissions
    chmod +x "$target_dir/qubinode_navigator"/*.sh 2>/dev/null || true
    chmod +x "$target_dir/qubinode_navigator/ai-assistant/scripts/"*.sh 2>/dev/null || true

    log_success "Qubinode Navigator repository setup completed"
    return 0
}

configure_environment() {
    log_step "Configuring Qubinode environment..."

    # Create/update environment configuration in current directory
    local env_file="$SCRIPT_DIR/.env"

    # Backup existing .env if it exists
    if [[ -f "$env_file" ]]; then
        cp "$env_file" "${env_file}.backup.$(date +%Y%m%d-%H%M%S)"
        log_info "Backed up existing .env file"
    fi

    # Create comprehensive environment configuration
    log_info "Creating environment configuration..."
    cat > "$env_file" << EOF
# Qubinode Navigator Configuration
# Generated by one-shot deployment script on $(date)

# =============================================================================
# BASIC CONFIGURATION
# =============================================================================
QUBINODE_DOMAIN=${QUBINODE_DOMAIN}
QUBINODE_ADMIN_USER=${QUBINODE_ADMIN_USER}
QUBINODE_CLUSTER_NAME=${QUBINODE_CLUSTER_NAME}
QUBINODE_DEPLOYMENT_MODE=${QUBINODE_DEPLOYMENT_MODE}

# =============================================================================
# QUBINODE NAVIGATOR INTEGRATION
# =============================================================================
GIT_REPO=${GIT_REPO}
CICD_PIPELINE=${CICD_PIPELINE}
INVENTORY=${INVENTORY}
USE_HASHICORP_VAULT=${USE_HASHICORP_VAULT}
SSH_USER=${SSH_USER}

# =============================================================================
# RESOURCE CONFIGURATION
# =============================================================================
QUBINODE_STORAGE_SIZE=${QUBINODE_STORAGE_SIZE}
QUBINODE_WORKER_NODES=${QUBINODE_WORKER_NODES}

# =============================================================================
# FEATURE FLAGS
# =============================================================================
QUBINODE_ENABLE_AI_ASSISTANT=${QUBINODE_ENABLE_AI_ASSISTANT}
QUBINODE_ENABLE_MONITORING=${QUBINODE_ENABLE_MONITORING}
QUBINODE_ENABLE_LOGGING=${QUBINODE_ENABLE_LOGGING}

# =============================================================================
# AI ASSISTANT CONFIGURATION
# =============================================================================
AI_ASSISTANT_PORT=${AI_ASSISTANT_PORT}
AI_ASSISTANT_VERSION=${AI_ASSISTANT_VERSION}

# =============================================================================
# SYSTEM INFORMATION
# =============================================================================
OS_TYPE=${OS_TYPE}
OS_VERSION=${OS_VERSION}
BASE_OS=${BASE_OS}
DEPLOYMENT_TIMESTAMP=$(date -Iseconds)
DEPLOYMENT_LOG=${DEPLOYMENT_LOG}
EOF

    log_success "Environment configuration created at $env_file"
    return 0
}

# Deployment orchestration using existing architecture
deploy_qubinode_infrastructure() {
    local my_dir="$1"
    log_step "Deploying Qubinode infrastructure using existing architecture..."

    # Change to the qubinode directory
    cd "$my_dir/qubinode_navigator" || {
        log_error "Failed to change to qubinode_navigator directory"
        return 1
    }

    log_info "Working directory: $(pwd)"
    log_info "Deployment mode: $QUBINODE_DEPLOYMENT_MODE"
    log_info "Target OS: $BASE_OS"

    # Determine the appropriate deployment approach
    if [[ "$BASE_OS" == "ROCKY8" ]]; then
        log_error "Rocky Linux 8 should use the rocky-linux-hypervisor.sh script"
        log_error "This script focuses on modern RHEL-based systems (9+)"
        return 1
    fi

    # Use the existing setup.sh workflow but with our environment
    log_info "Executing Qubinode Navigator setup workflow..."
    log_info "This process includes:"
    log_info "  1. OS configuration and package installation"
    log_info "  2. SSH and firewall configuration"
    log_info "  3. Ansible Navigator setup"
    log_info "  4. Vault configuration"
    log_info "  5. Inventory generation"
    log_info "  6. KVM host deployment"
    log_info "  7. Bash aliases and kcli setup"

    # Execute the setup workflow step by step
    configure_os "$BASE_OS" || return 1
    install_packages || return 1
    configure_ssh || return 1
    configure_firewalld || return 1

    # Create notouch.env for compatibility with existing scripts
    create_notouch_env || return 1

    # Configure ansible navigator (from setup.sh)
    configure_navigator "$my_dir" || return 1

    # Configure vault (from setup.sh)
    configure_vault "$my_dir" || return 1

    # Generate inventory (from setup.sh)
    generate_inventory "$my_dir" || return 1

    # Test inventory (from setup.sh)
    test_inventory "$my_dir" || return 1

    # Deploy KVM host (from setup.sh)
    deploy_kvmhost || return 1

    # Configure bash aliases (from setup.sh)
    configure_bash_aliases || return 1

    # Setup kcli base (from setup.sh)
    setup_kcli_base || return 1

    # Configure kcli to inject SSH keys into VMs
    configure_kcli_ssh_keys || log_warning "SSH key injection config failed"

    log_success "Qubinode infrastructure deployment completed successfully!"
    return 0
}

# =============================================================================
# FUNCTIONS FROM SETUP.SH (Referenced but not yet implemented)
# =============================================================================

# Ansible Navigator Configurator - From setup.sh
configure_navigator() {
    local target_dir="$1"
    log_step "Configuring ansible navigator..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        cd "$target_dir/qubinode_navigator" || return 1

        if ! command -v ansible-navigator &> /dev/null; then
            log_info "Installing ansible-navigator..."
            make install-ansible-navigator || {
                log_error "Failed to install ansible-navigator"
                ask_ai_for_help "ansible_navigator_install" "make install-ansible-navigator failed"
                return 1
            }

            make copy-navigator || {
                log_warning "Failed to copy navigator configuration"
            }

            # Update navigator configuration for current user
            sed -i "s|/home/admin/qubinode_navigator/inventories/localhost|${QUBINODE_HOME}/inventories/${INVENTORY}|g" ~/.ansible-navigator.yml
        fi

        # Install Python requirements
        ensure_uv
        sudo -E uv pip install --system -r requirements.txt || {
            log_warning "Failed to install Python requirements"
        }

        # Install passlib for Ansible password_hash filter
        log_info "Ensuring passlib is installed for password hashing..."
        sudo -E uv pip install --system passlib || {
            log_warning "Failed to install passlib, password operations may fail"
        }

        # Load variables
        log_info "Loading variables..."

        # Auto-detect /tmp/config.yml and use non-interactive mode
        if [[ -f "/tmp/config.yml" ]]; then
            log_info "Found existing /tmp/config.yml, using automated configuration"
            # Use CI/CD mode with environment variables when config file exists
            export CICD_PIPELINE="true"

            # Set reasonable defaults for CI/CD mode when config file exists
            export ENV_USERNAME="${ENV_USERNAME:-$SSH_USER}"
            export DOMAIN="${DOMAIN:-$QUBINODE_DOMAIN}"
            export FORWARDER="${FORWARDER:-8.8.8.8}"
            export ACTIVE_BRIDGE="${ACTIVE_BRIDGE:-false}"
            export INTERFACE="${INTERFACE:-$(ip route | grep default | awk '{print $5}' | head -1)}"
            export DISK="${DISK:-skip}"

            # Use appropriate inventory - force to hetzner when config file exists
            # (Override the default localhost set earlier in the script)
            export INVENTORY="hetzner"

            log_info "Using configuration: Domain=$DOMAIN, User=$ENV_USERNAME, Interface=$INTERFACE"
        fi

        if [[ "$CICD_PIPELINE" == "false" ]]; then
            python3 "$target_dir/qubinode_navigator/load-variables.py" || {
                log_error "Failed to load variables"
                ask_ai_for_help "load_variables" "python3 load-variables.py failed"
                return 1
            }
        else
            # Set defaults from QUBINODE_* environment variables for CI/CD mode
            export ENV_USERNAME="${ENV_USERNAME:-${QUBINODE_ADMIN_USER:-admin}}"
            export DOMAIN="${DOMAIN:-${QUBINODE_DOMAIN:-example.com}}"
            export FORWARDER="${FORWARDER:-8.8.8.8}"
            export ACTIVE_BRIDGE="${ACTIVE_BRIDGE:-false}"
            export INTERFACE="${INTERFACE:-$(ip route | grep default | awk '{print $5}' | head -1)}"
            export DISK="${DISK:-skip}"

            if [[ -z "$ENV_USERNAME" || -z "$DOMAIN" || -z "$FORWARDER" || -z "$ACTIVE_BRIDGE" || -z "$INTERFACE" || -z "$DISK" ]]; then
                log_error "Required environment variables not set for CI/CD mode"
                return 1
            fi
            python3 "$target_dir/qubinode_navigator/load-variables.py" --username "$ENV_USERNAME" --domain "$DOMAIN" --forwarder "$FORWARDER" --bridge "$ACTIVE_BRIDGE" --interface "$INTERFACE" --disk "$DISK" || {
                log_error "Failed to load variables with parameters"
                return 1
            }
        fi
    else
        log_error "Qubinode Navigator directory not found"
        return 1
    fi

    log_success "Ansible Navigator configuration completed"
    return 0
}

# Vault Configuration - From setup.sh
# IDEMPOTENT: Only configures vault if not already set up
configure_vault() {
    local target_dir="$1"
    log_step "Configuring ansible vault..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        cd "$target_dir/qubinode_navigator" || return 1

        # Install ansible-core if not present
        if ! command -v ansible-vault &> /dev/null; then
            sudo dnf install ansible-core -y || {
                log_error "Failed to install ansible-core"
                return 1
            }
        fi

        # Install ansiblesafe if not present
        if ! command -v ansiblesafe &> /dev/null; then
            log_info "Installing ansiblesafe..."
            curl -OL "https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.12/ansiblesafe-v0.0.14-linux-amd64.tar.gz" || {
                log_error "Failed to download ansiblesafe"
                return 1
            }
            tar -zxvf "ansiblesafe-v0.0.14-linux-amd64.tar.gz"
            chmod +x ansiblesafe-linux-amd64
            sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
        fi

        # Download ansible_vault_setup.sh if not present
        if [[ ! -f ~/qubinode_navigator/ansible_vault_setup.sh ]]; then
            curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
            chmod +x ansible_vault_setup.sh
        fi

        # IDEMPOTENT CHECK: Skip if vault password file already exists and is valid
        if [[ -f "$HOME/.vault_password" ]] && [[ -s "$HOME/.vault_password" ]]; then
            log_info "Vault password file already exists at $HOME/.vault_password"

            # Ensure root also has it
            if [[ ! -f "/root/.vault_password" ]] && [[ "$EUID" -ne 0 ]]; then
                sudo cp "$HOME/.vault_password" /root/.vault_password
                sudo chmod 600 /root/.vault_password
            fi

            log_success "Using existing vault password file (idempotent)"
            return 0
        fi

        # Configure Ansible Vault only if not already configured
        log_info "Configuring Ansible Vault password file..."

        if [[ "$USE_HASHICORP_VAULT" == "true" ]]; then
            # Use SSH_PASSWORD from HashiCorp Vault or environment
            if [[ -n "${SSH_PASSWORD:-}" ]]; then
                echo "$SSH_PASSWORD" > ~/.vault_password
                chmod 600 ~/.vault_password
                sudo cp ~/.vault_password /root/.vault_password
                sudo chmod 600 /root/.vault_password
                log_success "Vault password set from SSH_PASSWORD"
            else
                log_warning "USE_HASHICORP_VAULT=true but SSH_PASSWORD not set"
                bash ./ansible_vault_setup.sh
            fi
        elif [[ "$QUBINODE_DEPLOYMENT_MODE" == "development" ]]; then
            log_info "Setting up vault password file for development mode..."
            # For development mode, create a default vault password file
            echo "defaultpassword" > ~/.vault_password
            chmod 600 ~/.vault_password
            sudo cp ~/.vault_password /root/.vault_password
            sudo chmod 600 /root/.vault_password
            log_success "Development vault password file created"
        elif [[ "$CICD_PIPELINE" == "true" ]] && [[ -n "${SSH_PASSWORD:-}" ]]; then
            # CI/CD mode with password provided
            log_info "Setting up vault password for CI/CD pipeline..."
            echo "$SSH_PASSWORD" > ~/.vault_password
            chmod 600 ~/.vault_password
            sudo cp ~/.vault_password /root/.vault_password
            sudo chmod 600 /root/.vault_password
            log_success "Vault password set from CI/CD environment"
        else
            log_info "Setting up vault interactively..."
            bash ./ansible_vault_setup.sh
        fi
    else
        log_error "Qubinode Navigator directory not found"
        return 1
    fi

    log_success "Vault configuration completed"
    return 0
}

# Inventory Generation - From setup.sh
generate_inventory() {
    local target_dir="$1"
    log_step "Generating inventory..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        cd "$target_dir/qubinode_navigator" || return 1

        # Create inventory directory structure
        if [[ ! -d "inventories/${INVENTORY}" ]]; then
            mkdir -p "inventories/${INVENTORY}"
            mkdir -p "inventories/${INVENTORY}/group_vars/control"
        fi

        # Update bash aliases
        sed -i "s|export CURRENT_INVENTORY=\"localhost\"|export CURRENT_INVENTORY=\"${INVENTORY}\"|g" bash-aliases/functions.sh

        # Set up control host
        local control_host=$(hostname -I | awk '{print $1}')
        local control_user

        if [[ "$EUID" -eq 0 ]]; then
            control_user="$SSH_USER"
        else
            control_user="$USER"
        fi

        # Generate hosts file
        echo "[control]" > "inventories/${INVENTORY}/hosts"
        echo "control ansible_host=${control_host} ansible_user=${control_user}" >> "inventories/${INVENTORY}/hosts"

        # Create vault.yml if it doesn't exist
        local vault_file="inventories/${INVENTORY}/group_vars/control/vault.yml"
        if [[ ! -f "$vault_file" ]]; then
            log_info "Creating vault.yml with default credentials..."

            # Get password from environment or use default
            local vault_password="${SSH_PASSWORD:-COmp123\$%}"

            # Create unencrypted vault file first
            cat > "$vault_file" << VAULTEOF
---
# Ansible Vault - Sensitive Credentials
# Encrypted with ansible-vault

# FreeIPA Configuration
freeipa_server_admin_password: "${vault_password}"

# Red Hat Subscription Manager (leave empty for CentOS/community)
rhsm_org: ""
rhsm_activationkey: ""
rhsm_username: ""
rhsm_password: ""

# OpenShift Pull Secret (optional)
openshift_pull_secret: ""
VAULTEOF

            # Encrypt the vault file
            if [[ -f "$HOME/.vault_password" ]]; then
                ansible-vault encrypt "$vault_file" --vault-password-file "$HOME/.vault_password" --encrypt-vault-id default 2>/dev/null || \
                ansible-vault encrypt "$vault_file" --vault-password-file "$HOME/.vault_password" 2>/dev/null || \
                log_warning "Could not encrypt vault.yml - please encrypt manually"
                log_success "vault.yml created and encrypted"
            else
                log_warning "vault.yml created but not encrypted - .vault_password not found"
            fi
        else
            log_info "vault.yml already exists"
        fi

        log_success "Inventory generated for ${INVENTORY}"
    else
        log_error "Qubinode Navigator directory not found"
        return 1
    fi

    return 0
}

# Test Inventory - From setup.sh
test_inventory() {
    local target_dir="$1"
    log_step "Testing inventory..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        cd "$target_dir/qubinode_navigator" || return 1

        local ansible_navigator_cmd
        if ! command -v ansible-navigator &> /dev/null; then
            ansible_navigator_cmd=$(whereis ansible-navigator | awk '{print $2}')
        else
            ansible_navigator_cmd="ansible-navigator"
        fi

        $ansible_navigator_cmd inventory --list -i "inventories/${INVENTORY}" -m stdout --vault-password-file "$HOME/.vault_password" || {
            log_error "Inventory test failed"
            ask_ai_for_help "inventory_test" "ansible-navigator inventory test failed"
            return 1
        }

        log_success "Inventory test completed successfully"
    else
        log_error "Qubinode Navigator directory not found"
        return 1
    fi

    return 0
}

# Deploy KVM Host - From setup.sh
deploy_kvmhost() {
    log_step "Deploying KVM Host..."

    # Set up SSH agent - use the admin user's SSH key, not root's
    local ssh_key_path
    if [[ -n "${QUBINODE_ADMIN_USER:-}" && "${QUBINODE_ADMIN_USER}" != "root" ]]; then
        ssh_key_path="/home/${QUBINODE_ADMIN_USER}/.ssh/id_rsa"
    else
        ssh_key_path="$HOME/.ssh/id_rsa"
    fi

    eval $(ssh-agent)
    ssh-add "$ssh_key_path" || {
        log_error "Failed to add SSH key to agent: $ssh_key_path"
        return 1
    }

    # Use REPO_ROOT instead of hardcoded paths
    cd "$REPO_ROOT" || {
        log_error "Failed to change to qubinode_navigator directory at $REPO_ROOT"
        return 1
    }

    # Install required Ansible collections and roles when running without execution environment
    log_info "Installing required Ansible collections..."
    ansible-galaxy collection install -r "$REPO_ROOT/ansible-builder/requirements.yml" --force || {
        log_warning "Failed to install some Ansible collections, continuing anyway..."
    }

    log_info "Installing required Ansible roles..."
    ansible-galaxy role install linux-system-roles.cockpit linux-system-roles.network linux-system-roles.firewall --force || {
        log_warning "Failed to install some Ansible roles, continuing anyway..."
    }

    local ansible_navigator_cmd
    if ! command -v ansible-navigator &> /dev/null; then
        ansible_navigator_cmd=$(whereis ansible-navigator | awk '{print $2}')
    else
        ansible_navigator_cmd="ansible-navigator"
    fi

    $ansible_navigator_cmd run "$REPO_ROOT/ansible-navigator/setup_kvmhost.yml" \
        --vault-password-file "$HOME/.vault_password" \
        --execution-environment false \
        -m stdout || {
        log_error "KVM host deployment failed"
        ask_ai_for_help "kvmhost_deploy" "ansible-navigator run setup_kvmhost.yml failed"
        return 1
    }

    log_success "KVM host deployment completed"
    return 0
}

# Configure Bash Aliases - From setup.sh
configure_bash_aliases() {
    log_step "Configuring bash aliases..."

    # Use REPO_ROOT instead of hardcoded paths
    cd "$REPO_ROOT" || {
        log_error "Failed to change to $REPO_ROOT"
        return 1
    }

    # Source the function and alias definitions
    source bash-aliases/functions.sh || {
        log_warning "Failed to source functions.sh"
    }

    source bash-aliases/aliases.sh || {
        log_warning "Failed to source aliases.sh"
    }

    # Apply bash aliases
    if [[ -f ~/.bash_aliases ]]; then
        source ~/.bash_aliases
    fi

    # Ensure .bash_aliases is sourced from .bashrc
    if ! grep -qF "source ~/.bash_aliases" ~/.bashrc; then
        echo "source ~/.bash_aliases" >> ~/.bashrc
    fi

    log_success "Bash aliases configuration completed"
    return 0
}

# Setup Kcli Base - From setup.sh
setup_kcli_base() {
    log_step "Setting up kcli base..."

    # Use REPO_ROOT instead of hardcoded paths
    cd "$REPO_ROOT" || {
        log_error "Failed to change to $REPO_ROOT"
        return 1
    }

    # Source bash aliases to get kcli functions
    source ~/.bash_aliases || {
        log_warning "Failed to source bash aliases"
    }

    # Setup kcli
    qubinode_setup_kcli || {
        log_warning "Failed to setup kcli"
    }

    # Configure kcli images
    kcli_configure_images || {
        log_warning "Failed to configure kcli images"
    }

    log_success "Kcli base setup completed"
    return 0
}

# Configure kcli to inject SSH keys into all VMs
configure_kcli_ssh_keys() {
    log_step "Configuring kcli SSH key injection..."

    # Always use /root/ paths because:
    # 1. kcli runs with sudo (via get_kcli_prefix()), so uses /root/.kcli/config.yml
    # 2. Admin user's key is synced to /root/.ssh/ by configure_ssh() (lines 1387-1410)
    # 3. Airflow containers mount /root/.ssh:ro and use that key for SSH connections
    # This works regardless of QUBINODE_ADMIN_USER - the key is always synced to /root/
    local ssh_pub_key="/root/.ssh/id_rsa.pub"
    local kcli_config="/root/.kcli/config.yml"

    # Verify SSH public key exists
    if [[ ! -f "$ssh_pub_key" ]]; then
        log_warning "SSH public key not found at $ssh_pub_key"
        log_warning "VMs will be created without SSH key injection"
        return 0
    fi

    # Verify kcli config exists
    if [[ ! -f "$kcli_config" ]]; then
        log_warning "kcli config not found at $kcli_config"
        return 0
    fi

    # Check if keysname is already configured
    if grep -q "^  keysname:" "$kcli_config" 2>/dev/null; then
        log_info "kcli SSH key injection already configured"
        return 0
    fi

    # Add keysname parameter to default section
    # Insert after 'cloudinit: true' line
    if grep -q "cloudinit: true" "$kcli_config"; then
        sed -i '/^  cloudinit: true$/a\  keysname:\n    - '"$ssh_pub_key"'' "$kcli_config"
        log_success "kcli configured to inject SSH key from $ssh_pub_key"
    else
        log_warning "Could not find cloudinit setting in kcli config"
        log_warning "Manually add 'keysname: [\"$ssh_pub_key\"]' to $kcli_config"
    fi

    return 0
}

# Create notouch.env for compatibility with existing deployment scripts
create_notouch_env() {
    log_step "Creating notouch.env for compatibility with existing scripts..."

    local notouch_file="$SCRIPT_DIR/notouch.env"

    # Backup existing notouch.env if it exists
    if [[ -f "$notouch_file" ]]; then
        cp "$notouch_file" "${notouch_file}.backup.$(date +%Y%m%d-%H%M%S)"
        log_info "Backed up existing notouch.env"
    fi

    # Create notouch.env based on deployment target and current configuration
    log_info "Creating notouch.env for deployment target: $DEPLOYMENT_TARGET"

    cat > "$notouch_file" << EOF
# Qubinode Navigator Environment Configuration
# Generated by deploy-qubinode.sh on $(date)
# Deployment Target: $DEPLOYMENT_TARGET

export SSH_USER=$SSH_USER
export CICD_PIPELINE=$CICD_PIPELINE
export ENV_USERNAME=$ENV_USERNAME
export KVM_VERSION=$KVM_VERSION
export CICD_ENVIORNMENT=$CICD_ENVIORNMENT
export DOMAIN=$QUBINODE_DOMAIN
export USE_HASHICORP_VAULT=$USE_HASHICORP_VAULT
export USE_HASHICORP_CLOUD=$USE_HASHICORP_CLOUD
export FORWARDER=$FORWARDER
export ACTIVE_BRIDGE=$ACTIVE_BRIDGE
export INTERFACE=$INTERFACE
export USE_ROUTE53=$USE_ROUTE53
export GIT_REPO=$GIT_REPO
export INVENTORY=$INVENTORY
EOF

    # Add SSH_PASSWORD if it's set
    if [[ -n "${SSH_PASSWORD:-}" ]]; then
        echo "export SSH_PASSWORD='$SSH_PASSWORD'" >> "$notouch_file"
    fi

    # Add HashiCorp Cloud configuration if enabled
    if [[ "$USE_HASHICORP_CLOUD" == "true" ]]; then
        cat >> "$notouch_file" << EOF
export HCP_CLIENT_ID=\${HCP_CLIENT_ID:-}
export HCP_CLIENT_SECRET=\${HCP_CLIENT_SECRET:-}
export HCP_ORG_ID=\${HCP_ORG_ID:-}
export HCP_PROJECT_ID=\${HCP_PROJECT_ID:-}
export APP_NAME=\${APP_NAME:-qubinode}
EOF
    fi

    # Add deployment-target specific configuration
    case "$DEPLOYMENT_TARGET" in
        "hetzner")
            cat >> "$notouch_file" << EOF
# Hetzner Cloud specific configuration
export ZONE_NAME=$QUBINODE_DOMAIN
export EMAIL=\${EMAIL:-admin@$QUBINODE_DOMAIN}
export GUID=\${GUID:-hetzner-$(date +%s)}
EOF
            ;;
        "equinix")
            cat >> "$notouch_file" << EOF
# Red Hat Demo System (Equinix) specific configuration
export ZONE_NAME=$QUBINODE_DOMAIN
export EMAIL=\${EMAIL:-admin@$QUBINODE_DOMAIN}
export GUID=\${GUID:-equinix-$(date +%s)}
EOF
            ;;
        "local")
            cat >> "$notouch_file" << EOF
# Local development specific configuration
export ZONE_NAME=$QUBINODE_DOMAIN
export EMAIL=\${EMAIL:-admin@$QUBINODE_DOMAIN}
export GUID=\${GUID:-local-$(date +%s)}
EOF
            ;;
    esac

    # Make notouch.env executable
    chmod +x "$notouch_file"

    log_success "Created notouch.env for compatibility with existing deployment scripts"
    log_info "notouch.env location: $notouch_file"

    return 0
}

# Fix DNS configuration in inventory files - Auto-update CHANGEME values
fix_dns_configuration() {
    log_step "Fixing DNS configuration in inventory files..."

    # Use REPO_ROOT instead of SCRIPT_DIR
    local inventory_dir="$REPO_ROOT/inventories/$INVENTORY"
    local all_vars_file="$inventory_dir/group_vars/all.yml"
    local kvm_host_file="$inventory_dir/group_vars/control/kvm_host.yml"

    # Auto-detect current DNS servers from system
    local current_dns_servers=($(awk '/^nameserver/ {print $2}' /etc/resolv.conf))
    local primary_dns="${current_dns_servers[0]:-8.8.8.8}"
    local secondary_dns="${current_dns_servers[1]:-$FORWARDER}"

    # Use detected forwarder if available, otherwise use secondary DNS
    local dns_forwarder="${FORWARDER:-$secondary_dns}"

    log_info "Auto-detected DNS configuration:"
    log_info "  Primary DNS: $primary_dns"
    log_info "  DNS Forwarder: $dns_forwarder"
    log_info "  Domain: $QUBINODE_DOMAIN"

    # Function to update DNS in a YAML file
    update_dns_in_file() {
        local yaml_file="$1"

        if [[ ! -f "$yaml_file" ]]; then
            log_warning "File not found: $yaml_file"
            return 1
        fi

        # Create backup
        local backup_file="${yaml_file}.backup.$(date +%Y%m%d-%H%M%S)"
        cp "$yaml_file" "$backup_file"
        log_info "Created backup: $backup_file"

        # Update DNS configuration using sed
        sed -i "s/dns_forwarder: \"CHANGEME\"/dns_forwarder: \"$dns_forwarder\"/" "$yaml_file"
        sed -i "s/dns_forwarder: CHANGEME/dns_forwarder: \"$dns_forwarder\"/" "$yaml_file"
        sed -i "s/primary_dns_server: \"8.8.8.8\"/primary_dns_server: \"$primary_dns\"/" "$yaml_file"
        sed -i "s/kvm_host_dns_server: \"8.8.8.8\"/kvm_host_dns_server: \"$primary_dns\"/" "$yaml_file"
        sed -i "s/kvm_host_domain: \"lab.local\"/kvm_host_domain: \"$QUBINODE_DOMAIN\"/" "$yaml_file"

        # Update search domains
        sed -i "s/- \"lab.local\"/- \"$QUBINODE_DOMAIN\"/" "$yaml_file"
        sed -i "s/- lab.local/- \"$QUBINODE_DOMAIN\"/" "$yaml_file"

        log_success "Updated DNS configuration in: $yaml_file"
    }

    # Update main inventory file
    if [[ -f "$all_vars_file" ]]; then
        update_dns_in_file "$all_vars_file"
    else
        log_error "Main inventory file not found: $all_vars_file"
        return 1
    fi

    # Update control host configuration if it exists
    if [[ -f "$kvm_host_file" ]]; then
        update_dns_in_file "$kvm_host_file"
    fi

    # Validate the changes
    if grep -q "CHANGEME" "$all_vars_file"; then
        log_warning "Some CHANGEME values may still exist in inventory files"
        log_info "Remaining CHANGEME entries:"
        grep -n "CHANGEME" "$all_vars_file" || true
    else
        log_success "All CHANGEME values have been replaced with auto-detected DNS configuration"
    fi

    log_success "DNS configuration fix completed"
    return 0
}

# =============================================================================
# CREDENTIAL SYNC TO AIRFLOW
# =============================================================================
# Syncs credentials from Ansible Vault/HashiCorp Vault to Airflow Variables
# This makes credentials easily accessible to DAGs

sync_credentials_to_airflow() {
    if [[ "$QUBINODE_ENABLE_AIRFLOW" != "true" ]]; then
        log_info "Airflow not enabled, skipping credential sync..."
        return 0
    fi

    log_step "Syncing credentials to Airflow Variables..."

    local sync_script="$REPO_ROOT/airflow/scripts/sync-credentials-to-airflow.sh"

    if [[ ! -f "$sync_script" ]]; then
        log_warning "Credential sync script not found: $sync_script"
        return 0
    fi

    # Wait for Airflow to be ready
    log_info "Waiting for Airflow API to be ready..."
    local max_retries=30
    local retry=0
    while [[ $retry -lt $max_retries ]]; do
        if curl -s -u "admin:admin" "http://localhost:${AIRFLOW_PORT}/api/v1/health" | grep -q "healthy"; then
            break
        fi
        ((retry++))
        sleep 2
    done

    if [[ $retry -ge $max_retries ]]; then
        log_warning "Airflow API not ready, skipping credential sync"
        return 0
    fi

    # Run the sync script
    export AIRFLOW_URL="http://localhost:${AIRFLOW_PORT}"
    export INVENTORY="$INVENTORY"
    export VAULT_PASSWORD_FILE="$HOME/.vault_password"

    if bash "$sync_script" all; then
        log_success "Credentials synced to Airflow Variables"
    else
        log_warning "Some credentials may not have been synced (non-critical)"
    fi

    return 0
}

# =============================================================================
# RAG BOOTSTRAP
# =============================================================================
# Bootstrap the RAG knowledge base with ADRs, DAG examples, and documentation
# This makes the AI Assistant fully operational with project context

bootstrap_rag_knowledge_base() {
    if [[ "$QUBINODE_ENABLE_AIRFLOW" != "true" ]]; then
        log_info "Airflow not enabled, skipping RAG bootstrap..."
        return 0
    fi

    log_step "Bootstrapping RAG knowledge base..."

    # Check if Airflow API is accessible
    if ! curl -s -u "admin:admin" "http://localhost:${AIRFLOW_PORT}/api/v1/health" | grep -q "healthy"; then
        log_warning "Airflow API not ready, skipping RAG bootstrap"
        return 0
    fi

    # Unpause critical DAGs so they can be triggered
    log_info "Unpausing critical DAGs..."
    local critical_dags=(
        rag_bootstrap
        rag_document_ingestion
        freeipa_deployment
        generic_vm_deployment
        smoke_test_dag
        infrastructure_health_check
    )
    for dag_id in "${critical_dags[@]}"; do
        if curl -s -X PATCH \
            -u "admin:admin" \
            -H "Content-Type: application/json" \
            "http://localhost:${AIRFLOW_PORT}/api/v1/dags/${dag_id}" \
            -d '{"is_paused": false}' | grep -q '"is_paused":false\|"is_paused": false'; then
            log_success "Unpaused DAG: ${dag_id}"
        else
            log_warning "Could not unpause DAG: ${dag_id} (may not exist yet)"
        fi
    done

    # Create localhost SSH connection for DAGs that use SSHOperator
    log_info "Creating localhost_ssh Airflow connection..."
    curl -s -X POST -u "admin:admin" -H "Content-Type: application/json" \
        "http://localhost:${AIRFLOW_PORT}/api/v1/connections" \
        -d '{"connection_id":"localhost_ssh","conn_type":"ssh","host":"localhost","login":"root","port":22,"extra":"{\"no_host_key_check\": true}"}' \
        2>/dev/null | grep -q "connection_id" && \
        log_success "Created localhost_ssh Airflow connection" || \
        log_info "localhost_ssh connection already exists"

    # Trigger the rag_bootstrap DAG
    log_info "Triggering RAG bootstrap DAG to ingest ADRs, DAG examples, and documentation..."

    local response
    response=$(curl -s -X POST \
        -u "admin:admin" \
        -H "Content-Type: application/json" \
        "http://localhost:${AIRFLOW_PORT}/api/v1/dags/rag_bootstrap/dagRuns" \
        -d '{"conf": {}}' 2>&1)

    if echo "$response" | grep -q "dag_run_id\|queued"; then
        log_success "RAG bootstrap DAG triggered successfully"
        log_info "The knowledge base will be populated in the background"
        log_info "Monitor progress: http://localhost:${AIRFLOW_PORT}/dags/rag_bootstrap/grid"
    elif echo "$response" | grep -q "already running\|is paused"; then
        log_warning "RAG bootstrap DAG is paused or already running"
        log_info "Unpause and trigger manually: airflow dags unpause rag_bootstrap && airflow dags trigger rag_bootstrap"
    else
        log_warning "Could not trigger RAG bootstrap DAG (non-critical)"
        log_info "Trigger manually after deployment: airflow dags trigger rag_bootstrap"
    fi

    return 0
}

verify_deployment() {
    log_step "Verifying deployment..."

    # Check libvirt (skip in CI/CD mode where libvirt may not be available)
    if [[ "$CICD_PIPELINE" == "true" ]]; then
        # In CI/CD mode, only check libvirt if the socket exists
        if [[ -S /var/run/libvirt/libvirt-sock ]]; then
            if virsh list &> /dev/null; then
                local vm_count=$(virsh list --all | grep -c "running\|shut off" || echo "0")
                log_info "Virtual machines found: $vm_count"
            else
                log_warning "libvirt not accessible (may not be configured in CI/CD)"
            fi
        else
            log_info "Skipping libvirt verification (not available in CI/CD environment)"
        fi
    else
        # In normal mode, libvirt is required
        if ! virsh list &> /dev/null; then
            log_error "libvirt verification failed"
            return 1
        fi
        # Check for running VMs (if any were created)
        local vm_count=$(virsh list --all | grep -c "running\|shut off" || echo "0")
        log_info "Virtual machines found: $vm_count"
    fi

    # Check AI Assistant if enabled
    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]] && [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
        if curl -s http://localhost:${AI_ASSISTANT_PORT}/health &> /dev/null; then
            log_success "AI Assistant is running and accessible"
        else
            log_warning "AI Assistant is not responding"
        fi
    fi

    log_success "Deployment verification completed"
    return 0
}

# =============================================================================
# ERROR HANDLING AND CLEANUP
# =============================================================================

cleanup_on_error() {
    log_error "Deployment failed, performing cleanup..."
    DEPLOYMENT_FAILED=true

    # Stop AI Assistant container if it was started
    if [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
        log_info "Stopping AI Assistant container..."
        podman stop qubinode-ai-assistant &> /dev/null || true
        podman rm qubinode-ai-assistant &> /dev/null || true
    fi

    # Show deployment log location
    if [[ -f "$DEPLOYMENT_LOG" ]]; then
        log_info "Deployment log available at: $DEPLOYMENT_LOG"
    fi
}

signal_deployment_success() {
    # Signal to AI Assistant that deployment is complete
    # This switches the AI from SRE mode to Architect mode
    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]] && [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
        log_ai "Signaling deployment success to AI Assistant..."

        local success_message="DEPLOYMENT SUCCESS: The Qubinode Navigator system is now fully operational. You may now switch to Architect/Developer mode for feature additions and code improvements."

        curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "{\"message\": \"$success_message\", \"lifecycle_stage\": \"operational\"}" \
            http://localhost:${AI_ASSISTANT_PORT}/chat &> /dev/null || true
    fi
}

show_completion_summary() {
    # Signal deployment success first
    signal_deployment_success

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                   DEPLOYMENT COMPLETED                       ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Deployment Summary:${NC}"
    echo -e "  • Cluster Name: ${QUBINODE_CLUSTER_NAME}"
    echo -e "  • Domain: ${QUBINODE_DOMAIN}"
    echo -e "  • Admin User: ${QUBINODE_ADMIN_USER}"
    echo -e "  • OS: ${OS_TYPE} ${OS_VERSION}"
    echo -e "  • Mode: ${QUBINODE_DEPLOYMENT_MODE}"
    echo -e "  • DNS: Auto-configured from system settings"
    echo ""

    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]] && [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
        echo -e "${CYAN}AI Assistant Available:${NC}"
        echo -e "  • URL: http://localhost:${AI_ASSISTANT_PORT}"
        echo -e "  • Health: http://localhost:${AI_ASSISTANT_PORT}/health"
        echo -e "  • Mode: ${GREEN}Architect/Developer${NC} (System operational - full code access)"
        echo -e "  • Capabilities: Add features, refactor code, extend functionality"
        echo ""
    fi

    if [[ "$QUBINODE_ENABLE_AIRFLOW" == "true" ]]; then
        echo -e "${CYAN}Apache Airflow Orchestration:${NC}"
        echo -e "  • Airflow Web UI: http://localhost:${AIRFLOW_PORT}"
        echo -e "  • Username: admin"
        echo -e "  • Password: admin"
        echo -e "  • Documentation: airflow/README.md"
        echo ""

        if systemctl is-active --quiet nginx; then
            echo -e "${CYAN}Nginx Reverse Proxy (Web UIs):${NC}"
            echo -e "  • Status: Running on port 80"
            echo -e "  • Airflow UI (proxied): http://localhost/ → localhost:${AIRFLOW_PORT}"
            if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]]; then
                echo -e "  • AI Assistant API (proxied): http://localhost/ai/ → localhost:${AI_ASSISTANT_PORT}"
            fi
            echo ""
        fi

        echo -e "${CYAN}MCP Servers (Direct Access for LLMs):${NC}"
        echo -e "  • Airflow MCP: http://localhost:8889/sse"
        echo -e "    └─ Tools: DAG management (3), VM operations (5), Status (1)"
        if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]] && [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
            echo -e "  • AI Assistant MCP: http://localhost:8081"
            echo -e "    └─ Tools: Chat, query documents, RAG integration"
        fi
        echo ""

        echo -e "${CYAN}📖 Architecture & Documentation:${NC}"
        echo -e "  • Main: airflow/README.md"
        echo -e "  • MCP Servers: docs/MCP-SERVER-ARCHITECTURE.md"
        echo -e "  • Tools: airflow/TOOLS-AVAILABLE.md"
        echo ""
    fi

    echo -e "${BLUE}Next Steps:${NC}"
    echo -e "  1. Review deployment log: ${DEPLOYMENT_LOG}"
    echo -e "  2. Check running VMs: virsh list --all"
    echo -e "  3. Access Qubinode Navigator: /opt/qubinode-navigator"

    if [[ "$QUBINODE_ENABLE_AIRFLOW" == "true" ]]; then
        echo -e "  4. Access Airflow UI (port 80 via nginx or port ${AIRFLOW_PORT} direct)"
        echo -e "  5. Connect MCP servers to Claude Desktop for AI-powered automation"
        echo -e "     └─ Airflow MCP: http://localhost:8889/sse"
        if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]]; then
            echo -e "     └─ AI Assistant MCP: http://localhost:8081"
        fi
    fi

    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]]; then
        echo -e "  • Ask AI Assistant for guidance: http://localhost:${AI_ASSISTANT_PORT}/chat"
    fi

    echo ""
    log_success "Qubinode Navigator deployment completed successfully!"
}

show_failure_summary() {
    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                   DEPLOYMENT FAILED                          ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting Resources:${NC}"
    echo -e "  • Deployment log: ${DEPLOYMENT_LOG}"

    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]] && [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
        echo -e "  • AI Assistant: http://localhost:${AI_ASSISTANT_PORT}"
        echo -e "  • Ask AI for help with the specific error you encountered"
    fi

    echo -e "  • Check system resources: free -h && df -h"
    echo -e "  • Verify network connectivity: ping 8.8.8.8"
    echo -e "  • Check virtualization: grep -E '(vmx|svm)' /proc/cpuinfo"
    echo ""
    echo -e "${YELLOW}Common Solutions:${NC}"
    echo -e "  • Ensure you have sufficient resources (8GB+ RAM, 50GB+ disk)"
    echo -e "  • Enable virtualization in BIOS/UEFI"
    echo -e "  • Check internet connectivity"
    echo -e "  • Run as root user"
    echo ""
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Set up error handling
    trap cleanup_on_error ERR

    # Show banner
    show_banner

    # Start deployment log
    log_info "Starting Qubinode Navigator deployment..."
    log_info "Deployment log: $DEPLOYMENT_LOG"
    echo "Qubinode Navigator Deployment Log - $(date)" > "$DEPLOYMENT_LOG"

    # Execute deployment steps following ADR-0001 architecture
    get_rhel_version || exit 1
    check_prerequisites || exit 1
    validate_configuration || exit 1
    detect_deployment_target || exit 1  # New: Detect deployment target based on research
    start_ai_assistant  # Non-blocking, continues even if AI Assistant fails
    deploy_host_ai_services  # ADR-0050: Host AI services for hybrid architecture
    deploy_airflow_services  # Non-blocking, continues even if Airflow fails
    get_qubinode_navigator "$MY_DIR" || exit 1
    fix_dns_configuration || exit 1  # Auto-fix DNS configuration in inventory files
    # configure_environment || exit 1  # Commented out - users should configure .env manually to avoid overwriting
    deploy_qubinode_infrastructure "$MY_DIR" || exit 1
    setup_nginx_reverse_proxy  # Non-blocking, only active if Airflow is enabled
    sync_credentials_to_airflow  # Sync credentials to Airflow Variables
    bootstrap_rag_knowledge_base  # Bootstrap RAG with ADRs, DAGs, and docs
    verify_deployment || exit 1

    # Show completion summary
    show_completion_summary
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Deploy Qubinode Navigator on RHEL-based systems"
        echo ""
        echo "Environment Variables:"
        echo "  QUBINODE_DOMAIN              - Domain name (required)"
        echo "  QUBINODE_ADMIN_USER          - Admin username (required)"
        echo "  QUBINODE_CLUSTER_NAME        - Cluster name (required)"
        echo "  QUBINODE_DEPLOYMENT_MODE     - Deployment mode (default: production)"
        echo "  QUBINODE_ENABLE_AI_ASSISTANT - Enable AI Assistant (default: true)"
        echo "  BUILD_AI_ASSISTANT_FROM_SOURCE - Build AI Assistant from source (default: false)"
        echo "                                   Set to true for E2E testing with PydanticAI + Smart Pipeline"
        echo "  QUBINODE_ENABLE_AIRFLOW      - Enable Airflow orchestration (default: true)"
        echo "  QUBINODE_ENABLE_AI_SERVICES  - Enable host AI services (default: false, ADR-0050)"
        echo "  QUBINODE_ENABLE_NGINX_PROXY  - Enable nginx reverse proxy (auto-enabled with Airflow)"
        echo "  AI_ASSISTANT_PORT            - AI Assistant port (default: 8080)"
        echo "  AIRFLOW_PORT                 - Airflow webserver port (default: 8888)"
        echo "  EMBEDDING_SERVICE_PORT       - Embedding service port (default: 8891)"
        echo "  LITELLM_PROXY_PORT           - LiteLLM proxy port (default: 4000)"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --version, -v  Show version information"
        echo ""
        echo "Examples:"
        echo "  # Basic deployment with AI Assistant only"
        echo "  export QUBINODE_DOMAIN=example.com"
        echo "  export QUBINODE_ADMIN_USER=admin"
        echo "  export QUBINODE_CLUSTER_NAME=mycluster"
        echo "  ./deploy-qubinode.sh"
        echo ""
        echo "  # Deployment with Airflow orchestration"
        echo "  export QUBINODE_DOMAIN=example.com"
        echo "  export QUBINODE_ADMIN_USER=admin"
        echo "  export QUBINODE_CLUSTER_NAME=mycluster"
        echo "  export QUBINODE_ENABLE_AIRFLOW=true"
        echo "  ./deploy-qubinode.sh"
        echo ""
        echo "  # Full deployment with Airflow + Host AI Services (ADR-0050)"
        echo "  export QUBINODE_DOMAIN=example.com"
        echo "  export QUBINODE_ADMIN_USER=admin"
        echo "  export QUBINODE_CLUSTER_NAME=mycluster"
        echo "  export QUBINODE_ENABLE_AIRFLOW=true"
        echo "  export QUBINODE_ENABLE_AI_SERVICES=true"
        echo "  ./deploy-qubinode.sh"
        echo ""
        echo "  # E2E Testing with PydanticAI + Smart Pipeline (ADR-0066, ADR-0067)"
        echo "  # Builds AI Assistant from source with all latest features"
        echo "  export QUBINODE_DOMAIN=e2e.qubinode.local"
        echo "  export QUBINODE_ADMIN_USER=admin"
        echo "  export QUBINODE_CLUSTER_NAME=e2e-test"
        echo "  export QUBINODE_ENABLE_AIRFLOW=true"
        echo "  export BUILD_AI_ASSISTANT_FROM_SOURCE=true"
        echo "  export CICD_PIPELINE=true"
        echo "  ./deploy-qubinode.sh"
        echo ""
        echo "  # Using .env file"
        echo "  cat > .env << EOF"
        echo "  QUBINODE_DOMAIN=example.com"
        echo "  QUBINODE_ADMIN_USER=admin"
        echo "  QUBINODE_CLUSTER_NAME=mycluster"
        echo "  QUBINODE_ENABLE_AIRFLOW=true"
        echo "  EOF"
        echo "  ./deploy-qubinode.sh"
        exit 0
        ;;
    --version|-v)
        echo "Qubinode Navigator One-Shot Deployment v${SCRIPT_VERSION}"
        exit 0
        ;;
    "")
        # No arguments, proceed with deployment
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Handle script exit
if [[ "$DEPLOYMENT_FAILED" == "true" ]]; then
    show_failure_summary
    exit 1
fi
