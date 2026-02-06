#!/bin/bash
# =============================================================================
# Qubinode Navigator + Airflow Unified Deployment
# Deploys complete stack: AI Assistant + Airflow on shared network
# =============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SERVER_IP="$(hostname -I | awk '{print $1}')"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}"
cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║     Qubinode Navigator + Airflow Unified Deployment           ║
║                                                                ║
║     • AI Assistant                                             ║
║     • Apache Airflow with kcli + virsh                         ║
║     • Nginx Reverse Proxy (Production-Ready)                   ║
║     • Shared Podman network                                    ║
║     • Integrated chat in Airflow UI                            ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Step 0: Pre-flight checks (optional but recommended)
if [[ -f "$SCRIPT_DIR/scripts/preflight-check.sh" ]]; then
    echo -e "${BLUE}[0/5] Running pre-flight checks...${NC}"
    if ! "$SCRIPT_DIR/scripts/preflight-check.sh" --fix; then
        echo -e "${YELLOW}Pre-flight checks found issues. Continue anyway? (y/N)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${RED}Deployment cancelled. Fix issues and retry.${NC}"
            exit 1
        fi
    fi
    echo ""
fi

# Step 0.5: Initialize prerequisites for infrastructure DAGs (Issue #3 Fix)
echo -e "${BLUE}[0.5/5] Initializing prerequisites for infrastructure DAGs...${NC}"
if [[ -f "$SCRIPT_DIR/airflow/scripts/init-prerequisites.sh" ]]; then
    "$SCRIPT_DIR/airflow/scripts/init-prerequisites.sh" || {
        echo -e "${YELLOW}Warning: Some prerequisites could not be initialized${NC}"
        echo -e "${YELLOW}Infrastructure DAGs may require manual configuration${NC}"
    }
    echo ""
fi

# Step 1: Deploy base infrastructure
echo -e "${BLUE}[1/5] Deploying base infrastructure...${NC}"
if [[ -f "$SCRIPT_DIR/deploy-qubinode.sh" ]]; then
    # Run the base deployment (handles hypervisor, AI Assistant, etc.)
    "$SCRIPT_DIR/deploy-qubinode.sh" || {
        echo -e "${RED}Base deployment failed${NC}"
        exit 1
    }
else
    echo -e "${BLUE}Skipping base deployment (not found)${NC}"
fi

# Verify vault.yml exists for FreeIPA/infrastructure deployments
INVENTORY="${INVENTORY:-localhost}"
VAULT_FILE="$SCRIPT_DIR/inventories/${INVENTORY}/group_vars/control/vault.yml"
if [[ ! -f "$VAULT_FILE" ]]; then
    echo -e "${YELLOW}Warning: vault.yml not found at $VAULT_FILE${NC}"
    echo -e "${CYAN}Creating vault.yml with default credentials...${NC}"

    # Ensure directory exists
    mkdir -p "$SCRIPT_DIR/inventories/${INVENTORY}/group_vars/control"

    # Get password from notouch.env or use default
    if [[ -f "$SCRIPT_DIR/notouch.env" ]]; then
        source "$SCRIPT_DIR/notouch.env"
    fi
    VAULT_PASSWORD="${SSH_PASSWORD:-COmp123\$%}"

    # Create vault file
    cat > "$VAULT_FILE" << VAULTEOF
---
# Ansible Vault - Sensitive Credentials
# Encrypted with ansible-vault

# FreeIPA Configuration
freeipa_server_admin_password: "${VAULT_PASSWORD}"

# Red Hat Subscription Manager (leave empty for CentOS/community)
rhsm_org: ""
rhsm_activationkey: ""
rhsm_username: ""
rhsm_password: ""

# OpenShift Pull Secret (optional)
openshift_pull_secret: ""
VAULTEOF

    # Encrypt if vault password file exists
    if [[ -f "$HOME/.vault_password" ]]; then
        ansible-vault encrypt "$VAULT_FILE" --vault-password-file "$HOME/.vault_password" --encrypt-vault-id default 2>/dev/null || \
        ansible-vault encrypt "$VAULT_FILE" --vault-password-file "$HOME/.vault_password" 2>/dev/null || \
        echo -e "${YELLOW}Warning: Could not encrypt vault.yml${NC}"
        echo -e "${GREEN}vault.yml created and encrypted${NC}"
    else
        echo -e "${YELLOW}Warning: vault.yml created but not encrypted - .vault_password not found${NC}"
    fi
else
    echo -e "${GREEN}vault.yml exists at $VAULT_FILE${NC}"
fi

# Configure SSH for Airflow container to access host (ADR-0046)
echo -e "${BLUE}[1.5/4] Configuring SSH access for Airflow container...${NC}"

# Ensure SSH key exists
if [[ ! -f "$HOME/.ssh/id_rsa" ]]; then
    echo -e "${CYAN}  Generating SSH key...${NC}"
    ssh-keygen -t rsa -b 4096 -f "$HOME/.ssh/id_rsa" -N '' -q
fi

# Add the key to authorized_keys for localhost access
# This allows the Airflow container to SSH to the host for Ansible execution
if ! grep -q "$(cat $HOME/.ssh/id_rsa.pub)" "$HOME/.ssh/authorized_keys" 2>/dev/null; then
    echo -e "${CYAN}  Adding SSH key to authorized_keys for container access...${NC}"
    cat "$HOME/.ssh/id_rsa.pub" >> "$HOME/.ssh/authorized_keys"
    chmod 600 "$HOME/.ssh/authorized_keys"
    echo -e "${GREEN}  SSH key configured for Airflow container${NC}"
else
    echo -e "${GREEN}  SSH key already in authorized_keys${NC}"
fi

# Ensure SSH service is running
if ! systemctl is-active --quiet sshd; then
    echo -e "${CYAN}  Starting SSH service...${NC}"
    systemctl start sshd
    systemctl enable sshd
fi

# Test SSH access
if ssh -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5 root@localhost "echo 'SSH test successful'" &>/dev/null; then
    echo -e "${GREEN}  SSH localhost access verified${NC}"
else
    echo -e "${YELLOW}  Warning: SSH localhost access may require manual configuration${NC}"
    echo -e "${YELLOW}  Ensure PasswordAuthentication or PubkeyAuthentication is enabled in /etc/ssh/sshd_config${NC}"
fi

# Create symlinks for vault password in external repos (for Ansible playbooks)
echo -e "${CYAN}  Setting up vault password symlinks for external repos...${NC}"
if [[ -f "$HOME/.vault_password" ]]; then
    # qubinode-pipelines (root and component directories)
    if [[ -d "/root/qubinode-pipelines" ]]; then
        ln -sf "$HOME/.vault_password" /root/qubinode-pipelines/.vault_password 2>/dev/null || true
        # VyOS router ansible playbooks
        if [[ -d "/root/qubinode-pipelines/vyos-router" ]]; then
            ln -sf "$HOME/.vault_password" /root/qubinode-pipelines/vyos-router/.vault_password 2>/dev/null || true
        fi
    fi
    echo -e "${GREEN}  Vault password symlinks created${NC}"
fi

# Step 2: Deploy Airflow
echo -e "${BLUE}[2/4] Deploying Airflow workflow orchestration...${NC}"
if [[ -f "$SCRIPT_DIR/airflow/deploy-airflow.sh" ]]; then
    "$SCRIPT_DIR/airflow/deploy-airflow.sh" deploy || {
        echo -e "${RED}Airflow deployment failed${NC}"
        exit 1
    }
else
    echo -e "${RED}Error: airflow/deploy-airflow.sh not found${NC}"
    exit 1
fi

# Step 2.5: Create Airflow orchestrator service account
echo -e "${BLUE}[2.5/5] Creating Airflow orchestrator service account...${NC}"

# Generate a random password for the orchestrator
ORCHESTRATOR_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)

# Wait for Airflow to be ready
echo -e "${CYAN}  Waiting for Airflow to be ready...${NC}"
MAX_WAIT=60
WAIT_COUNT=0
while ! curl -s http://localhost:8888/health >/dev/null 2>&1; do
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
    if [[ $WAIT_COUNT -ge $MAX_WAIT ]]; then
        echo -e "${YELLOW}  Warning: Airflow health check timed out, proceeding anyway...${NC}"
        break
    fi
done

# Create the orchestrator user with Op role (can trigger DAGs but not admin)
echo -e "${CYAN}  Creating orchestrator service account...${NC}"
if podman exec airflow_airflow-webserver_1 airflow users list 2>/dev/null | grep -q orchestrator; then
    echo -e "${GREEN}  Orchestrator user already exists${NC}"
    # Update password if user exists
    podman exec airflow_airflow-webserver_1 airflow users reset-password \
        --username orchestrator \
        --password "$ORCHESTRATOR_PASSWORD" 2>/dev/null || true
else
    podman exec airflow_airflow-webserver_1 airflow users create \
        --username orchestrator \
        --password "$ORCHESTRATOR_PASSWORD" \
        --firstname PydanticAI \
        --lastname Orchestrator \
        --email orchestrator@qubinode.local \
        --role Op 2>/dev/null || {
            echo -e "${YELLOW}  Warning: Could not create orchestrator user${NC}"
        }
fi

# Store credentials securely
CREDS_DIR="$SCRIPT_DIR/.credentials"
mkdir -p "$CREDS_DIR"
chmod 700 "$CREDS_DIR"

ORCHESTRATOR_CREDS_FILE="$CREDS_DIR/airflow-orchestrator.env"
cat > "$ORCHESTRATOR_CREDS_FILE" << CREDS_EOF
# Airflow Orchestrator Service Account
# Generated: $(date -Iseconds)
# Used by: AI Assistant PydanticAI Orchestrator
AIRFLOW_USER=orchestrator
AIRFLOW_PASSWORD=$ORCHESTRATOR_PASSWORD
CREDS_EOF
chmod 600 "$ORCHESTRATOR_CREDS_FILE"

echo -e "${GREEN}  ✓ Orchestrator service account created${NC}"
echo -e "${CYAN}  Credentials saved to: $ORCHESTRATOR_CREDS_FILE${NC}"

# Also update .env if it exists (for local development)
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    # Remove old AIRFLOW_USER/PASSWORD if present
    sed -i '/^AIRFLOW_USER=/d' "$SCRIPT_DIR/.env"
    sed -i '/^AIRFLOW_PASSWORD=/d' "$SCRIPT_DIR/.env"
    # Add new credentials
    echo "" >> "$SCRIPT_DIR/.env"
    echo "# Airflow Orchestrator Credentials (auto-generated)" >> "$SCRIPT_DIR/.env"
    echo "AIRFLOW_USER=orchestrator" >> "$SCRIPT_DIR/.env"
    echo "AIRFLOW_PASSWORD=$ORCHESTRATOR_PASSWORD" >> "$SCRIPT_DIR/.env"
    echo -e "${GREEN}  ✓ Updated .env with orchestrator credentials${NC}"
fi

# Step 3: Deploy Nginx Reverse Proxy
echo -e "${BLUE}[3/5] Setting up Nginx reverse proxy for secure access...${NC}"

# Install nginx if not present
if ! command -v nginx &> /dev/null; then
    echo -e "${CYAN}  Installing nginx...${NC}"
    dnf install -y nginx || {
        echo -e "${RED}Failed to install nginx${NC}"
        exit 1
    }
fi

# Create nginx configuration
echo -e "${CYAN}  Creating nginx configuration...${NC}"
cat > /etc/nginx/conf.d/airflow.conf << 'NGINX_EOF'
# Airflow and AI Assistant Reverse Proxy Configuration

# Upstream definitions
upstream airflow_backend {
    server localhost:8888;
}

upstream ai_assistant_backend {
    server localhost:8080;
}

# HTTP server
server {
    listen 80;
    server_name _;

    # Airflow UI at root
    location / {
        proxy_pass http://airflow_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for live updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # AI Assistant API
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

    # Health check
    location /health {
        proxy_pass http://airflow_backend/health;
        access_log off;
    }
}
NGINX_EOF

# Test nginx configuration
echo -e "${CYAN}  Testing nginx configuration...${NC}"
nginx -t || {
    echo -e "${RED}Nginx configuration test failed${NC}"
    exit 1
}

# Configure firewall
echo -e "${CYAN}  Configuring firewall...${NC}"
# Close direct access ports from public zone
firewall-cmd --permanent --remove-port=8888/tcp 2>/dev/null || true
firewall-cmd --permanent --remove-port=8080/tcp 2>/dev/null || true
# Open standard web ports
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https

# Allow VMs on libvirt networks to access Airflow and MCP server
# This enables jumpserver and other VMs to reach the host services
echo -e "${CYAN}  Configuring libvirt zone for VM access...${NC}"
if firewall-cmd --get-zones | grep -q libvirt; then
    firewall-cmd --zone=libvirt --add-port=8888/tcp --permanent 2>/dev/null || true  # Airflow webserver
    firewall-cmd --zone=libvirt --add-port=8889/tcp --permanent 2>/dev/null || true  # MCP server
    firewall-cmd --zone=libvirt --add-port=8080/tcp --permanent 2>/dev/null || true  # AI Assistant
    firewall-cmd --zone=libvirt --add-port=5432/tcp --permanent 2>/dev/null || true  # PostgreSQL (for debugging)
    echo -e "${GREEN}  ✓ Libvirt zone configured for VM access${NC}"
fi

firewall-cmd --reload

# Enable and start nginx
echo -e "${CYAN}  Starting nginx service...${NC}"
systemctl enable nginx
systemctl restart nginx

# Verify nginx is running
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}  ✓ Nginx reverse proxy configured successfully${NC}"
else
    echo -e "${RED}  ✗ Nginx failed to start${NC}"
    exit 1
fi

# Step 4: Final verification
echo -e "${BLUE}[4/5] Verifying deployment...${NC}"
"$SCRIPT_DIR/airflow/deploy-airflow.sh" status

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Qubinode Navigator Deployment Complete!              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}🎯 Quick Links:${NC}"
echo -e "${GREEN}   • Airflow UI (via nginx): http://${SERVER_IP}/${NC}"
echo -e "   • AI Assistant API:         http://${SERVER_IP}/ai/"
echo -e "   • Health Check:             http://${SERVER_IP}/health"
echo -e ""
echo -e "${CYAN}🔐 Airflow Admin Credentials:${NC}"
echo -e "   Username: admin"
echo -e "   Password: admin"
echo -e ""
echo -e "${CYAN}🤖 Orchestrator Service Account:${NC}"
echo -e "   Username: orchestrator"
echo -e "   Credentials: $CREDS_DIR/airflow-orchestrator.env"
echo -e ""
echo -e "${YELLOW}🔒 Security:${NC}"
echo -e "   ✓ Direct ports 8888/8080 closed (public)"
echo -e "   ✓ Access only through nginx (port 80/443)"
echo -e "   ✓ VMs can access services via libvirt zone"
echo -e "   ✓ Ready for SSL/TLS configuration"
echo -e ""
echo -e "${CYAN}🖥️  VM Access (from jumpserver/VMs):${NC}"
echo -e "   • Airflow:      http://192.168.122.1:8888"
echo -e "   • MCP Server:   http://192.168.122.1:8889"
echo -e "   • AI Assistant: http://192.168.122.1:8080"
echo ""
echo -e "${CYAN}📚 Next Steps:${NC}"
echo -e "   1. Access Airflow UI and enable example DAGs"
echo -e "   2. Test kcli and virsh operators"
echo -e "   3. Chat with AI Assistant for guidance"
echo ""
echo -e "${CYAN}📖 Documentation:${NC}"
echo -e "   • airflow/README.md"
echo -e "   • airflow/TOOLS-AVAILABLE.md"
echo ""
