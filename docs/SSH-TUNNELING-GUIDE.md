---
nav_exclude: true
---

# SSH Tunneling Guide for Remote Access

## Overview

This guide explains how to securely access Qubinode Navigator services from a remote location using SSH tunneling. This is useful when:

- Your ISP blocks direct access to certain ports
- You need to access services from outside your local network
- You want to keep MCP servers secure behind SSH
- You need to bypass network filtering

## Why SSH Tunneling?

SSH tunneling creates an encrypted tunnel through which you can forward network traffic. This allows you to:

- ✅ Access local services as if they were on your machine
- ✅ Bypass ISP/firewall restrictions
- ✅ Encrypt all traffic between your machine and the server
- ✅ Access multiple services through a single SSH connection
- ✅ Maintain security while working remotely

## Prerequisites

- SSH access to your Qubinode server
- Server IP address or hostname
- SSH credentials (username/password or SSH key)
- Local ports available (8888, 8889, 8080, 8081, 80)

## Setup Methods

### Method 1: SSH Config File (Recommended)

Create or edit `~/.ssh/config`:

```
Host qubinode
    HostName <YOUR_SERVER_IP>
    User root
    IdentityFile ~/.ssh/id_rsa          # Optional: if using SSH keys
    LocalForward 80 localhost:80         # Nginx proxy
    LocalForward 8080 localhost:8080     # AI Assistant
    LocalForward 8081 localhost:8081     # AI Assistant MCP
    LocalForward 8888 localhost:8888     # Airflow Web UI
    LocalForward 8889 localhost:8889     # Airflow MCP Server
    ServerAliveInterval 60               # Keep connection alive
    ServerAliveCountMax 5
```

**Usage:**

```bash
# Connect and establish tunnels
ssh qubinode

# Or run in background
ssh -fN qubinode
```

### Method 2: Command Line

**Connect and stay connected:**

```bash
ssh -L 80:localhost:80 \
    -L 8080:localhost:8080 \
    -L 8081:localhost:8081 \
    -L 8888:localhost:8888 \
    -L 8889:localhost:8889 \
    root@<YOUR_SERVER_IP>
```

**Connect in background (recommended for persistent access):**

```bash
ssh -fN -L 80:localhost:80 \
    -L 8080:localhost:8080 \
    -L 8081:localhost:8081 \
    -L 8888:localhost:8888 \
    -L 8889:localhost:8889 \
    root@<YOUR_SERVER_IP>
```

Flags explained:

- `-f` = fork to background
- `-N` = don't execute remote command
- `-L` = forward local port to remote

### Method 3: Script File

Create `~/bin/qubinode-tunnel.sh`:

```bash
#!/bin/bash
# Qubinode SSH Tunnel Manager

QUBINODE_IP="${1:-<YOUR_SERVER_IP>}"
USER="${2:-root}"

case "${3:-start}" in
    start)
        echo "Starting SSH tunnel to $QUBINODE_IP..."
        ssh -fN -L 80:localhost:80 \
            -L 8080:localhost:8080 \
            -L 8081:localhost:8081 \
            -L 8888:localhost:8888 \
            -L 8889:localhost:8889 \
            "$USER@$QUBINODE_IP"
        echo "✓ Tunnel started in background"
        ;;
    stop)
        echo "Stopping SSH tunnel..."
        pkill -f "ssh.*$QUBINODE_IP"
        echo "✓ Tunnel stopped"
        ;;
    status)
        if pgrep -f "ssh.*$QUBINODE_IP" > /dev/null; then
            echo "✓ Tunnel is running"
        else
            echo "✗ Tunnel is not running"
        fi
        ;;
    *)
        echo "Usage: $0 <server_ip> [user] {start|stop|status}"
        exit 1
        ;;
esac
```

Make it executable:

```bash
chmod +x ~/bin/qubinode-tunnel.sh
```

Usage:

```bash
# Start tunnel
~/bin/qubinode-tunnel.sh 138.201.217.45 root start

# Check status
~/bin/qubinode-tunnel.sh 138.201.217.45 root status

# Stop tunnel
~/bin/qubinode-tunnel.sh 138.201.217.45 root stop
```

## Port Mapping Reference

When tunneling is active, you can access services on these local ports:

| Service            | Local Port | Tunneled To    | Purpose               |
| ------------------ | ---------- | -------------- | --------------------- |
| Nginx Proxy        | 80         | localhost:80   | Web UI reverse proxy  |
| AI Assistant       | 8080       | localhost:8080 | Chat interface        |
| AI Assistant MCP   | 8081       | localhost:8081 | Chat tools for LLMs   |
| Airflow Web UI     | 8888       | localhost:8888 | Workflow interface    |
| Airflow MCP Server | 8889       | localhost:8889 | DAG/VM tools for LLMs |

## Accessing Services Through Tunnel

### Web Interfaces

```bash
# Airflow Web UI (via Nginx proxy)
http://localhost/

# Direct Airflow access
http://localhost:8888/

# AI Assistant (if running)
http://localhost:8080/
```

### MCP Servers (for Claude Desktop)

Update `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "airflow": {
      "command": "curl",
      "args": ["-N", "http://localhost:8889/sse"]
    },
    "qubinode-ai": {
      "command": "curl",
      "args": ["-N", "http://localhost:8081"]
    }
  }
}
```

### Testing Connection

```bash
# Test tunnel is working
curl http://localhost:8888/health | python3 -m json.tool

# Test Airflow MCP
curl -N http://localhost:8889/sse | head -20

# Test Nginx proxy
curl http://localhost/ | head -5
```

## Using SSH Keys (More Secure)

Instead of password authentication, use SSH keys:

### Generate SSH Key (if you don't have one)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_rsa -N ""
```

### Copy Public Key to Server

```bash
ssh-copy-id -i ~/.ssh/id_rsa.pub root@<YOUR_SERVER_IP>
```

### Update SSH Config

```
Host qubinode
    HostName <YOUR_SERVER_IP>
    User root
    IdentityFile ~/.ssh/id_rsa
    LocalForward 80 localhost:80
    LocalForward 8080 localhost:8080
    LocalForward 8081 localhost:8081
    LocalForward 8888 localhost:8888
    LocalForward 8889 localhost:8889
```

Now you can connect without entering a password:

```bash
ssh -fN qubinode
```

## Advanced Configuration

### Keep Tunnel Alive Automatically

Add to `~/.ssh/config`:

```
Host qubinode
    HostName <YOUR_SERVER_IP>
    User root
    LocalForward 80 localhost:80
    LocalForward 8080 localhost:8080
    LocalForward 8081 localhost:8081
    LocalForward 8888 localhost:8888
    LocalForward 8889 localhost:8889

    # Keep connection alive
    ServerAliveInterval 60
    ServerAliveCountMax 5

    # Auto-reconnect on failure
    ConnectTimeout 10
    StrictHostKeyChecking no
```

### Use with Autossh (Persistent Reconnection)

Install autossh:

```bash
# macOS
brew install autossh

# Linux
sudo apt-get install autossh  # Debian/Ubuntu
sudo dnf install autossh      # RHEL/Rocky
```

Use autossh instead of ssh:

```bash
autossh -M 20000 -fN -L 80:localhost:80 \
    -L 8080:localhost:8080 \
    -L 8081:localhost:8081 \
    -L 8888:localhost:8888 \
    -L 8889:localhost:8889 \
    root@<YOUR_SERVER_IP>
```

The `-M 20000` flag tells autossh to use port 20000 for monitoring.

## Managing Tunnels

### Check if Tunnel is Running

```bash
# Method 1: Check process
ps aux | grep "ssh.*qubinode"

# Method 2: Check port listening
netstat -tuln | grep 8889

# Method 3: Test connection
curl http://localhost:8888/health
```

### Stop Tunnel

```bash
# If using background process
pkill -f "ssh.*<YOUR_SERVER_IP>"

# If using autossh
pkill autossh

# If interactive session, press Ctrl+C
```

### Troubleshooting Connection Issues

```bash
# Verbose SSH output (helpful for debugging)
ssh -vvv -L 8888:localhost:8888 root@<YOUR_SERVER_IP>

# Check SSH service on server
ssh root@<YOUR_SERVER_IP> 'systemctl status ssh'

# Verify port forwarding
ssh root@<YOUR_SERVER_IP> 'netstat -tuln | grep 8888'
```

## Firewall Configuration

### On Your Local Machine

If using a firewall, allow SSH:

```bash
# macOS
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/ssh

# Linux (firewalld)
sudo firewall-cmd --add-service=ssh --permanent
sudo firewall-cmd --reload

# Linux (ufw)
sudo ufw allow ssh
```

### On Qubinode Server

Allow SSH access:

```bash
sudo firewall-cmd --add-service=ssh --permanent
sudo firewall-cmd --reload
```

## Security Best Practices

1. **Use SSH Keys**

   - More secure than passwords
   - Easier to automate
   - Can be revoked independently

1. **Limit SSH Access**

   - Disable root login if possible
   - Use key-based authentication only
   - Restrict SSH to specific IPs if feasible

1. **Monitor Tunnels**

   - Regularly check active connections
   - Close unused tunnels
   - Audit SSH logs

1. **Use Non-Standard SSH Port** (Optional)

   - Change SSH port from 22 to reduce scanning
   - Update config: `Port 2222`

1. **Enable SSH Timeout**

   - Automatically close idle connections
   - Add to server `sshd_config`:
     ```
     ClientAliveInterval 300
     ClientAliveCountMax 2
     ```

## Scheduling Tunnel at Startup

### macOS (using launchd)

Create `~/Library/LaunchAgents/com.qubinode.tunnel.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.qubinode.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/ssh</string>
        <string>-fN</string>
        <string>qubinode</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.qubinode.tunnel.plist
```

### Linux (using systemd)

Create `~/.config/systemd/user/qubinode-tunnel.service`:

```ini
[Unit]
Description=Qubinode SSH Tunnel
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/ssh -fN qubinode
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl --user enable qubinode-tunnel
systemctl --user start qubinode-tunnel
```

Check status:

```bash
systemctl --user status qubinode-tunnel
```

## Troubleshooting Common Issues

### "Connection refused"

```bash
# Check if SSH service is running on server
ssh root@<YOUR_SERVER_IP> 'systemctl status ssh'

# Check if firewall is blocking
ssh root@<YOUR_SERVER_IP> 'sudo firewall-cmd --list-all'
```

### "Port already in use"

```bash
# Check what's using the port
lsof -i :8888

# Kill the process
kill <PID>

# Or use a different local port
ssh -L 9888:localhost:8888 root@<YOUR_SERVER_IP>
```

### "Permission denied (publickey)"

```bash
# Check SSH key permissions
ls -la ~/.ssh/

# Should be:
# -rw------- for private keys
# -rw-r--r-- for public keys

# Fix permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

### "Tunnel works but services not responding"

```bash
# Verify services are running on server
ssh root@<YOUR_SERVER_IP> 'podman ps'

# Check specific service
ssh root@<YOUR_SERVER_IP> 'curl http://localhost:8888/health'
```

## Example: Complete Setup

**Step 1: Generate SSH key**

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_rsa -N ""
```

**Step 2: Add key to server**

```bash
ssh-copy-id -i ~/.ssh/id_rsa.pub root@138.201.217.45
```

**Step 3: Create SSH config**

```bash
cat > ~/.ssh/config << 'EOF'
Host qubinode
    HostName 138.201.217.45
    User root
    IdentityFile ~/.ssh/id_rsa
    LocalForward 80 localhost:80
    LocalForward 8080 localhost:8080
    LocalForward 8081 localhost:8081
    LocalForward 8888 localhost:8888
    LocalForward 8889 localhost:8889
    ServerAliveInterval 60
    ServerAliveCountMax 5
EOF
```

**Step 4: Start tunnel**

```bash
ssh -fN qubinode
```

**Step 5: Verify connection**

```bash
curl http://localhost:8888/health
```

**Step 6: Access services**

- **Web UI**: http://localhost:8888
- **MCP Server**: http://localhost:8889/sse

Done! 🎉

## References

- [SSH Manual](https://man.openbsd.org/ssh)
- [SSH Config Manual](https://man.openbsd.org/ssh_config)
- [Using SSH Tunneling](https://www.ssh.com/ssh/tunneling/)
- [Autossh Documentation](http://www.harding.motd.ca/autossh/)

______________________________________________________________________

**Last Updated**: 2025-11-26
