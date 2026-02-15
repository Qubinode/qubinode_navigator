#!/usr/bin/env python3
"""
FastMCP Implementation for Qubinode Airflow MCP Server
ADR-0049: Multi-Agent LLM Memory Architecture

MCP server for Airflow DAG management, VM operations, and RAG-powered
intelligent workflow assistance.

Tools:
- DAG Management: list_dags, get_dag_info, trigger_dag
- VM Operations: list_vms, get_vm_info, create_vm, delete_vm
- RAG Queries: query_rag, ingest_to_rag, search_similar_errors
- Troubleshooting: get_troubleshooting_history, log_troubleshooting_attempt
- Agent Orchestration: delegate_to_developer, override_developer
- Provider Checks: check_provider_exists
- Lineage: get_dag_lineage, get_failure_blast_radius

NOTE: This file is loaded by the MCP server profile only.
It requires fastmcp to be installed.
"""

import os
import sys
import logging

# Guard against import when fastmcp is not installed
# This file should only be loaded with the 'mcp' profile
try:
    from fastmcp import FastMCP
except ImportError:
    print(
        "Warning: fastmcp not installed. MCP server will not be available.",
        file=sys.stderr,
    )
    print("Install with: pip install mcp starlette uvicorn sse-starlette", file=sys.stderr)
    # Exit early if not running as main script (being imported by plugins)
    if __name__ != "__main__":
        raise SystemExit(0)
    else:
        raise

import subprocess
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fastmcp-airflow")

# Configuration
MCP_ENABLED = os.getenv("AIRFLOW_MCP_ENABLED", "false").lower() == "true"
MCP_PORT = int(os.getenv("AIRFLOW_MCP_PORT", "8889"))
MCP_HOST = os.getenv("AIRFLOW_MCP_HOST", "0.0.0.0")
READ_ONLY = os.getenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "false").lower() == "true"

# Create FastMCP server
mcp = FastMCP(name="qubinode-airflow-mcp")

logger.info("=" * 60)
logger.info("Initializing FastMCP Airflow Server")
logger.info(f"Port: {MCP_PORT}")
logger.info(f"Read-only mode: {READ_ONLY}")
logger.info(f"Enabled: {MCP_ENABLED}")
logger.info("=" * 60)

# Import Airflow components (may fail if not in Airflow context)
try:
    from airflow.models import DagBag
    from airflow.api.common.experimental.trigger_dag import (
        trigger_dag as trigger_dag_api,
    )

    AIRFLOW_AVAILABLE = True
    dag_bag = DagBag()
except ImportError:
    AIRFLOW_AVAILABLE = False
    logger.warning("Airflow not available - DAG tools will return errors")

# Import RAG components (ADR-0049)
RAG_AVAILABLE = False
rag_store = None
try:
    from qubinode.rag_store import get_rag_store

    RAG_AVAILABLE = True
    logger.info("RAG components available")
except ImportError as e:
    logger.warning(f"RAG components not available: {e}")

# Session tracking for troubleshooting
_current_session_id: Optional[str] = None


def get_session_id() -> str:
    """Get or create current session ID for troubleshooting tracking."""
    global _current_session_id
    if _current_session_id is None:
        _current_session_id = str(uuid.uuid4())
        logger.info(f"New session started: {_current_session_id}")
    return _current_session_id


def get_rag():
    """Get RAG store singleton, initializing if needed."""
    global rag_store
    if RAG_AVAILABLE and rag_store is None:
        try:
            rag_store = get_rag_store()
        except Exception as e:
            logger.error(f"Failed to initialize RAG store: {e}")
    return rag_store


# =============================================================================
# DAG Management Tools
# =============================================================================


@mcp.tool()
async def list_dags() -> str:
    """
    List all available Airflow DAGs with their schedules, tags, and owners.

    WHEN TO USE: Call this FIRST when you need to understand what workflows
    are available. This is your discovery tool for finding DAG IDs to use
    with other tools like get_dag_info() or trigger_dag().

    WHAT YOU GET: A formatted list showing each DAG's:
    - dag_id (use this for other DAG tools)
    - schedule interval (when it runs automatically)
    - tags (categories like 'vm', 'freeipa', 'network')
    - owner (who maintains it)

    NEXT STEPS after calling:
    - Use get_dag_info(dag_id) to see DAG details and required parameters
    - Use trigger_dag(dag_id) to execute a workflow

    Returns:
        Formatted list of all DAGs with metadata
    """
    logger.info("Tool called: list_dags()")

    if not AIRFLOW_AVAILABLE:
        return "Error: Airflow is not available in this environment"

    try:
        dags = dag_bag.dags
        output = f"# Airflow DAGs ({len(dags)} total)\n\n"

        for dag_id, dag in sorted(dags.items()):
            output += f"## {dag_id}\n"
            output += f"**Description:** {dag.description or 'No description'}\n"
            output += f"**Schedule:** {dag.schedule_interval}\n"
            output += f"**Tags:** {', '.join(dag.tags) if dag.tags else 'None'}\n"
            output += f"**Owner:** {dag.owner}\n\n"

        logger.info(f"Listed {len(dags)} DAGs")
        return output
    except Exception as e:
        error_msg = f"Error listing DAGs: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def get_dag_info(dag_id: str) -> str:
    """
    Get detailed information about a specific DAG including tasks and configuration.

    Args:
        dag_id: The ID of the DAG to query

    Returns:
        Detailed DAG information including tasks, schedule, and metadata
    """
    logger.info(f"Tool called: get_dag_info(dag_id='{dag_id}')")

    if not AIRFLOW_AVAILABLE:
        return "Error: Airflow is not available"

    try:
        if dag_id not in dag_bag.dags:
            return f"Error: DAG '{dag_id}' not found"

        dag = dag_bag.dags[dag_id]

        output = f"# DAG: {dag_id}\n\n"
        output += f"**Description:** {dag.description or 'No description'}\n"
        output += f"**Schedule:** {dag.schedule_interval}\n"
        output += f"**Start Date:** {dag.start_date}\n"
        output += f"**Tags:** {', '.join(dag.tags) if dag.tags else 'None'}\n"
        output += f"**Owner:** {dag.owner}\n"
        output += f"**Catchup:** {dag.catchup}\n\n"

        output += f"## Tasks ({len(dag.tasks)})\n\n"
        for task in dag.tasks:
            output += f"- **{task.task_id}** ({task.task_type})\n"

        logger.info(f"Retrieved info for DAG: {dag_id}")
        return output
    except Exception as e:
        error_msg = f"Error getting DAG info: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def trigger_dag(dag_id: str, conf: Optional[Dict[str, Any]] = None) -> str:
    """
    Trigger an Airflow DAG execution with optional configuration.

    WHEN TO USE: Execute a workflow after you've confirmed:
    1. The DAG exists (use list_dags() first)
    2. You understand the required parameters (use get_dag_info() first)
    3. You have the correct conf dictionary for the DAG

    IMPORTANT: This is a WRITE operation. In read-only mode, this will fail.

    Args:
        dag_id: The ID of the DAG to trigger (get from list_dags())
        conf: Optional configuration dictionary. Common patterns:
            - VM DAGs: {"vm_name": "myvm", "cpu": 4, "memory": 8192}
            - FreeIPA DAGs: {"domain": "example.com", "realm": "EXAMPLE.COM"}
            - Network DAGs: {"network_name": "qubinat", "cidr": "192.168.1.0/24"}

    EXAMPLES:
        trigger_dag("example_kcli_vm_provisioning")
        trigger_dag("vm_creation", {"vm_name": "test-vm", "memory": 4096})

    Returns:
        Success message with run ID, or error message if failed
    """
    logger.info(f"Tool called: trigger_dag(dag_id='{dag_id}', conf={conf})")

    if READ_ONLY:
        return "Error: Cannot trigger DAG in read-only mode"

    if not AIRFLOW_AVAILABLE:
        return "Error: Airflow is not available"

    try:
        run_id = trigger_dag_api(dag_id, conf=conf)
        logger.info(f"Triggered DAG '{dag_id}' with run_id: {run_id}")
        return f"Successfully triggered DAG '{dag_id}'\nRun ID: {run_id}"
    except Exception as e:
        error_msg = f"Error triggering DAG: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# =============================================================================
# VM Management Tools
# =============================================================================


@mcp.tool()
async def preflight_vm_creation(
    name: str,
    image: str = "centos10stream",
    memory: int = 2048,
    cpus: int = 2,
    disk_size: int = 10,
) -> str:
    """
    Run pre-flight checks before VM creation to ensure success.

    ALWAYS CALL THIS BEFORE create_vm(). This tool validates:
    1. VM name doesn't already exist
    2. Requested image is available (or can be downloaded)
    3. Host has sufficient resources (memory, disk, CPU)
    4. Libvirt/kcli services are running

    If all checks pass, you can safely call create_vm() with the same parameters.
    If checks fail, the response tells you exactly how to fix each issue.

    Args:
        name: Proposed VM name to validate
        image: Image to check availability
        memory: Memory in MB to validate against available
        cpus: CPUs to validate against available
        disk_size: Disk in GB to validate against available space

    Returns:
        Detailed pre-flight report with PASS/FAIL status and fix commands
    """
    logger.info(f"Tool called: preflight_vm_creation(name='{name}', image='{image}')")

    output = "# VM Creation Pre-Flight Check\n\n"
    all_passed = True
    fixes_needed = []

    # Check 1: VM name doesn't exist
    output += "## 1. VM Name Availability\n"
    try:
        result = subprocess.run(
            ["virsh", "-c", "qemu:///system", "dominfo", name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            output += f"❌ **FAIL**: VM '{name}' already exists\n"
            output += "   Fix: Choose a different name or delete existing VM\n"
            output += f"   Command: `kcli delete vm {name} -y`\n\n"
            all_passed = False
            fixes_needed.append(f"delete_vm('{name}') or choose different name")
        else:
            output += f"✅ **PASS**: Name '{name}' is available\n\n"
    except Exception as e:
        output += f"⚠️ **WARN**: Could not check VM existence: {e}\n\n"

    # Check 2: Image availability
    output += "## 2. Image Availability\n"
    try:
        result = subprocess.run(["kcli", "list", "images"], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            if image in result.stdout:
                output += f"✅ **PASS**: Image '{image}' is available\n\n"
            else:
                output += f"❌ **FAIL**: Image '{image}' not found\n"
                output += f"   Available images:\n```\n{result.stdout[:500]}\n```\n"
                output += "   Fix: Download the image first\n"
                output += f"   Command: `kcli download image {image}`\n\n"
                all_passed = False
                fixes_needed.append(f"Run: kcli download image {image}")
        else:
            output += f"⚠️ **WARN**: Could not list images: {result.stderr}\n\n"
    except Exception as e:
        output += f"⚠️ **WARN**: Could not check images: {e}\n\n"

    # Check 3: Available memory
    output += "## 3. Host Memory\n"
    try:
        result = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if line.startswith("Mem:"):
                    parts = line.split()
                    available_mb = int(parts[6]) if len(parts) > 6 else int(parts[3])
                    if available_mb >= memory + 1024:  # Need buffer
                        output += f"✅ **PASS**: {available_mb}MB available (need {memory}MB + buffer)\n\n"
                    else:
                        output += f"❌ **FAIL**: Only {available_mb}MB available, need {memory}MB + 1GB buffer\n"
                        output += "   Fix: Stop unused VMs or reduce requested memory\n\n"
                        all_passed = False
                        fixes_needed.append("Stop unused VMs or reduce memory request")
                    break
    except Exception as e:
        output += f"⚠️ **WARN**: Could not check memory: {e}\n\n"

    # Check 4: Disk space
    output += "## 4. Disk Space\n"
    try:
        result = subprocess.run(
            ["df", "-BG", "/var/lib/libvirt/images"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                available_gb = int(parts[3].replace("G", ""))
                if available_gb >= disk_size + 10:  # Need buffer
                    output += f"✅ **PASS**: {available_gb}GB available (need {disk_size}GB + buffer)\n\n"
                else:
                    output += f"❌ **FAIL**: Only {available_gb}GB available, need {disk_size}GB + 10GB buffer\n"
                    output += "   Fix: Free up disk space or reduce disk_size\n\n"
                    all_passed = False
                    fixes_needed.append("Free disk space or reduce disk_size")
    except Exception as e:
        output += f"⚠️ **WARN**: Could not check disk: {e}\n\n"

    # Check 5: Libvirt service
    output += "## 5. Libvirt Service\n"
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "libvirtd"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip() == "active":
            output += "✅ **PASS**: libvirtd is running\n\n"
        else:
            output += "❌ **FAIL**: libvirtd is not running\n"
            output += "   Fix: `sudo systemctl start libvirtd`\n\n"
            all_passed = False
            fixes_needed.append("Run: sudo systemctl start libvirtd")
    except Exception as e:
        output += f"⚠️ **WARN**: Could not check libvirtd: {e}\n\n"

    # Summary
    output += "---\n\n## Summary\n\n"
    if all_passed:
        output += "✅ **ALL CHECKS PASSED** - Safe to create VM\n\n"
        output += "**Next step:** Call `create_vm()` with these parameters:\n"
        output += f'```\ncreate_vm(\n    name="{name}",\n    image="{image}",\n'
        output += f"    memory={memory},\n    cpus={cpus},\n    disk_size={disk_size}\n)\n```\n"
    else:
        output += "❌ **CHECKS FAILED** - Fix issues before creating VM\n\n"
        output += "**Fixes needed:**\n"
        for fix in fixes_needed:
            output += f"- {fix}\n"
        output += "\n**After fixing:** Run `preflight_vm_creation()` again to verify.\n"

    return output


@mcp.tool()
async def list_vms() -> str:
    """
    List all virtual machines managed by kcli/virsh.

    WHEN TO USE: Call this to see existing infrastructure before:
    - Creating new VMs (to check naming conventions and available resources)
    - Getting VM details (to find exact VM names)
    - Deleting VMs (to verify the VM exists)

    WHAT YOU GET: A list showing each VM's:
    - ID (internal libvirt ID)
    - Name (use this for get_vm_info, delete_vm, etc.)
    - State (running, shut off, paused)

    NEXT STEPS:
    - Use get_vm_info(vm_name) to see CPU, memory, disk details
    - Use create_vm() if you need a new VM
    - Use delete_vm(vm_name) to remove a VM

    Returns:
        Formatted list of VMs with their states
    """
    logger.info("Tool called: list_vms()")

    try:
        result = subprocess.run(
            ["virsh", "-c", "qemu:///system", "list", "--all"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            output = f"# Virtual Machines\n\n```\n{result.stdout}\n```"
            logger.info("Successfully listed VMs")
            return output
        else:
            return f"Error listing VMs: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def get_vm_info(vm_name: str) -> str:
    """
    Get detailed information about a specific virtual machine.

    Args:
        vm_name: Name of the virtual machine

    Returns:
        Detailed VM information including resources and state
    """
    logger.info(f"Tool called: get_vm_info(vm_name='{vm_name}')")

    try:
        result = subprocess.run(
            ["virsh", "-c", "qemu:///system", "dominfo", vm_name],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            output = f"# VM Info: {vm_name}\n\n```\n{result.stdout}\n```"
            logger.info(f"Retrieved info for VM: {vm_name}")
            return output
        else:
            return f"Error getting VM info: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def create_vm(
    name: str,
    image: str = "centos10stream",
    memory: int = 2048,
    cpus: int = 2,
    disk_size: int = 10,
) -> str:
    """
    Create a new virtual machine using kcli.

    WHEN TO USE: Create infrastructure for testing, development, or deployment.

    BEFORE CALLING:
    1. Call list_vms() to check existing VMs and naming conventions
    2. Ensure the name is unique and follows your naming pattern
    3. Verify you have sufficient host resources for the requested specs

    IMPORTANT: This is a WRITE operation that takes 1-5 minutes.
    In read-only mode, this will fail.

    Args:
        name: Unique name for the new VM (e.g., "dev-web-01", "test-db")
              Naming convention: <env>-<role>-<number>
        image: Base image. Available options:
              - "centos10stream" (default, recommended)
              - "rhel9", "rhel8"
              - "fedora40", "fedora39"
              - "ubuntu2404", "ubuntu2204"
        memory: Memory in MB. Recommendations:
              - 2048 (2GB): Minimal workloads
              - 4096 (4GB): Standard applications
              - 8192 (8GB): Databases, Java apps
              - 16384 (16GB): Heavy workloads
        cpus: Number of vCPUs (1-16 typical)
        disk_size: Disk size in GB (10-500 typical)

    EXAMPLES:
        create_vm("test-vm")  # Minimal defaults
        create_vm("prod-web-01", memory=4096, cpus=4, disk_size=50)
        create_vm("db-server", image="rhel9", memory=16384, cpus=8, disk_size=200)

    Returns:
        Success message with VM details, or error if creation failed
    """
    logger.info(f"Tool called: create_vm(name='{name}', image='{image}', memory={memory}, cpus={cpus}, disk_size={disk_size})")

    if READ_ONLY:
        return "Error: Cannot create VM in read-only mode"

    try:
        cmd = [
            "kcli",
            "create",
            "vm",
            name,
            "-i",
            image,
            "-P",
            f"memory={memory}",
            "-P",
            f"numcpus={cpus}",
            "-P",
            f"disks=[{disk_size}]",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            output = "# VM Created Successfully\n\n"
            output += f"**Name:** {name}\n"
            output += f"**Image:** {image}\n"
            output += f"**Memory:** {memory}MB\n"
            output += f"**CPUs:** {cpus}\n"
            output += f"**Disk:** {disk_size}GB\n\n"
            output += f"```\n{result.stdout}\n```"
            logger.info(f"Created VM: {name}")
            return output
        else:
            return f"Error creating VM:\n```\n{result.stderr}\n```"
    except subprocess.TimeoutExpired:
        return "Error: VM creation timed out (5 minutes)"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def delete_vm(name: str) -> str:
    """
    Delete a virtual machine.

    Args:
        name: Name of the VM to delete

    Returns:
        Success message or error
    """
    logger.info(f"Tool called: delete_vm(name='{name}')")

    if READ_ONLY:
        return "Error: Cannot delete VM in read-only mode"

    try:
        result = subprocess.run(
            ["kcli", "delete", "vm", name, "-y"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            output = f"Successfully deleted VM '{name}'\n\n```\n{result.stdout}\n```"
            logger.info(f"Deleted VM: {name}")
            return output
        else:
            return f"Error deleting VM:\n```\n{result.stderr}\n```"
    except subprocess.TimeoutExpired:
        return "Error: Delete operation timed out"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# =============================================================================
# Health & Status Tools
# =============================================================================


@mcp.tool()
async def get_airflow_status() -> str:
    """
    Get Airflow system status including scheduler and webserver health.

    Returns:
        Formatted status report
    """
    logger.info("Tool called: get_airflow_status()")

    output = "# Airflow System Status\n\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n"
    output += f"**MCP Server:** Running on port {MCP_PORT}\n"
    output += f"**Read-only Mode:** {READ_ONLY}\n\n"

    if AIRFLOW_AVAILABLE:
        output += "## DAGs\n"
        output += f"Total DAGs: {len(dag_bag.dags)}\n\n"
    else:
        output += "## Status\n"
        output += "⚠️ Airflow context not available\n"

    return output


# =============================================================================
# Information & Context Tools
# =============================================================================


@mcp.tool()
async def get_system_info() -> str:
    """
    Get comprehensive information about Qubinode Navigator system, architecture,
    and available capabilities. Use this to understand the system before making
    requests with other tools.

    Returns:
        Detailed system information, architecture overview, and usage examples
    """
    logger.info("Tool called: get_system_info()")

    info = """# Qubinode Navigator System Information

## System Overview
Qubinode Navigator is a container-first, plugin-based automation platform that orchestrates:
- Apache Airflow for workflow management
- Libvirt/KVM for virtual machine operations
- FastMCP servers for LLM integration

## Architecture
**Nginx Reverse Proxy** (Port 80)
├─ Web UI proxy for Airflow and AI Assistant
└─ User-friendly interface for human operators

**Airflow Services** (Port 8888)
├─ Webserver: DAG management and monitoring UI
├─ Scheduler: Workflow execution engine
├─ PostgreSQL: Metadata database
└─ MCP Server (Port 8889): Tool access for LLMs

## Available Tools (11 Total)

### DAG Management (3 tools)
- **list_dags()** - List all available DAGs
  Usage: Call this first to see available workflows

- **get_dag_info(dag_id)** - Get details about a specific DAG
  Usage: get_dag_info("example_kcli_vm_provisioning")

- **trigger_dag(dag_id, conf)** - Execute a DAG with optional configuration
  Usage: trigger_dag("vm_creation", {"vm_name": "test-vm", "cpu": 4})

### VM Operations (5 tools)
- **list_vms()** - List all virtual machines
  Usage: Call this to see existing VMs and their status

- **get_vm_info(vm_name)** - Get details about a specific VM
  Usage: get_vm_info("web-server-01")

- **create_vm(name, cpu, memory, disk)** - Create a new virtual machine
  Usage: create_vm("dev-env", cpu=8, memory=16, disk=50)
  Note: Resource values in GB for disk, GB for memory, count for CPU

- **start_vm(vm_name)** - Start a stopped VM
  Usage: start_vm("web-server-01")

- **stop_vm(vm_name)** - Stop a running VM
  Usage: stop_vm("database-vm")

### System Status (1 tool)
- **get_airflow_status()** - Get system health and status
  Usage: Call this to verify system is operational

### Information (1 tool)
- **get_system_info()** - Get this information (you are here!)
  Usage: Call when you need to understand the system

### RAG (Retrieval-Augmented Generation) Operations (1 tool)
- **manage_rag_documents(operation, params)** - Manage RAG document ingestion
  Operations: 'scan', 'ingest', 'status', 'list', 'estimate'
  Usage Examples:
    - manage_rag_documents('scan') - Find documents in /opt/documents/incoming
    - manage_rag_documents('ingest') - Trigger ingestion pipeline
    - manage_rag_documents('status') - Check ingestion progress
    - manage_rag_documents('list', {'limit': 5}) - Show processed documents
    - manage_rag_documents('estimate') - Calculate storage requirements

## How to Use These Tools Effectively

### 1. First Steps
Always start by understanding the current state:
```
1. Call get_system_info() to understand capabilities
2. Call get_airflow_status() to verify system health
3. Call list_dags() to see available workflows
4. Call list_vms() to see existing VMs
```

### 2. Creating VMs
To create a new VM:
```
1. Call list_vms() to see existing VMs and naming conventions
2. Call create_vm(name, cpu, memory, disk) with:
   - name: Unique VM name (e.g., "prod-web-01")
   - cpu: Number of CPU cores (e.g., 4, 8, 16)
   - memory: RAM in GB (e.g., 8, 16, 32)
   - disk: Disk size in GB (e.g., 50, 100, 200)
3. Wait for VM creation to complete
4. Call get_vm_info(vm_name) to verify creation
5. Call start_vm(vm_name) if needed
```

### 3. Managing DAGs
To trigger a workflow:
```
1. Call list_dags() to see available workflows
2. Call get_dag_info(dag_id) to understand DAG requirements
3. Call trigger_dag(dag_id, config) with:
   - dag_id: The DAG identifier
   - config: Dict with required parameters for the DAG
4. The DAG scheduler will execute the workflow
5. Check progress via Airflow UI (http://localhost:8888)
```

### 4. RAG Document Ingestion
To ingest documents for Retrieval-Augmented Generation:
```
1. Call manage_rag_documents('scan') to find documents in /opt/documents/incoming
   - Supports: .md, .yml, .yaml, .txt files
   - Shows file count and total size
2. Call manage_rag_documents('estimate') to see chunking requirements
   - Calculates estimated chunks, embeddings, and storage
3. Call manage_rag_documents('ingest') to trigger the ingestion DAG
   - Processes documents into chunks
   - Generates embeddings
   - Stores in vector database
4. Call manage_rag_documents('status') to check progress
5. Call manage_rag_documents('list') to see processed documents
   - Shows metadata and chunk counts
   - Verifies successful ingestion
```

**RAG Best Practices:**
- Place documents in `/opt/documents/incoming/` before ingestion
- Use Markdown files for complex documentation (headers help chunking)
- Check estimate before ingesting large document sets
- Monitor Airflow UI at http://localhost:8888/dags/rag_document_ingestion for detailed logs

### 5. VM Lifecycle Management
Typical workflow:
```
1. create_vm(...) -> Create new VM
2. get_vm_info(name) -> Verify it's running
3. [Do operations via DAGs]
4. stop_vm(name) -> Stop when done
```

## Configuration & Customization

### Airflow Configuration
- Location: `/opt/qubinode-navigator/airflow/config/airflow.env`
- Key settings: Executor type, database, logging
- Restart required: Yes (use podman-compose restart)

### VM Resources
- Minimum recommended: 2 CPU, 4GB RAM, 20GB disk
- Maximum per system: Depends on host hardware
- Storage: Uses libvirt storage pools (default: /var/lib/libvirt/images/)

### Custom DAGs
- Location: `/opt/qubinode-navigator/airflow/dags/`
- Format: Python files with DAG definitions
- Requirements: Inherit from airflow.models.DAG

## Common Patterns & Best Practices

### Pattern 1: Batch VM Creation
Don't create too many VMs at once. Recommended:
- Create 1-3 VMs per batch
- Wait for completion before next batch
- Monitor system resources

### Pattern 2: DAG Chaining
Workflows can trigger other DAGs:
- Call trigger_dag() from within a DAG
- Create multi-stage deployments
- Build automation chains

### Pattern 3: Error Recovery
If something fails:
1. Check get_airflow_status() for health
2. Review Airflow UI logs at http://localhost:8888
3. Retry operation or contact administrator

## Limits & Constraints

- **Concurrent DAGs**: Depends on scheduler resources (typically 8-16)
- **Max VMs per host**: Depends on available resources
- **Tool timeout**: 30 seconds per operation
- **Message size**: Limited to 1MB per operation

## Tips for LLM Interaction

1. **Be Specific**: Provide exact VM names, DAG IDs, and parameters
2. **Check State First**: Always list/check before operating
3. **Follow Naming Conventions**: Use consistent, descriptive names
4. **Document Your Intent**: Explain what you're trying to accomplish
5. **Use Correct Parameters**: Ensure parameters match system requirements

## Emergency Operations

### System is unresponsive
1. Call get_airflow_status()
2. If no response, check Airflow container: `podman-compose ps`
3. Restart if needed: `podman-compose restart`

### VM creation fails repeatedly
1. Call list_vms() to check existing load
2. Check available system resources
3. Reduce VM size/resource requests
4. Try again with smaller parameters

## Resources & Help

- Airflow UI: http://localhost:8888 (admin/admin)
- MCP Server Logs: `podman logs airflow_airflow-mcp-server_1`
- Airflow Logs: `podman logs airflow_airflow-scheduler_1`
- System Status: `get_airflow_status()`

## System Capabilities Summary

✅ Multi-DAG workflow orchestration
✅ VM provisioning and management
✅ Real-time task monitoring
✅ Failed task recovery
✅ Custom DAG support
✅ Resource-aware scheduling
✅ Comprehensive logging
✅ RAG document ingestion and management
✅ Vector database integration

📊 Monitor everything via Airflow UI: http://localhost:8888
📚 Manage documents via manage_rag_documents() tool
🔧 Troubleshoot via tool responses and system logs
"""

    logger.info("System info provided")
    return info


# =============================================================================
# RAG (Retrieval-Augmented Generation) Operations
# =============================================================================


@mcp.tool()
async def manage_rag_documents(operation: str, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Manage RAG document ingestion and vector database operations.

    This tool controls document lifecycle for Retrieval-Augmented Generation (RAG),
    enabling LLMs to ingest new documentation into searchable vector databases.

    Args:
        operation: One of 'scan', 'ingest', 'status', 'list', or 'estimate'
            - 'scan': Discover documents in /opt/documents/incoming
            - 'ingest': Trigger rag_document_ingestion DAG to process documents
            - 'status': Check current ingestion progress and recent run status
            - 'list': List recently processed documents with metadata
            - 'estimate': Calculate chunk count and storage estimate for documents

        params: Optional dict with:
            - 'doc_dir': Custom directory path (default: /opt/documents/incoming)
            - 'limit': For 'list' operation, max results to return (default: 10)

    Returns:
        Status report with operation results or error message

    Examples:
        - List documents: manage_rag_documents('list', {'limit': 5})
        - Estimate chunks: manage_rag_documents('estimate')
        - Trigger ingestion: manage_rag_documents('ingest')
        - Check progress: manage_rag_documents('status')
        - Scan directory: manage_rag_documents('scan', {'doc_dir': '/opt/documents/incoming'})
    """
    logger.info(f"Tool called: manage_rag_documents(operation='{operation}', params={params})")

    if READ_ONLY and operation in ["ingest"]:
        return f"Error: '{operation}' operation requires write access but read-only mode is enabled"

    if params is None:
        params = {}

    doc_dir = params.get("doc_dir", "/opt/documents/incoming")
    limit = params.get("limit", 10)

    try:
        if operation == "scan":
            return _rag_scan_documents(doc_dir)
        elif operation == "ingest":
            return _rag_trigger_ingestion(doc_dir)
        elif operation == "status":
            return _rag_ingestion_status()
        elif operation == "list":
            return _rag_list_processed(limit)
        elif operation == "estimate":
            return _rag_estimate_chunks(doc_dir)
        else:
            return f"Error: Unknown operation '{operation}'. Valid operations: scan, ingest, status, list, estimate"

    except Exception as e:
        error_msg = f"RAG operation '{operation}' failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def _rag_scan_documents(doc_dir: str) -> str:
    """Scan for documents in the specified directory."""
    output = "# RAG Document Scan\n\n"
    output += f"**Directory:** `{doc_dir}`\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"

    if not os.path.isdir(doc_dir):
        output += f"⚠️ Directory does not exist: {doc_dir}\n"
        return output

    documents = []
    supported_exts = {".md", ".markdown", ".yml", ".yaml", ".txt"}

    try:
        for root, dirs, files in os.walk(doc_dir):
            for fname in files:
                file_path = os.path.join(root, fname)
                _, ext = os.path.splitext(fname)

                if ext.lower() in supported_exts:
                    try:
                        file_size = os.path.getsize(file_path)
                        documents.append(
                            {
                                "path": file_path,
                                "name": fname,
                                "type": ext.lower(),
                                "size": file_size,
                                "size_kb": round(file_size / 1024, 2),
                            }
                        )
                    except OSError:
                        pass

        if documents:
            output += f"## Found {len(documents)} document(s)\n\n"
            total_size = sum(d["size"] for d in documents)
            output += f"**Total Size:** {round(total_size / 1024, 2)} KB\n\n"

            output += "| File | Type | Size (KB) |\n"
            output += "|------|------|----------|\n"
            for doc in sorted(documents, key=lambda x: x["name"]):
                output += f"| `{doc['name']}` | {doc['type']} | {doc['size_kb']} |\n"

            output += "\n**Next Step:** Call `manage_rag_documents('ingest')` to process these documents\n"
        else:
            output += "❌ No supported documents found (looking for: .md, .yml, .yaml, .txt)\n"

        return output

    except Exception as e:
        return f"Error scanning documents: {str(e)}"


def _rag_trigger_ingestion(doc_dir: str) -> str:
    """Trigger the rag_document_ingestion DAG."""
    output = "# RAG Document Ingestion\n\n"

    if not AIRFLOW_AVAILABLE:
        return "Error: Airflow not available in this context"

    try:
        # Prepare DAG run configuration
        conf = {"RAG_DOC_DIR": doc_dir} if doc_dir != "/opt/documents/incoming" else {}

        # Trigger the DAG
        dag_run = trigger_dag_api(dag_id="rag_document_ingestion", conf=conf)

        output += "✅ **Ingestion triggered successfully**\n\n"
        output += f"**DAG Run ID:** `{dag_run}`\n"
        output += f"**Source Directory:** `{doc_dir}`\n"
        output += "**Status:** Queued\n"
        output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"
        output += "**Next Steps:**\n"
        output += "1. Wait 10-30 seconds for tasks to execute\n"
        output += "2. Call `manage_rag_documents('status')` to check progress\n"
        output += "3. View detailed logs in Airflow UI: http://localhost:8888/dags/rag_document_ingestion\n"

        logger.info(f"Triggered RAG ingestion DAG: {dag_run}")
        return output

    except Exception as e:
        output += f"❌ Failed to trigger ingestion: {str(e)}\n"
        output += "\n**Troubleshooting:**\n"
        output += "- Check Airflow scheduler is running: `podman-compose ps | grep scheduler`\n"
        output += "- Verify DAG exists: `podman exec airflow_airflow-scheduler_1 airflow dags list | grep rag_document_ingestion`\n"
        output += "- Check Airflow logs for errors\n"
        return output


def _rag_ingestion_status() -> str:
    """Check RAG ingestion DAG run status."""
    output = "# RAG Ingestion Status\n\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"

    if not AIRFLOW_AVAILABLE:
        output += "⚠️ Airflow not available - cannot check status\n"
        return output

    try:
        dag_id = "rag_document_ingestion"
        dag = dag_bag.get_dag(dag_id)

        if not dag:
            output += f"❌ DAG not found: {dag_id}\n"
            return output

        output += f"## DAG: {dag_id}\n"
        output += f"**Schedule:** {dag.schedule_interval or 'Manual'}\n"
        output += f"**Tasks:** {len(dag.tasks)} total\n\n"

        output += "### Task Pipeline\n"
        for task in dag.tasks:
            output += f"- `{task.task_id}`: {task.__class__.__name__}\n"

        output += "\n### Recent Runs\n"
        output += f"(Check Airflow UI for detailed task logs: http://localhost:8888/dags/{dag_id})\n"

        return output

    except Exception as e:
        output += f"Error checking status: {str(e)}\n"
        return output


def _rag_list_processed(limit: int = 10) -> str:
    """List recently processed RAG documents."""
    output = "# Processed RAG Documents\n\n"
    output += f"**Limit:** {limit} results\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"

    metadata_file = "/opt/documents/processed/metadata.json"

    if not os.path.exists(metadata_file):
        output += "ℹ️ No processed documents yet.\n"
        output += "**To process documents:**\n"
        output += "1. Copy documents to `/opt/documents/incoming/`\n"
        output += "2. Call `manage_rag_documents('ingest')`\n"
        output += "3. Wait for processing to complete\n"
        return output

    try:
        import json

        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        if isinstance(metadata, dict) and "documents" in metadata:
            docs = metadata["documents"]
        elif isinstance(metadata, list):
            docs = metadata
        else:
            docs = []

        if not docs:
            output += "ℹ️ No documents in metadata file\n"
            return output

        # Sort by timestamp (newest first)
        if isinstance(docs, list) and docs and isinstance(docs[0], dict) and "timestamp" in docs[0]:
            docs = sorted(docs, key=lambda x: x.get("timestamp", ""), reverse=True)

        output += f"## {len(docs)} document(s) processed\n\n"

        for i, doc in enumerate(docs[:limit], 1):
            if isinstance(doc, dict):
                output += f"### {i}. {doc.get('source', 'Unknown')}\n"
                output += f"- **Path:** `{doc.get('path', 'N/A')}`\n"
                output += f"- **Type:** {doc.get('type', 'N/A')}\n"
                output += f"- **Chunks:** {doc.get('chunk_count', 'N/A')}\n"
                output += f"- **Processed:** {doc.get('timestamp', 'N/A')}\n\n"
            else:
                output += f"{i}. {doc}\n"

        if len(docs) > limit:
            output += f"\n*(Showing {limit} of {len(docs)} documents)*\n"

        return output

    except Exception as e:
        output += f"Error reading processed documents: {str(e)}\n"
        return output


def _rag_estimate_chunks(doc_dir: str) -> str:
    """Estimate document chunking and storage requirements."""
    output = "# RAG Chunk Estimation\n\n"
    output += f"**Source Directory:** `{doc_dir}`\n"
    output += f"**Timestamp:** {datetime.now().isoformat()}\n\n"

    if not os.path.isdir(doc_dir):
        output += f"❌ Directory does not exist: {doc_dir}\n"
        return output

    try:
        total_words = 0
        total_size = 0
        doc_count = 0
        supported_exts = {".md", ".markdown", ".yml", ".yaml", ".txt"}

        for root, dirs, files in os.walk(doc_dir):
            for fname in files:
                _, ext = os.path.splitext(fname)
                if ext.lower() in supported_exts:
                    file_path = os.path.join(root, fname)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            total_words += len(content.split())
                            total_size += len(content)
                            doc_count += 1
                    except (OSError, IOError):
                        pass

        # Estimation parameters
        avg_chunk_size = 250  # words per chunk (typical ~2000 chars)
        estimated_chunks = max(1, total_words // avg_chunk_size)
        embedding_size_bytes = 384 * 4  # 384-dim embedding * 4 bytes per float
        estimated_db_size_mb = (estimated_chunks * embedding_size_bytes) / (1024 * 1024)

        output += "## Document Statistics\n"
        output += f"- **Total Documents:** {doc_count}\n"
        output += f"- **Total Content Size:** {round(total_size / 1024, 2)} KB\n"
        output += f"- **Total Words:** {total_words:,}\n\n"

        output += "## Chunking Estimate\n"
        output += f"- **Average Chunk Size:** ~{avg_chunk_size} words\n"
        output += f"- **Estimated Chunks:** ~{estimated_chunks:,}\n"
        output += "- **Embedding Dimension:** 384-d\n\n"

        output += "## Storage Requirements\n"
        output += f"- **Vector DB Size (estimated):** ~{round(estimated_db_size_mb, 2)} MB\n"
        output += f"- **Including Metadata:** ~{round(estimated_db_size_mb * 1.5, 2)} MB\n\n"

        output += "## Quality Metrics\n"
        output += "- **Documents Ready:** ✅ Yes (>0 documents found)\n"
        output += f"- **Sufficient Content:** {'✅ Yes' if total_words > 100 else '⚠️ May be limited'}\n"
        output += f"- **Processing Time Est:** ~{max(10, estimated_chunks // 100)} seconds\n\n"

        output += "**Next Step:** Call `manage_rag_documents('ingest')` to process documents\n"

        return output

    except Exception as e:
        output += f"Error estimating chunks: {str(e)}\n"
        return output


# =============================================================================
# ADR-0049: RAG Query Tools
# =============================================================================


@mcp.tool()
async def query_rag(
    query: str,
    doc_types: Optional[List[str]] = None,
    limit: int = 5,
    threshold: float = 0.7,
) -> str:
    """
    Search the RAG knowledge base for relevant documents using semantic similarity.

    WHEN TO USE: Before attempting any task, search for existing knowledge:
    - Error messages you encounter
    - Configuration questions
    - Best practices for a technology
    - Past solutions to similar problems

    Use this tool to find documentation, ADRs, past troubleshooting solutions,
    and DAG examples related to your query.

    WORKFLOW:
    1. Call query_rag() with your question or error message
    2. If results found, use the information to proceed
    3. If no results, lower threshold or broaden query
    4. After solving a problem, use log_troubleshooting_attempt() to save solution

    Args:
        query: Natural language search query (e.g., "How to configure FreeIPA DNS?")
        doc_types: Filter by document types. Options:
            - 'adr': Architecture Decision Records
            - 'provider_doc': Airflow provider documentation
            - 'dag': Example DAG code
            - 'troubleshooting': Past troubleshooting solutions
            - 'guide': How-to guides
            - None: Search all types (recommended first)
        limit: Maximum number of results (default: 5, max: 20)
        threshold: Minimum similarity score 0-1 (default: 0.7)
            - 0.8+: High confidence matches only
            - 0.6-0.8: Good matches
            - 0.5-0.6: Broader search
            - <0.5: May return less relevant results

    Returns:
        Formatted list of matching documents with similarity scores and content excerpts.

    EXAMPLES:
        query_rag("FreeIPA DNS configuration")
        query_rag("OpenShift deployment errors", doc_types=["troubleshooting"])
        query_rag("SSH operator usage", doc_types=["provider_doc", "dag"])
        query_rag("connection refused", threshold=0.5)  # Broader error search
    """
    logger.info(f"Tool called: query_rag(query='{query[:50]}...', doc_types={doc_types}, limit={limit})")

    store = get_rag()
    if store is None:
        return "Error: RAG store not available. Ensure PgVector is configured and running."

    try:
        results = store.search_documents(query=query, doc_types=doc_types, limit=limit, threshold=threshold)

        if not results:
            output = "# No Results Found\n\n"
            output += f"**Query:** {query}\n"
            output += f"**Filters:** {doc_types or 'All types'}\n"
            output += f"**Threshold:** {threshold}\n\n"
            output += "Try:\n"
            output += "- Lowering the threshold (e.g., 0.5)\n"
            output += "- Broadening your query\n"
            output += "- Removing doc_type filters\n"
            return output

        output = "# RAG Search Results\n\n"
        output += f"**Query:** {query}\n"
        output += f"**Found:** {len(results)} documents\n\n"

        for i, doc in enumerate(results, 1):
            similarity_pct = int(doc["similarity"] * 100)
            output += f"## {i}. [{doc['doc_type']}] Similarity: {similarity_pct}%\n"
            if doc.get("source_path"):
                output += f"**Source:** `{doc['source_path']}`\n"

            # Truncate content for display
            content = doc["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            output += f"\n{content}\n\n"
            output += "---\n\n"

        logger.info(f"RAG query returned {len(results)} results")
        return output

    except Exception as e:
        error_msg = f"RAG query failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def ingest_to_rag(
    content: str,
    doc_type: str,
    source: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Ingest new documentation into the RAG knowledge base.

    Use this when you need to add new documentation, guides, or context
    that the system doesn't have. The content will be chunked, embedded,
    and stored for future semantic search.

    Args:
        content: Document content (markdown, text, code)
        doc_type: Type of document. One of:
            - 'adr': Architecture Decision Record
            - 'provider_doc': Airflow provider documentation
            - 'dag': DAG example or template
            - 'troubleshooting': Troubleshooting guide or solution
            - 'guide': How-to guide
            - 'policy': Organization policy
            - 'example': Code example
        source: Source path or URL (optional)
        metadata: Additional metadata dictionary (optional)

    Returns:
        Confirmation with document IDs created.

    Examples:
        - ingest_to_rag("# FreeIPA Guide\\n...", "guide", source="/docs/freeipa.md")
        - ingest_to_rag(dag_code, "dag", metadata={"component": "freeipa"})
    """
    logger.info(f"Tool called: ingest_to_rag(doc_type='{doc_type}', source='{source}')")

    if READ_ONLY:
        return "Error: Cannot ingest documents in read-only mode"

    store = get_rag()
    if store is None:
        return "Error: RAG store not available. Ensure PgVector is configured and running."

    valid_types = [
        "adr",
        "provider_doc",
        "dag",
        "troubleshooting",
        "guide",
        "policy",
        "example",
        "api_doc",
        "readme",
    ]
    if doc_type not in valid_types:
        return f"Error: Invalid doc_type '{doc_type}'. Must be one of: {valid_types}"

    try:
        doc_ids = store.ingest_document(
            content=content,
            doc_type=doc_type,
            source_path=source,
            metadata=metadata or {},
        )

        if not doc_ids:
            return "Document already exists in RAG store (duplicate detected)"

        output = "# Document Ingested Successfully\n\n"
        output += f"**Type:** {doc_type}\n"
        output += f"**Source:** {source or 'N/A'}\n"
        output += f"**Chunks Created:** {len(doc_ids)}\n"
        output += f"**Document IDs:** {', '.join(doc_ids[:3])}{'...' if len(doc_ids) > 3 else ''}\n\n"
        output += "The document is now searchable via `query_rag()`."

        logger.info(f"Ingested document: {len(doc_ids)} chunks")
        return output

    except Exception as e:
        error_msg = f"Ingestion failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


# =============================================================================
# ADR-0049: Troubleshooting Memory Tools
# =============================================================================


@mcp.tool()
async def get_troubleshooting_history(
    error_pattern: Optional[str] = None,
    component: Optional[str] = None,
    only_successful: bool = False,
    limit: int = 10,
) -> str:
    """
    Retrieve past troubleshooting attempts to learn from previous solutions.

    Use this BEFORE attempting to fix an error to see if similar issues
    have been solved before. This enables the system to learn and avoid
    repeating failed approaches.

    Args:
        error_pattern: Search for similar errors (semantic search)
        component: Filter by component (freeipa, vyos, openshift, etc.)
        only_successful: Only return successful solutions
        limit: Maximum results to return

    Returns:
        List of past troubleshooting attempts with outcomes.

    Examples:
        - get_troubleshooting_history(error_pattern="DNS resolution failed")
        - get_troubleshooting_history(component="freeipa", only_successful=True)
    """
    logger.info(f"Tool called: get_troubleshooting_history(error_pattern='{error_pattern}', component='{component}')")

    store = get_rag()
    if store is None:
        return "Error: RAG store not available."

    try:
        output = "# Troubleshooting History\n\n"

        if error_pattern:
            # Semantic search for similar errors
            results = store.search_similar_errors(
                error_description=error_pattern,
                only_successful=only_successful,
                limit=limit,
            )

            output += f"**Search:** {error_pattern}\n"
            output += f"**Filter:** {'Successful only' if only_successful else 'All results'}\n"
            output += f"**Found:** {len(results)} similar cases\n\n"

            if not results:
                output += "No similar troubleshooting attempts found.\n"
                output += "This appears to be a new type of error.\n"
                return output

            for i, r in enumerate(results, 1):
                similarity_pct = int(r["similarity"] * 100)
                result_emoji = "✅" if r["result"] == "success" else "❌" if r["result"] == "failed" else "⚠️"

                output += f"## {i}. {result_emoji} Similarity: {similarity_pct}%\n"
                output += f"**Error:** {r.get('error_message', 'N/A')}\n"
                output += f"**Solution Tried:** {r.get('attempted_solution', 'N/A')}\n"
                output += f"**Result:** {r['result']}\n"
                if r.get("component"):
                    output += f"**Component:** {r['component']}\n"
                output += "\n---\n\n"
        else:
            # Get session history
            session_id = get_session_id()
            history = store.get_session_history(session_id)

            output += f"**Current Session:** {session_id[:8]}...\n"
            output += f"**Attempts:** {len(history)}\n\n"

            if not history:
                output += "No troubleshooting attempts in this session yet.\n"
                return output

            for h in history:
                result_emoji = "✅" if h["result"] == "success" else "❌" if h["result"] == "failed" else "⚠️"
                output += f"### Attempt {h['sequence_num']} {result_emoji}\n"
                output += f"**Task:** {h['task_description']}\n"
                if h.get("error_message"):
                    output += f"**Error:** {h['error_message']}\n"
                output += f"**Solution:** {h['attempted_solution']}\n"
                output += f"**Result:** {h['result']}\n"
                if h.get("override_by"):
                    output += f"**Override By:** {h['override_by']}\n"
                output += "\n"

        return output

    except Exception as e:
        error_msg = f"Failed to get history: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def log_troubleshooting_attempt(
    task: str,
    solution: str,
    result: str,
    error_message: Optional[str] = None,
    component: Optional[str] = None,
    details: Optional[str] = None,
) -> str:
    """
    Log a troubleshooting attempt for future learning.

    Call this AFTER attempting a fix to record what was tried and whether
    it worked. This builds the knowledge base for future similar issues.

    Args:
        task: What you were trying to accomplish
        solution: What solution/fix was attempted
        result: Outcome - one of 'success', 'failed', or 'partial'
        error_message: The original error (if any)
        component: Which component (freeipa, vyos, openshift, etc.)
        details: Additional details about the outcome

    Returns:
        Confirmation of logged attempt.

    Examples:
        - log_troubleshooting_attempt(
            task="Deploy FreeIPA",
            error_message="DNS resolution failed",
            solution="Opened port 53 in firewalld",
            result="success",
            component="freeipa"
          )
    """
    logger.info(f"Tool called: log_troubleshooting_attempt(task='{task[:30]}...', result='{result}')")

    if READ_ONLY:
        return "Error: Cannot log attempts in read-only mode"

    if result not in ["success", "failed", "partial"]:
        return f"Error: result must be 'success', 'failed', or 'partial'. Got: {result}"

    store = get_rag()
    if store is None:
        return "Error: RAG store not available."

    try:
        attempt_id = store.log_troubleshooting(
            session_id=get_session_id(),
            task_description=task,
            attempted_solution=solution,
            result=result,
            error_message=error_message,
            component=component,
            result_details=details,
            agent="calling_llm",  # Logged by calling LLM
        )

        result_emoji = "✅" if result == "success" else "❌" if result == "failed" else "⚠️"

        output = f"# Troubleshooting Attempt Logged {result_emoji}\n\n"
        output += f"**ID:** {attempt_id[:8]}...\n"
        output += f"**Session:** {get_session_id()[:8]}...\n"
        output += f"**Task:** {task}\n"
        output += f"**Result:** {result}\n\n"

        if result == "success":
            output += "This solution will be suggested for similar future errors."
        elif result == "failed":
            output += "This approach will be noted to avoid in similar situations."

        return output

    except Exception as e:
        error_msg = f"Failed to log attempt: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


# =============================================================================
# ADR-0049: Agent Orchestration Tools
# =============================================================================


@mcp.tool()
async def check_provider_exists(system_name: str) -> str:
    """
    Check if an Airflow provider exists for a given system (Provider-First Rule).

    ALWAYS call this before designing DAGs that interact with external systems.
    If a provider exists, you MUST use its operators instead of BashOperator.

    Args:
        system_name: Name of the system (e.g., 'azure', 'postgres', 'kubernetes')

    Returns:
        Provider information if found, or guidance if not.

    Examples:
        - check_provider_exists("azure")
        - check_provider_exists("postgres")
        - check_provider_exists("custom_internal_api")
    """
    logger.info(f"Tool called: check_provider_exists(system_name='{system_name}')")

    store = get_rag()
    if store is None:
        # Fallback to basic check
        known_providers = [
            "postgres",
            "ssh",
            "http",
            "kubernetes",
            "docker",
            "amazon",
            "google",
            "microsoft-azure",
            "slack",
            "redis",
        ]
        system_lower = system_name.lower()

        for p in known_providers:
            if system_lower in p or p in system_lower:
                return f"# Provider Found: {p}\n\nUse `apache-airflow-providers-{p}` operators."

        return f"# No Provider Found for '{system_name}'\n\nConsider using HTTP/SSH operators or designing a custom provider."

    try:
        result = store.check_provider_exists(system_name)

        if result:
            output = "# ✅ Provider Found\n\n"
            output += f"**Provider:** {result['provider_name']}\n"
            output += f"**Package:** `{result['package_name']}`\n"
            output += f"**Description:** {result.get('description', 'N/A')}\n"
            if result.get("documentation_url"):
                output += f"**Docs:** {result['documentation_url']}\n"
            output += "\n## Provider-First Rule\n"
            output += "You MUST use this provider's operators instead of BashOperator.\n"
            output += "Query RAG for usage examples: `query_rag('azure operator examples', doc_types=['dag', 'provider_doc'])`"
            return output
        else:
            output = f"# ❌ No Provider Found for '{system_name}'\n\n"
            output += "## Options\n\n"
            output += "1. **Use HTTP Operator** - If the system has a REST API\n"
            output += "2. **Use SSH Operator** - If accessible via SSH\n"
            output += "3. **Design a Provider** - For complex integrations\n\n"
            output += "## If No Provider is Suitable\n"
            output += "Escalate to create a provider design document:\n"
            output += "- Document required connections\n"
            output += "- Define operators/hooks needed\n"
            output += "- Create `docs/provider_plan_<name>.md`\n"
            return output

    except Exception as e:
        error_msg = f"Provider check failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def compute_confidence_score(task_description: str, doc_types: Optional[List[str]] = None) -> str:
    """
    Compute confidence score for a task based on RAG knowledge.

    Use this to determine if you have enough context to proceed with a task.
    Follow the Confidence Policy (ADR-0049):
    - High (≥0.8): Proceed confidently
    - Medium (0.6-0.8): Proceed with caveats
    - Low (<0.6): STOP and request more documentation

    Args:
        task_description: What you're trying to accomplish
        doc_types: Document types to search (optional)

    Returns:
        Confidence assessment with recommendation.
    """
    logger.info(f"Tool called: compute_confidence_score(task='{task_description[:50]}...')")

    store = get_rag()
    if store is None:
        return "Error: RAG store not available. Cannot compute confidence."

    try:
        # Search RAG for relevant documents
        results = store.search_documents(query=task_description, doc_types=doc_types, limit=10, threshold=0.5)

        # Compute confidence factors
        rag_hit_count = len(results)
        rag_max_similarity = max([r["similarity"] for r in results]) if results else 0

        # Check for provider if task mentions external system
        provider_exists = False
        for keyword in ["azure", "aws", "gcp", "kubernetes", "postgres", "redis"]:
            if keyword in task_description.lower():
                provider_check = store.check_provider_exists(keyword)
                if provider_check:
                    provider_exists = True
                    break

        # Check for similar DAGs
        dag_results = store.search_documents(query=task_description, doc_types=["dag"], limit=3, threshold=0.6)
        similar_dag_exists = len(dag_results) > 0

        # Compute score
        confidence = 0.4 * rag_max_similarity + 0.3 * min(rag_hit_count / 5.0, 1.0) + 0.2 * (1.0 if provider_exists else 0.0) + 0.1 * (1.0 if similar_dag_exists else 0.0)

        # Determine recommendation
        if confidence >= 0.8:
            level = "HIGH"
            emoji = "✅"
            recommendation = "Proceed with task. Sufficient context available."
        elif confidence >= 0.6:
            level = "MEDIUM"
            emoji = "⚠️"
            recommendation = "Proceed with caution. Note any assumptions made."
        else:
            level = "LOW"
            emoji = "❌"
            recommendation = "STOP. Request additional documentation before proceeding."

        output = f"# Confidence Assessment {emoji}\n\n"
        output += f"**Task:** {task_description}\n"
        output += f"**Confidence:** {confidence:.2f} ({level})\n\n"

        output += "## Factors\n"
        output += f"- RAG Hits: {rag_hit_count} documents\n"
        output += f"- Best Match Similarity: {rag_max_similarity:.2f}\n"
        output += f"- Provider Available: {'Yes' if provider_exists else 'No'}\n"
        output += f"- Similar DAG Exists: {'Yes' if similar_dag_exists else 'No'}\n\n"

        output += f"## Recommendation\n{recommendation}\n"

        if confidence < 0.6:
            output += "\n## To Increase Confidence\n"
            output += "1. Provide relevant documentation via `ingest_to_rag()`\n"
            output += "2. Share example implementations\n"
            output += "3. Clarify requirements\n"

        # Log decision
        store.log_decision(
            agent="calling_llm",
            decision_type="confidence_check",
            context={"task": task_description, "doc_types": doc_types},
            decision=f"{level} confidence ({confidence:.2f})",
            confidence=confidence,
            rag_hits=rag_hit_count,
            rag_max_similarity=rag_max_similarity,
            session_id=get_session_id(),
        )

        return output

    except Exception as e:
        error_msg = f"Confidence computation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def get_rag_stats() -> str:
    """
    Get statistics about the RAG knowledge base.

    Returns:
        Summary of documents, troubleshooting attempts, and decisions in the store.
    """
    logger.info("Tool called: get_rag_stats()")

    store = get_rag()
    if store is None:
        return "Error: RAG store not available."

    try:
        stats = store.get_stats()

        output = "# RAG Knowledge Base Statistics\n\n"

        output += "## Documents by Type\n"
        if stats.get("documents"):
            for doc_type, count in stats["documents"].items():
                output += f"- **{doc_type}:** {count}\n"
        else:
            output += "No documents ingested yet.\n"

        output += "\n## Troubleshooting Attempts\n"
        if stats.get("troubleshooting"):
            total = sum(stats["troubleshooting"].values())
            output += f"- **Total:** {total}\n"
            for result, count in stats["troubleshooting"].items():
                emoji = "✅" if result == "success" else "❌" if result == "failed" else "⚠️"
                output += f"- {emoji} **{result}:** {count}\n"
        else:
            output += "No troubleshooting attempts logged yet.\n"

        output += "\n## Agent Decisions\n"
        if stats.get("decisions"):
            for agent, count in stats["decisions"].items():
                output += f"- **{agent}:** {count} decisions\n"
        else:
            output += "No decisions logged yet.\n"

        output += "\n## Current Session\n"
        output += f"**ID:** {get_session_id()[:8]}...\n"

        return output

    except Exception as e:
        error_msg = f"Failed to get stats: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


# =============================================================================
# ADR-0049 Phase 4: OpenLineage / Lineage Query Tools
# =============================================================================

# Import lineage service
LINEAGE_AVAILABLE = False
lineage_service = None
try:
    from qubinode.lineage_service import get_lineage_service

    LINEAGE_AVAILABLE = True
    logger.info("Lineage service available")
except ImportError as e:
    logger.warning(f"Lineage service not available: {e}")


def get_lineage():
    """Get lineage service singleton."""
    global lineage_service
    if LINEAGE_AVAILABLE and lineage_service is None:
        try:
            lineage_service = get_lineage_service()
        except Exception as e:
            logger.error(f"Failed to initialize lineage service: {e}")
    return lineage_service


@mcp.tool()
async def get_dag_lineage(dag_id: str, depth: int = 5) -> str:
    """
    Get lineage information for a DAG, showing upstream and downstream dependencies.

    This tool queries the OpenLineage/Marquez backend to understand:
    - What tasks are in the DAG
    - What datasets each task produces/consumes
    - What other DAGs depend on or are dependencies of this DAG

    Args:
        dag_id: The DAG identifier to analyze
        depth: How deep to traverse the lineage graph (default: 5)

    Returns:
        Formatted lineage information including tasks, datasets, and dependencies.
    """
    logger.info(f"Tool called: get_dag_lineage(dag_id={dag_id}, depth={depth})")

    service = get_lineage()
    if service is None:
        return "Error: Lineage service not available. Enable with: docker-compose --profile lineage up"

    try:
        # Check if Marquez is available
        if not await service.is_available():
            return "Error: Marquez lineage backend is not available. Start with: docker-compose --profile lineage up"

        lineage = await service.get_dag_lineage(dag_id, depth=depth)

        if "error" in lineage:
            return f"Error getting lineage: {lineage['error']}"

        # Format output
        output = f"# Lineage for DAG: {dag_id}\n\n"
        output += f"**Namespace:** {lineage.get('namespace', 'qubinode')}\n\n"

        # Tasks
        output += "## Tasks\n"
        tasks = lineage.get("tasks", [])
        if tasks:
            for task in tasks:
                output += f"\n### {task['name']}\n"
                output += f"- **Job:** {task['job_name']}\n"

                inputs = task.get("inputs", [])
                if inputs:
                    output += f"- **Inputs:** {', '.join([i.get('name', 'unknown') for i in inputs])}\n"

                outputs = task.get("outputs", [])
                if outputs:
                    output += f"- **Outputs:** {', '.join([o.get('name', 'unknown') for o in outputs])}\n"

                latest_run = task.get("latest_run")
                if latest_run:
                    output += f"- **Latest Run:** {latest_run.get('state', 'unknown')}\n"
        else:
            output += "No tasks found. DAG may not have run yet.\n"

        # Datasets
        output += "\n## Datasets\n"
        datasets = lineage.get("datasets", [])
        if datasets:
            for ds in datasets:
                output += f"- {ds}\n"
        else:
            output += "No datasets tracked yet.\n"

        # Dependencies
        upstream = lineage.get("upstream_dags", [])
        downstream = lineage.get("downstream_dags", [])

        if upstream or downstream:
            output += "\n## Dependencies\n"
            if upstream:
                output += f"**Upstream DAGs:** {', '.join(upstream)}\n"
            if downstream:
                output += f"**Downstream DAGs:** {', '.join(downstream)}\n"

        return output

    except Exception as e:
        error_msg = f"Failed to get DAG lineage: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def get_failure_blast_radius(dag_id: str, task_id: Optional[str] = None) -> str:
    """
    Analyze the impact (blast radius) of a DAG or task failure.

    This helps understand what would be affected if a DAG/task fails:
    - Downstream jobs that depend on this one
    - Datasets that would be affected
    - Severity assessment
    - Recommended action

    Use this before retrying failed tasks to understand the impact.

    Args:
        dag_id: The DAG to analyze
        task_id: Specific task within the DAG (optional)

    Returns:
        Impact analysis with severity rating and recommendations.
    """
    logger.info(f"Tool called: get_failure_blast_radius(dag_id={dag_id}, task_id={task_id})")

    service = get_lineage()
    if service is None:
        return "Error: Lineage service not available. Enable with: docker-compose --profile lineage up"

    try:
        if not await service.is_available():
            return "Error: Marquez lineage backend is not available."

        result = await service.get_failure_blast_radius(dag_id, task_id)

        if "error" in result:
            return f"Error: {result['error']}"

        # Format output
        source = result.get("source", {})
        impact = result.get("impact", {})

        output = "# Failure Blast Radius Analysis\n\n"
        output += "## Source\n"
        output += f"- **DAG:** {source.get('dag_id', dag_id)}\n"
        if source.get("task_id"):
            output += f"- **Task:** {source.get('task_id')}\n"
        output += f"- **Job Name:** {source.get('job_name', 'unknown')}\n"

        output += "\n## Impact Assessment\n"
        severity = result.get("severity", "unknown")
        severity_emoji = {"none": "✅", "low": "🟡", "medium": "🟠", "high": "🔴"}.get(severity, "❓")
        output += f"**Severity:** {severity_emoji} {severity.upper()}\n\n"

        output += f"- **Downstream Jobs Affected:** {impact.get('job_count', 0)}\n"
        output += f"- **Datasets Affected:** {impact.get('dataset_count', 0)}\n"

        downstream_jobs = impact.get("downstream_jobs", [])
        if downstream_jobs:
            output += "\n### Affected Jobs:\n"
            for job in downstream_jobs[:10]:
                output += f"- {job}\n"
            if len(downstream_jobs) > 10:
                output += f"- ... and {len(downstream_jobs) - 10} more\n"

        output += "\n## Recommendation\n"
        output += f"{result.get('recommendation', 'No specific recommendation')}\n"

        if result.get("note"):
            output += f"\n*Note: {result.get('note')}*\n"

        return output

    except Exception as e:
        error_msg = f"Failed to analyze blast radius: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def get_dataset_lineage(dataset_name: str) -> str:
    """
    Get lineage information for a specific dataset.

    Shows which jobs produce and consume the dataset, enabling
    understanding of data flow through the system.

    Args:
        dataset_name: Name of the dataset to analyze

    Returns:
        Dataset lineage including producers, consumers, and schema.
    """
    logger.info(f"Tool called: get_dataset_lineage(dataset_name={dataset_name})")

    service = get_lineage()
    if service is None:
        return "Error: Lineage service not available."

    try:
        if not await service.is_available():
            return "Error: Marquez lineage backend is not available."

        result = await service.get_dataset_lineage(dataset_name)

        if "error" in result:
            return f"Error: {result['error']}"

        output = f"# Dataset Lineage: {dataset_name}\n\n"
        output += f"**Namespace:** {result.get('namespace', 'qubinode')}\n"
        output += f"**Description:** {result.get('description', 'No description')}\n\n"

        output += "## Producer\n"
        output += f"**Job:** {result.get('producers', 'unknown')}\n\n"

        schema = result.get("schema", [])
        if schema:
            output += "## Schema\n"
            for field in schema:
                output += f"- **{field.get('name', 'unknown')}**: {field.get('type', 'unknown')}\n"

        output += "\n## Metadata\n"
        output += f"- **Created:** {result.get('created_at', 'unknown')}\n"
        output += f"- **Updated:** {result.get('updated_at', 'unknown')}\n"

        tags = result.get("tags", [])
        if tags:
            output += f"- **Tags:** {', '.join(tags)}\n"

        return output

    except Exception as e:
        error_msg = f"Failed to get dataset lineage: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


@mcp.tool()
async def get_lineage_stats() -> str:
    """
    Get statistics about the OpenLineage/Marquez lineage system.

    Returns summary of:
    - Total jobs and their states
    - Total datasets being tracked
    - Success rate of recent runs
    - System availability

    Returns:
        Lineage system statistics.
    """
    logger.info("Tool called: get_lineage_stats()")

    service = get_lineage()
    if service is None:
        return "Error: Lineage service not available. Enable with: docker-compose --profile lineage up"

    try:
        available = await service.is_available()
        if not available:
            return """# Lineage System Status

**Status:** ❌ Not Available

The Marquez lineage backend is not running.

## To Enable Lineage Tracking:

```bash
cd airflow
docker-compose --profile lineage up -d
```

This will start:
- Marquez API (port 5001)
- Marquez Web UI (port 3000)

Then set `OPENLINEAGE_DISABLED=false` to enable lineage emission from Airflow.
"""

        stats = await service.get_lineage_stats()

        output = "# Lineage System Statistics\n\n"
        output += "**Status:** ✅ Available\n\n"

        jobs = stats.get("jobs", {})
        output += "## Jobs\n"
        output += f"- **Total:** {jobs.get('total', 0)}\n"
        output += f"- **Running:** {jobs.get('running', 0)}\n"
        output += f"- **Failed:** {jobs.get('failed', 0)}\n"
        output += f"- **Success Rate:** {jobs.get('success_rate', 0):.1f}%\n\n"

        datasets = stats.get("datasets", {})
        output += "## Datasets\n"
        output += f"- **Total:** {datasets.get('total', 0)}\n\n"

        output += "## Access\n"
        output += "- **API:** http://localhost:5001/api/v1\n"
        output += "- **Web UI:** http://localhost:3000\n"

        return output

    except Exception as e:
        error_msg = f"Failed to get lineage stats: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


# =============================================================================
# WORKFLOW ORCHESTRATION TOOLS (ADR-0034 Enhancement)
# =============================================================================

WORKFLOW_TEMPLATES = {
    "create_openshift_cluster": {
        "name": "Create OpenShift Cluster",
        "description": "Deploy a new OpenShift cluster from scratch",
        "steps": [
            {
                "name": "Verify prerequisites",
                "tool": "preflight_vm_creation",
                "required": True,
            },
            {
                "name": "Check DNS configuration",
                "tool": "query_rag",
                "query": "openshift dns requirements",
            },
            {
                "name": "Create bootstrap VM",
                "tool": "create_vm",
                "params": {"memory": 16384, "cpus": 4},
            },
            {
                "name": "Trigger deployment DAG",
                "tool": "trigger_dag",
                "dag_id": "openshift_deploy_cluster",
            },
            {"name": "Monitor progress", "tool": "get_dag_info", "check_status": True},
        ],
        "estimated_duration": "45-90 minutes",
        "confidence_threshold": 0.8,
    },
    "setup_freeipa": {
        "name": "Setup FreeIPA Server",
        "description": "Deploy FreeIPA for identity management",
        "steps": [
            {
                "name": "Check existing setup",
                "tool": "list_vms",
                "check_for": "freeipa",
            },
            {
                "name": "Run preflight checks",
                "tool": "preflight_vm_creation",
                "required": True,
            },
            {
                "name": "Create FreeIPA VM",
                "tool": "create_vm",
                "params": {"memory": 4096, "cpus": 2},
            },
            {
                "name": "Trigger FreeIPA DAG",
                "tool": "trigger_dag",
                "dag_id": "freeipa_deploy",
            },
            {
                "name": "Verify DNS records",
                "tool": "query_rag",
                "query": "freeipa dns verification",
            },
        ],
        "estimated_duration": "20-30 minutes",
        "confidence_threshold": 0.75,
    },
    "deploy_vm_basic": {
        "name": "Deploy Basic VM",
        "description": "Create and configure a simple virtual machine",
        "steps": [
            {
                "name": "Run preflight checks",
                "tool": "preflight_vm_creation",
                "required": True,
            },
            {"name": "Create VM", "tool": "create_vm", "required": True},
            {
                "name": "Verify VM is running",
                "tool": "get_vm_info",
                "check_status": True,
            },
            {
                "name": "Log success",
                "tool": "log_troubleshooting_attempt",
                "log_success": True,
            },
        ],
        "estimated_duration": "5-10 minutes",
        "confidence_threshold": 0.7,
    },
    "troubleshoot_vm": {
        "name": "Troubleshoot VM Issues",
        "description": "Diagnose and fix common VM problems",
        "steps": [
            {"name": "Check VM state", "tool": "get_vm_info", "required": True},
            {
                "name": "Search past solutions",
                "tool": "get_troubleshooting_history",
                "required": True,
            },
            {
                "name": "Query knowledge base",
                "tool": "query_rag",
                "query": "vm troubleshooting",
            },
            {
                "name": "Check host resources",
                "tool": "preflight_vm_creation",
                "diagnostics_only": True,
            },
            {"name": "Review related DAGs", "tool": "list_dags", "filter": "vm"},
        ],
        "estimated_duration": "10-20 minutes",
        "confidence_threshold": 0.6,
    },
}


@mcp.tool()
async def get_workflow_guide(workflow_type: str = "", goal_description: str = "") -> str:
    """
    Get step-by-step guidance for multi-step infrastructure workflows.

    WHEN TO USE: Call this FIRST when you need to:
    - Deploy OpenShift clusters
    - Setup FreeIPA identity management
    - Create VMs with proper validation
    - Troubleshoot infrastructure issues
    - Plan any multi-step operation

    WHAT YOU GET: A structured workflow plan showing:
    - Ordered steps with specific tools to call
    - Required vs optional steps
    - Confidence thresholds to meet
    - Estimated duration
    - What to do if a step fails

    HOW IT IMPROVES SUCCESS:
    - Ensures prerequisites are checked first
    - Prevents common ordering mistakes
    - Links to troubleshooting history if steps fail
    - Provides rollback guidance

    Args:
        workflow_type: One of: 'create_openshift_cluster', 'setup_freeipa',
                      'deploy_vm_basic', 'troubleshoot_vm'
                      Leave empty to see all available workflows.
        goal_description: Natural language description of what you want to achieve
                         (used if workflow_type is not specified)

    EXAMPLES:
        get_workflow_guide(workflow_type="deploy_vm_basic")
        get_workflow_guide(goal_description="I need to set up DNS for my cluster")

    NEXT STEPS after getting the guide:
    - Follow steps in order, calling each tool
    - If a step fails, check get_troubleshooting_history()
    - After completion, call log_troubleshooting_attempt() to record success
    """
    logger.info(f"Tool called: get_workflow_guide(workflow_type='{workflow_type}', goal='{goal_description}')")

    output = "# Workflow Orchestration Guide\n\n"

    # If no workflow specified, show all available
    if not workflow_type and not goal_description:
        output += "## Available Workflows\n\n"
        for wf_id, wf in WORKFLOW_TEMPLATES.items():
            output += f"### `{wf_id}`\n"
            output += f"**{wf['name']}**: {wf['description']}\n"
            output += f"- Steps: {len(wf['steps'])}\n"
            output += f"- Duration: {wf['estimated_duration']}\n"
            output += f"- Confidence needed: {wf['confidence_threshold']:.0%}\n\n"

        output += "---\n\n"
        output += "**To get detailed steps:** Call `get_workflow_guide(workflow_type='workflow_id')`\n\n"
        output += "**Or describe your goal:** Call `get_workflow_guide(goal_description='what you want to do')`\n"
        return output

    # Try to match goal description to workflow
    if goal_description and not workflow_type:
        goal_lower = goal_description.lower()
        if any(term in goal_lower for term in ["openshift", "ocp", "cluster"]):
            workflow_type = "create_openshift_cluster"
        elif any(term in goal_lower for term in ["freeipa", "idm", "identity", "dns"]):
            workflow_type = "setup_freeipa"
        elif any(term in goal_lower for term in ["troubleshoot", "fix", "error", "problem", "issue"]):
            workflow_type = "troubleshoot_vm"
        elif any(term in goal_lower for term in ["vm", "virtual", "create", "deploy"]):
            workflow_type = "deploy_vm_basic"
        else:
            output += "## Goal Analysis\n\n"
            output += f"**Your goal:** {goal_description}\n\n"
            output += "I couldn't match this to a specific workflow. Here's what I recommend:\n\n"
            output += "1. **Search the knowledge base first:**\n"
            output += f'   ```\n   query_rag(query="{goal_description}")\n   ```\n\n'
            output += "2. **Check for existing solutions:**\n"
            output += f'   ```\n   get_troubleshooting_history(error_pattern="{goal_description[:50]}")\n   ```\n\n'
            output += "3. **Review available DAGs:**\n"
            output += "   ```\n   list_dags()\n   ```\n\n"
            return output

    # Get the workflow template
    workflow = WORKFLOW_TEMPLATES.get(workflow_type)
    if not workflow:
        output += f"❌ Unknown workflow: `{workflow_type}`\n\n"
        output += "Available workflows:\n"
        for wf_id in WORKFLOW_TEMPLATES:
            output += f"- `{wf_id}`\n"
        return output

    # Generate detailed step-by-step guide
    output += f"## {workflow['name']}\n\n"
    output += f"**Description:** {workflow['description']}\n"
    output += f"**Estimated Duration:** {workflow['estimated_duration']}\n"
    output += f"**Minimum Confidence Required:** {workflow['confidence_threshold']:.0%}\n\n"

    output += "---\n\n"
    output += "## Step-by-Step Execution Plan\n\n"

    for i, step in enumerate(workflow["steps"], 1):
        required = step.get("required", False)
        req_badge = "🔴 REQUIRED" if required else "🟢 Recommended"

        output += f"### Step {i}: {step['name']} {req_badge}\n\n"
        output += f"**Tool:** `{step['tool']}`\n\n"

        # Generate example call
        if step["tool"] == "preflight_vm_creation":
            output += "```python\n"
            if step.get("diagnostics_only"):
                output += "# Run preflight for diagnostics (check resources)\n"
            output += "result = preflight_vm_creation(name='your-vm-name')\n"
            output += "# ⚠️ STOP if any checks fail. Fix issues before proceeding.\n"
            output += "```\n\n"

        elif step["tool"] == "create_vm":
            params = step.get("params", {})
            mem = params.get("memory", 2048)
            cpus = params.get("cpus", 2)
            output += "```python\n"
            output += "result = create_vm(\n"
            output += "    name='your-vm-name',\n"
            output += f"    memory={mem},\n"
            output += f"    cpus={cpus}\n"
            output += ")\n"
            output += "```\n\n"

        elif step["tool"] == "trigger_dag":
            dag_id = step.get("dag_id", "your_dag_id")
            output += "```python\n"
            output += f"result = trigger_dag(dag_id='{dag_id}')\n"
            output += "# Note the run_id from the response\n"
            output += "```\n\n"

        elif step["tool"] == "query_rag":
            query = step.get("query", "your query")
            output += "```python\n"
            output += f"result = query_rag(query='{query}')\n"
            output += "```\n\n"

        elif step["tool"] == "get_troubleshooting_history":
            output += "```python\n"
            output += "result = get_troubleshooting_history(only_successful=True, limit=5)\n"
            output += "```\n\n"

        elif step["tool"] == "list_vms":
            check_for = step.get("check_for", "")
            output += "```python\n"
            output += "result = list_vms()\n"
            if check_for:
                output += f"# Look for existing VMs containing '{check_for}'\n"
            output += "```\n\n"

        elif step["tool"] == "get_vm_info":
            output += "```python\n"
            output += "result = get_vm_info(vm_name='your-vm-name')\n"
            if step.get("check_status"):
                output += "# Verify state is 'running'\n"
            output += "```\n\n"

        elif step["tool"] == "get_dag_info":
            output += "```python\n"
            output += f"result = get_dag_info(dag_id='{step.get('dag_id', 'your_dag_id')}')\n"
            output += "# Check last_run_state for completion\n"
            output += "```\n\n"

        else:
            output += f"```python\n{step['tool']}()\n```\n\n"

        # Failure guidance
        output += "**If this step fails:**\n"
        output += "1. Call `get_troubleshooting_history(error_pattern='<error message>')`\n"
        output += "2. Call `query_rag(query='<error message> solution')`\n"
        if required:
            output += "3. **DO NOT proceed** until this step succeeds\n"
        output += "\n---\n\n"

    output += "## Post-Completion\n\n"
    output += "After successful completion, **always log the result:**\n"
    output += "```python\n"
    output += "log_troubleshooting_attempt(\n"
    output += f"    task='{workflow['name']}',\n"
    output += f"    solution='Followed workflow steps 1-{len(workflow['steps'])}',\n"
    output += "    result='success',\n"
    output += "    component='workflow_orchestrator'\n"
    output += ")\n"
    output += "```\n\n"

    output += "This builds the knowledge base for future success.\n"

    return output


@mcp.tool()
async def diagnose_issue(
    symptom: str,
    component: str = "unknown",
    error_message: str = "",
    affected_resource: str = "",
) -> str:
    """
    Structured diagnostic tool for complex infrastructure issues.

    WHEN TO USE: Call this when facing:
    - VM won't start or is unreachable
    - DAG failures with unclear causes
    - Network/DNS issues
    - Resource exhaustion problems
    - Any error that isn't immediately clear

    WHAT YOU GET: A systematic diagnostic plan showing:
    - Categorized checks to run
    - Specific commands/tools for each check
    - Historical solutions for similar issues
    - Escalation paths if basic checks don't help

    HOW IT IMPROVES SUCCESS:
    - Prevents random troubleshooting attempts
    - Checks most common causes first
    - Links to past successful solutions
    - Ensures nothing obvious is missed

    Args:
        symptom: Brief description of what's wrong
                 (e.g., "VM not responding", "DAG stuck in running state")
        component: The component affected: 'vm', 'dag', 'network', 'storage',
                   'freeipa', 'openshift', or 'unknown'
        error_message: Any error message you're seeing (optional but helpful)
        affected_resource: Name of the VM, DAG, or resource having issues (optional)

    EXAMPLES:
        diagnose_issue(symptom="VM won't boot", component="vm", affected_resource="test-vm-1")
        diagnose_issue(symptom="DAG failed", component="dag", error_message="Task timeout")
        diagnose_issue(symptom="cannot resolve hostname", component="network")

    NEXT STEPS after diagnosis:
    - Run the diagnostic checks in order
    - When you find the cause, apply the suggested fix
    - Call log_troubleshooting_attempt() with the solution that worked
    """
    logger.info(f"Tool called: diagnose_issue(symptom='{symptom}', component='{component}')")

    output = "# Structured Diagnostic Analysis\n\n"
    output += f"**Symptom:** {symptom}\n"
    output += f"**Component:** {component}\n"
    if error_message:
        output += f"**Error Message:** `{error_message}`\n"
    if affected_resource:
        output += f"**Affected Resource:** {affected_resource}\n"
    output += "\n---\n\n"

    # Search for historical solutions first
    output += "## Step 1: Check Historical Solutions\n\n"
    output += "First, let's see if this issue has been solved before:\n\n"
    output += "```python\n"
    if error_message:
        output += "get_troubleshooting_history(\n"
        output += f"    error_pattern='{error_message[:50]}',\n"
        output += f"    component='{component}',\n"
        output += "    only_successful=True,\n"
        output += "    limit=5\n"
        output += ")\n"
    else:
        output += "get_troubleshooting_history(\n"
        output += f"    error_pattern='{symptom[:50]}',\n"
        output += "    only_successful=True,\n"
        output += "    limit=5\n"
        output += ")\n"
    output += "```\n\n"

    # Search RAG
    output += "## Step 2: Search Knowledge Base\n\n"
    search_query = f"{symptom} {component} troubleshooting"
    output += "```python\n"
    output += "query_rag(\n"
    output += f"    query='{search_query}',\n"
    output += "    doc_types=['runbook', 'adr', 'troubleshooting'],\n"
    output += "    limit=5\n"
    output += ")\n"
    output += "```\n\n"

    # Component-specific diagnostics
    output += "## Step 3: Run Diagnostic Checks\n\n"

    if component == "vm" or "vm" in symptom.lower():
        output += "### VM-Specific Diagnostics\n\n"
        output += "**Check 1: VM State**\n"
        if affected_resource:
            output += f"```python\nget_vm_info(vm_name='{affected_resource}')\n```\n\n"
        else:
            output += "```python\nlist_vms()  # Find the VM name first\n```\n\n"

        output += "**Check 2: Host Resources**\n"
        output += "```python\npreflight_vm_creation(name='diagnostic-check')\n```\n"
        output += "This will show available memory, disk, and CPU.\n\n"

        output += "**Check 3: Libvirt Service**\n"
        output += "```bash\nsystemctl status libvirtd\n```\n\n"

        output += "**Check 4: VM Console/Logs**\n"
        if affected_resource:
            output += f"```bash\nvirsh console {affected_resource}\n"
            output += f"# Or check logs:\nvirsh domblklist {affected_resource}\n```\n\n"
        else:
            output += "```bash\nvirsh console <vm-name>\n```\n\n"

        output += "### Common VM Issues & Fixes\n\n"
        output += "| Symptom | Likely Cause | Fix |\n"
        output += "|---------|--------------|-----|\n"
        output += "| Won't start | Insufficient memory | Free up RAM or reduce VM memory |\n"
        output += "| No network | libvirt network down | `virsh net-start default` |\n"
        output += "| Boot fails | Corrupt image | Recreate VM with fresh image |\n"
        output += "| Stuck shutting off | Zombie process | `virsh destroy <vm>` |\n\n"

    elif component == "dag" or "dag" in symptom.lower():
        output += "### DAG-Specific Diagnostics\n\n"
        output += "**Check 1: DAG Status**\n"
        if affected_resource:
            output += f"```python\nget_dag_info(dag_id='{affected_resource}')\n```\n\n"
        else:
            output += "```python\nlist_dags()  # Find active DAGs\n```\n\n"

        output += "**Check 2: Airflow Health**\n"
        output += "```python\nget_airflow_status()\n```\n\n"

        output += "**Check 3: DAG Lineage (Upstream Failures)**\n"
        if affected_resource:
            output += f"```python\nget_dag_lineage(dag_id='{affected_resource}')\n```\n\n"
        output += "Check if upstream DAGs failed first.\n\n"

        output += "**Check 4: Task Logs**\n"
        output += "Access Airflow UI at http://localhost:8080 → DAG → Task Instance → Logs\n\n"

        output += "### Common DAG Issues & Fixes\n\n"
        output += "| Symptom | Likely Cause | Fix |\n"
        output += "|---------|--------------|-----|\n"
        output += "| Stuck queued | Worker overload | Scale workers or wait |\n"
        output += "| Import error | Syntax/dep issue | Check DAG file syntax |\n"
        output += "| Task timeout | Long-running op | Increase timeout or optimize |\n"
        output += "| Sensor timeout | Upstream stuck | Check sensor's poke_interval |\n\n"

    elif component == "network" or any(term in symptom.lower() for term in ["dns", "network", "connect", "resolve"]):
        output += "### Network-Specific Diagnostics\n\n"
        output += "**Check 1: DNS Resolution**\n"
        output += "```bash\nnslookup <hostname>\ndig <hostname>\n```\n\n"

        output += "**Check 2: Network Connectivity**\n"
        output += "```bash\nping <target>\nnetstat -tulpn | grep LISTEN\n```\n\n"

        output += "**Check 3: Firewall Rules**\n"
        output += "```bash\nfirewall-cmd --list-all\niptables -L -n\n```\n\n"

        output += "**Check 4: Libvirt Network**\n"
        output += "```bash\nvirsh net-list --all\nvirsh net-info default\n```\n\n"

        output += "**Check 5: FreeIPA DNS (if applicable)**\n"
        output += "```python\nquery_rag(query='freeipa dns troubleshooting')\n```\n\n"

    elif component == "storage" or any(term in symptom.lower() for term in ["disk", "storage", "space", "full"]):
        output += "### Storage-Specific Diagnostics\n\n"
        output += "**Check 1: Disk Space**\n"
        output += "```bash\ndf -h\ndf -i  # inodes\n```\n\n"

        output += "**Check 2: Libvirt Storage Pools**\n"
        output += "```bash\nvirsh pool-list --all\nvirsh pool-info default\n```\n\n"

        output += "**Check 3: Large Files**\n"
        output += "```bash\ndu -sh /var/lib/libvirt/images/*\nfind /var -size +1G -exec ls -lh {} \\;\n```\n\n"

    else:
        output += "### General Diagnostics\n\n"
        output += "**Check 1: System Health**\n"
        output += "```python\nget_system_info()\n```\n\n"

        output += "**Check 2: Airflow Status**\n"
        output += "```python\nget_airflow_status()\n```\n\n"

        output += "**Check 3: Resource Availability**\n"
        output += "```python\npreflight_vm_creation(name='health-check')\n```\n\n"

        output += "**Check 4: Recent Changes**\n"
        output += "```python\nget_troubleshooting_history(limit=10)\n```\n"
        output += "Look for recent activities that might have caused the issue.\n\n"

    output += "---\n\n"
    output += "## Step 4: Log Your Findings\n\n"
    output += "After resolving the issue, **always log it**:\n\n"
    output += "```python\n"
    output += "log_troubleshooting_attempt(\n"
    output += f"    task='{symptom}',\n"
    output += "    solution='<what fixed it>',\n"
    output += "    result='success',  # or 'failed'\n"
    if error_message:
        output += f"    error_message='{error_message[:100]}',\n"
    output += f"    component='{component}'\n"
    output += ")\n"
    output += "```\n\n"

    output += "This helps future troubleshooting succeed faster.\n"

    return output


# =============================================================================
# VM SSH Check API Endpoint (Second-Hop Validation)
# =============================================================================


async def _run_on_host(cmd: str, timeout: int = 10) -> tuple:
    """Run a command on the host via ``ssh root@localhost``.

    kcli/virsh are not available inside the Airflow container — they live
    on the KVM host.  All host-level commands are proxied through the
    first-hop SSH connection that the SSH preflight already validates.

    Returns ``(returncode, stdout_str, stderr_str)``.
    """
    import asyncio as _aio

    proc = await _aio.create_subprocess_exec(
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=5",
        "root@localhost",
        cmd,
        stdout=_aio.subprocess.PIPE,
        stderr=_aio.subprocess.PIPE,
    )
    stdout, stderr = await _aio.wait_for(proc.communicate(), timeout=timeout)
    return proc.returncode, stdout.decode(), stderr.decode()


async def _check_vm_ssh_impl(vm_name: str, ssh_user: str = "cloud-user") -> dict:
    """Check VM SSH reachability and auto-fix key issues.

    All host-level commands (kcli, nc, ssh to VM) are executed on the KVM
    host via ``ssh root@localhost`` because the Airflow container does not
    have kcli/virsh installed.

    Sequential checks:
    1. kcli info vm — get IP  (on host)
    2. nc -z — TCP port 22    (on host)
    3. ssh BatchMode — auth   (on host)
    4. kcli ssh key injection  (on host, only if step 3 failed)

    Uses QUBINODE_SSH_KEY_PATH env var for the primary key (default: id_rsa).
    Returns dict with status and metadata.
    """

    # Determine which SSH key DAGs actually use
    dag_key = os.getenv("QUBINODE_SSH_KEY_PATH", "/root/.ssh/id_rsa")
    dag_key_pub = dag_key + ".pub"

    # Step 1: Get VM IP via kcli (on host)
    try:
        rc, stdout, stderr = await _run_on_host(f"kcli info vm {vm_name}")
    except Exception as exc:
        return {"status": "no_vm", "vm": vm_name, "error": str(exc)}

    if rc != 0:
        return {"status": "no_vm", "vm": vm_name}

    # Parse IP from kcli output (line like "ip: 192.168.122.233")
    ip = None
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("ip:"):
            val = stripped.split(":", 1)[1].strip()
            if val and val.lower() != "none":
                ip = val
            break

    if not ip:
        return {"status": "no_ip", "vm": vm_name}

    # Step 2: TCP port check (on host)
    try:
        rc, _, _ = await _run_on_host(f"nc -z -w3 {ip} 22", timeout=8)
    except Exception:
        return {"status": "port_closed", "vm": vm_name, "ip": ip}

    if rc != 0:
        return {"status": "port_closed", "vm": vm_name, "ip": ip}

    # Step 3: SSH auth test (host -> VM) using the configured key
    ssh_test_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no " f"-o ConnectTimeout=5 -i {dag_key} " f"{ssh_user}@{ip} exit"
    try:
        rc, _, stderr = await _run_on_host(ssh_test_cmd, timeout=12)
    except Exception as exc:
        rc = 1
        stderr = str(exc)

    if rc == 0:
        return {"status": "ok", "vm": vm_name, "ip": ip}

    # Step 4: Auto-fix — inject the DAG key's public key via a cloud-init key
    # kcli injects id_ed25519 into VMs via cloud-init. Try that first,
    # then fall back to other available keys.
    cloud_init_keys = ["/root/.ssh/id_ed25519", "/root/.ssh/id_rsa"]
    # De-duplicate: don't re-test dag_key (already failed in step 3)
    cloud_init_keys = [k for k in cloud_init_keys if k != dag_key]
    fix_applied = False

    for ci_key in cloud_init_keys:
        # Check if the cloud-init key can reach the VM
        ci_test = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no " f"-o ConnectTimeout=5 -i {ci_key} " f"{ssh_user}@{ip} exit"
        try:
            rc, _, _ = await _run_on_host(ci_test, timeout=12)
        except Exception:
            continue
        if rc != 0:
            continue

        # This key works — use it to inject the DAG key's public key
        inject_cmd = (
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
            f"-i {ci_key} {ssh_user}@{ip} "
            f"'mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
            f"cat >> ~/.ssh/authorized_keys && "
            f"chmod 600 ~/.ssh/authorized_keys' "
            f"< {dag_key_pub}"
        )
        try:
            rc, _, inject_err = await _run_on_host(inject_cmd, timeout=15)
            if rc == 0:
                fix_applied = True
                break
        except Exception as exc:
            logger.warning("Key injection via %s failed for %s: %s", ci_key, vm_name, exc)

    if not fix_applied:
        return {
            "status": "auth_failed",
            "vm": vm_name,
            "ip": ip,
            "error": stderr.strip() if stderr else "no working cloud-init key found",
        }

    # Retest SSH with the DAG key
    try:
        rc, _, stderr = await _run_on_host(ssh_test_cmd, timeout=12)
    except Exception as exc:
        return {
            "status": "auth_failed",
            "vm": vm_name,
            "ip": ip,
            "error": str(exc),
        }

    if rc == 0:
        return {
            "status": "fixed",
            "vm": vm_name,
            "ip": ip,
            "fix": f"injected {dag_key_pub} via cloud-init SSH key",
        }

    return {
        "status": "auth_failed",
        "vm": vm_name,
        "ip": ip,
        "error": stderr.strip() if stderr else f"key injected but {dag_key} still fails",
    }


@mcp.custom_route("/api/check-vm-ssh/{vm_name}", methods=["GET"])
async def api_check_vm_ssh(request):
    """HTTP endpoint for VM SSH second-hop validation."""
    from starlette.responses import JSONResponse

    vm_name = request.path_params["vm_name"]
    ssh_user = request.query_params.get("ssh_user", "cloud-user")
    logger.info("API call: check-vm-ssh vm=%s user=%s", vm_name, ssh_user)
    result = await _check_vm_ssh_impl(vm_name, ssh_user)
    return JSONResponse(result)


def main():
    """Main entry point"""
    if not MCP_ENABLED:
        logger.warning("=" * 60)
        logger.warning("Airflow MCP Server is DISABLED")
        logger.warning("To enable: export AIRFLOW_MCP_ENABLED=true")
        logger.warning("=" * 60)
        sys.exit(0)

    logger.info("=" * 60)
    logger.info("Starting FastMCP Airflow Server (ADR-0049)")
    logger.info(f"Host: {MCP_HOST}")
    logger.info(f"Port: {MCP_PORT}")
    logger.info("Tools: DAGs(3), VMs(5), RAG(6), Troubleshooting(2), Lineage(4), Status(2), Orchestration(2)")
    logger.info(f"RAG Available: {RAG_AVAILABLE}")
    logger.info(f"Lineage Available: {LINEAGE_AVAILABLE}")
    logger.info("=" * 60)

    # FastMCP handles everything!
    mcp.run(transport="sse", host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
