# =============================================================================
# Qubinode Navigator Build System - The "Automation Assembly Line"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This Makefile provides automated build and management commands for Qubinode Navigator
# container images, ansible-navigator configuration, and development workflows.
# It implements ADR-0001 container-first execution model through standardized build processes.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This Makefile implements build automation:
# 1. [PHASE 1]: Environment Setup - Installs ansible-navigator and dependencies
# 2. [PHASE 2]: Container Building - Builds execution environment containers
# 3. [PHASE 3]: Configuration Management - Copies navigator configuration files
# 4. [PHASE 4]: Registry Integration - Handles container registry authentication
# 5. [PHASE 5]: Inventory Management - Provides inventory listing and validation
# 6. [PHASE 6]: Cleanup Operations - Removes unused images and failed builds
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Build Automation]: Automates container image building per ADR-0001
# - [Development Workflow]: Provides standardized commands for developers
# - [Container Management]: Manages execution environment containers
# - [Configuration Deployment]: Handles ansible-navigator configuration
# - [Registry Integration]: Manages Red Hat registry authentication
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Container-First]: All operations use containerized execution environments
# - [Standardized Commands]: Provides consistent interface for common operations
# - [Version Management]: Handles container image versioning and tagging
# - [Cleanup Automation]: Includes cleanup commands for development hygiene
# - [Registry Integration]: Supports Red Hat container registry authentication
#
# 💡 WHEN TO MODIFY THIS MAKEFILE (for future LLMs):
# - [Version Updates]: Update TAG variable for new releases
# - [New Commands]: Add new targets for additional automation needs
# - [Registry Changes]: Update registry URLs or authentication methods
# - [Build Enhancements]: Add new build options or optimization flags
# - [Cleanup Improvements]: Enhance cleanup commands for better resource management
#
# 🚨 IMPORTANT FOR LLMs: This Makefile manages container images and system configuration.
# It requires podman, ansible-navigator, and may require registry authentication.
# Changes affect build processes and development workflows.

.DEFAULT_GOAL := build

# 🔧 CONFIGURATION CONSTANTS FOR LLMs:
GIT_URL := https://github.com/tosin2013/qubinode_navigator.git  # Repository URL
TAG := 0.1.0  # Container image version tag - update for new releases
INSTALL_PATH = ~/.ansible-navigator.yml  # Navigator configuration destination
SOURCE_FILE = ~/qubinode_navigator/ansible-navigator/release-ansible-navigator.yml  # Navigator config source

# 📊 COMMAND DEFINITIONS (build automation commands):
INSTALL_ANSIBLE_NAVIGATOR := uv pip install ansible-navigator>=25.5.0  # Install navigator with minimum version
BUILD_CMD := tag=$(TAG) && cd ~/qubinode_navigator/ansible-builder/ && ansible-builder build -f execution-environment.yml -t qubinode-installer:$${tag} -v 3  # Build execution environment
COPY_NAVIGATOR_CMD := cp $(SOURCE_FILE) $(INSTALL_PATH)  # Copy navigator configuration
PODMAN_LOGIN := podman login registry.redhat.io  # Authenticate with Red Hat registry
LIST_INVENTORY_CMD := ansible-navigator inventory --list -m stdout  # List inventory in stdout mode
REMOVE_BAD_BUILDS := podman rmi $$(podman images | grep "<none>" | awk '{print $$3}')  # Remove failed builds
REMOVE_IMAGES := podman rmi $$(podman images | grep "qubinode-installer" | awk '{print $$3}')  # Remove all qubinode images

# Ansible Navigator Installer - The "Tool Provisioner"
# 🎯 FOR LLMs: Installs ansible-navigator with minimum required version
.PHONY: install-ansible-navigator
install-ansible-navigator:
	$(INSTALL_ANSIBLE_NAVIGATOR)

# Container Image Builder - The "Execution Environment Creator"
# 🎯 FOR LLMs: Builds qubinode-installer container with all required dependencies
.PHONY: build-image
build-image:
	$(BUILD_CMD)

# Registry Authenticator - The "Credential Manager"
# 🎯 FOR LLMs: Authenticates with Red Hat container registry for base image access
.PHONY: podman-login
podman-login:
	$(PODMAN_LOGIN)

# Configuration Deployer - The "Settings Manager"
# 🎯 FOR LLMs: Copies ansible-navigator configuration to user home directory
.PHONY: copy-navigator
copy-navigator:
	$(COPY_NAVIGATOR_CMD)

# Inventory Lister - The "Environment Inspector"
# 🎯 FOR LLMs: Lists all available inventory configurations for validation
.PHONY: list-inventory
list-inventory:
	$(LIST_INVENTORY_CMD)

# Failed Build Cleaner - The "Build Janitor"
# 🎯 FOR LLMs: Removes failed container builds with <none> tags
.PHONY: remove-bad-builds
remove-bad-builds:
	$(REMOVE_BAD_BUILDS)

# Image Cleaner - The "Storage Manager"
# 🎯 FOR LLMs: Removes all qubinode-installer images to free disk space
.PHONY: remove-images
remove-images:
	$(REMOVE_IMAGES)

# =============================================================================
# MCP Server Testing Targets - The "MCP Validator"
# =============================================================================
# 🎯 FOR LLMs: Tests MCP servers using ansible-collection-mcp-audit
# These targets validate that MCP tools are working correctly

# MCP Collection Installer - The "Test Framework Provisioner"
# 🎯 FOR LLMs: Installs ansible-collection-mcp-audit from Galaxy
.PHONY: mcp-install
mcp-install:
	@echo "🔧 Installing ansible-collection-mcp-audit..."
	ansible-galaxy collection install tosin2013.mcp_audit --force

# AI Assistant MCP Tester - The "AI MCP Validator"
# 🎯 FOR LLMs: Tests AI Assistant MCP server (port 8081) with 3 tools
.PHONY: test-mcp-ai
test-mcp-ai: mcp-install
	@echo "🧪 Testing AI Assistant MCP Server..."
	@ansible-playbook tests/mcp/test_ai_assistant_mcp.yml

# Airflow MCP Tester - The "Airflow MCP Validator"
# 🎯 FOR LLMs: Tests Airflow MCP server (port 8889) with 9 tools
.PHONY: test-mcp-airflow
test-mcp-airflow: mcp-install
	@echo "🧪 Testing Airflow MCP Server..."
	@ansible-playbook tests/mcp/test_airflow_mcp.yml

# Comprehensive MCP Tester - The "Full MCP Validator"
# 🎯 FOR LLMs: Runs complete test suite for both MCP servers
.PHONY: test-mcp
test-mcp: mcp-install
	@echo "🧪 Running comprehensive MCP test suite..."
	@ansible-playbook tests/mcp/test_mcp_suite.yml

# MCP Test Reporter - The "Test Results Viewer"
# 🎯 FOR LLMs: Runs tests and displays generated reports
.PHONY: test-mcp-report
test-mcp-report: test-mcp
	@echo ""
	@echo "📊 === MCP Test Reports ==="
	@ls -lh tests/mcp/*.md 2>/dev/null || echo "No reports generated yet"
	@echo ""
	@echo "📖 View reports with:"
	@echo "  cat tests/mcp/ai_assistant_test_report.md"
	@echo "  cat tests/mcp/airflow_test_report.md"
	@echo "  cat tests/mcp/comprehensive_test_report.md"
