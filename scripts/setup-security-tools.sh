#!/bin/bash
# DevSecOps Security Tools Setup Script
# Installs Gitleaks, BFG Repo-Cleaner, and pre-commit hooks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔧 Setting up DevSecOps security tools..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Gitleaks
install_gitleaks() {
    echo "📦 Installing Gitleaks..."

    if command_exists gitleaks; then
        echo "✅ Gitleaks already installed: $(gitleaks version)"
        return 0
    fi

    # Detect OS and architecture
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)

    case $ARCH in
        x86_64) ARCH="x64" ;;
        aarch64|arm64) ARCH="arm64" ;;
        *) echo "❌ Unsupported architecture: $ARCH"; exit 1 ;;
    esac

    # Download latest Gitleaks
    GITLEAKS_VERSION="8.18.0"
    GITLEAKS_URL="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_${OS}_${ARCH}.tar.gz"

    echo "📥 Downloading Gitleaks v${GITLEAKS_VERSION}..."
    curl -sSL "$GITLEAKS_URL" | tar -xz -C /tmp

    # Install to /usr/local/bin (requires sudo) or ~/.local/bin
    if [[ $EUID -eq 0 ]] || sudo -n true 2>/dev/null; then
        sudo mv /tmp/gitleaks /usr/local/bin/
        echo "✅ Gitleaks installed to /usr/local/bin/gitleaks"
    else
        mkdir -p ~/.local/bin
        mv /tmp/gitleaks ~/.local/bin/
        echo "✅ Gitleaks installed to ~/.local/bin/gitleaks"
        echo "⚠️  Make sure ~/.local/bin is in your PATH"
    fi
}

# Install BFG Repo-Cleaner
install_bfg() {
    echo "📦 Installing BFG Repo-Cleaner..."

    if command_exists bfg; then
        echo "✅ BFG already installed"
        return 0
    fi

    # Check for Java
    if ! command_exists java; then
        echo "❌ Java is required for BFG Repo-Cleaner"
        echo "   Install Java: sudo apt-get install openjdk-11-jre-headless"
        exit 1
    fi

    # Download BFG
    BFG_VERSION="1.14.0"
    BFG_URL="https://repo1.maven.org/maven2/com/madgag/bfg/${BFG_VERSION}/bfg-${BFG_VERSION}.jar"

    echo "📥 Downloading BFG Repo-Cleaner v${BFG_VERSION}..."
    curl -sSL "$BFG_URL" -o /tmp/bfg.jar

    # Install BFG
    if [[ $EUID -eq 0 ]] || sudo -n true 2>/dev/null; then
        sudo mv /tmp/bfg.jar /usr/local/bin/bfg.jar
        sudo tee /usr/local/bin/bfg > /dev/null << 'EOF'
#!/bin/bash
java -jar /usr/local/bin/bfg.jar "$@"
EOF
        sudo chmod +x /usr/local/bin/bfg
        echo "✅ BFG installed to /usr/local/bin/bfg"
    else
        mkdir -p ~/.local/bin
        mv /tmp/bfg.jar ~/.local/bin/bfg.jar
        cat > ~/.local/bin/bfg << 'EOF'
#!/bin/bash
java -jar ~/.local/bin/bfg.jar "$@"
EOF
        chmod +x ~/.local/bin/bfg
        echo "✅ BFG installed to ~/.local/bin/bfg"
    fi
}

# Install pre-commit
install_precommit() {
    echo "📦 Installing pre-commit..."

    if command_exists pre-commit; then
        echo "✅ pre-commit already installed: $(pre-commit --version)"
        return 0
    fi

    if command_exists uv; then
        uv pip install pre-commit
        echo "✅ pre-commit installed via uv"
    elif command_exists pip3; then
        pip3 install --user pre-commit
        echo "✅ pre-commit installed via pip3"
    elif command_exists pip; then
        pip install --user pre-commit
        echo "✅ pre-commit installed via pip"
    else
        echo "❌ uv/pip/pip3 not found. Install Python package manager first."
        exit 1
    fi
}

# Create backup directory
create_backup_structure() {
    echo "📁 Creating backup directory structure..."

    BACKUP_DIR="$PROJECT_ROOT/.security-backups"
    mkdir -p "$BACKUP_DIR"/{git-bundles,file-backups,scan-results}

    echo "✅ Backup structure created at $BACKUP_DIR"
}

# Main installation
main() {
    echo "🚀 Starting DevSecOps tools installation..."

    install_gitleaks
    install_bfg
    install_precommit
    create_backup_structure

    echo ""
    echo "🎉 Installation complete!"
    echo ""
    echo "Next steps:"
    echo "1. Run: ./scripts/create-repository-backup.sh"
    echo "2. Configure: .gitleaks.toml"
    echo "3. Scan: ./scripts/security-scan.sh"
    echo ""
    echo "⚠️  IMPORTANT: Create a full repository backup before any cleanup operations!"
}

main "$@"
