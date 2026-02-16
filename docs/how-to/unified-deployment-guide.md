---
title: Unified Deployment Guide
parent: How to
nav_order: 7
---

# Qubinode Navigator Unified Deployment with Nginx

## 🎯 Overview

Single-script deployment of complete Qubinode Navigator stack with production-ready security via nginx reverse proxy.

## ✨ What's Included

### Components Deployed:

1. **AI Assistant** - RAG-powered assistant
1. **Apache Airflow** - Workflow orchestration with kcli/virsh
1. **Nginx Reverse Proxy** - Secure single entry point
1. **Firewall Configuration** - Proper security rules
1. **Podman Network** - Shared networking for all services

### Security Features:

- ✅ Direct ports (8888, 8080) closed
- ✅ Access only through nginx (80/443)
- ✅ Production-ready architecture
- ✅ SSL/TLS ready
- ✅ Single entry point for all services

## 🚀 Quick Start

### One-Command Deployment:

```bash
cd /opt/qubinode_navigator
./deploy-qubinode-with-airflow.sh
```

That's it! The script handles:

1. Base infrastructure deployment
1. Airflow workflow orchestration setup
1. Nginx reverse proxy configuration
1. Firewall security rules
1. Service verification

## 📋 Deployment Steps

The unified script performs these steps automatically:

### Step 1: Base Infrastructure (1/4)

- Deploys hypervisor setup
- Starts AI Assistant container
- Configures base networking

### Step 2: Airflow Deployment (2/4)

- Builds custom Airflow image with kcli
- Deploys Airflow services (webserver, scheduler, postgres)
- Mounts volumes and scripts
- Connects to shared network

### Step 3: Nginx Reverse Proxy (3/4)

- Installs nginx if needed
- Creates reverse proxy configuration
- Configures firewall (closes 8888/8080, opens 80/443)
- Starts and enables nginx service

### Step 4: Verification (4/4)

- Verifies all services running
- Tests connectivity
- Displays access URLs

## 🌐 Access Points

After deployment:

| Service          | URL                   | Credentials   |
| ---------------- | --------------------- | ------------- |
| **Airflow UI**   | http://YOUR_IP/       | admin / admin |
| **AI Assistant** | http://YOUR_IP/ai/    | (no auth)     |
| **Health Check** | http://YOUR_IP/health | (status)      |

Replace `YOUR_IP` with your server IP (shown in deployment output).

## 🔒 Security Architecture

### Before (Direct Access):

```
Internet → Port 8888 → Airflow
Internet → Port 8080 → AI Assistant
❌ Multiple entry points
❌ Ports exposed directly
```

### After (Nginx Reverse Proxy):

```
Internet → Port 80/443 → Nginx → {
                                    Port 8888 (localhost only) → Airflow
                                    Port 8080 (localhost only) → AI Assistant
                                  }
✅ Single entry point
✅ SSL termination point
✅ Better security
```

### Firewall Rules:

**Closed:**

- ❌ Port 8888 (Airflow direct access)
- ❌ Port 8080 (AI Assistant direct access)

**Open:**

- ✅ Port 80 (HTTP via nginx)
- ✅ Port 443 (HTTPS via nginx - ready for SSL)
- ✅ Port 22 (SSH)
- ✅ Port 9090 (Cockpit - if installed)

## 🔧 Configuration Files

### Nginx Configuration:

**Location:** `/etc/nginx/conf.d/airflow.conf`

Automatically created by deployment script with:

- Airflow UI served at root (`/`)
- AI Assistant API at `/ai/`
- Health check at `/health`
- WebSocket support for Airflow live updates
- Proper timeout settings

### Airflow Configuration:

**Location:** `/opt/qubinode_navigator/airflow/docker-compose.yml`

Key settings:

- No BASE_URL (serves at any path)
- ENABLE_PROXY_FIX enabled
- Shared network with AI Assistant
- Scripts mounted for DAGs

## 🧪 Testing

### Verify Deployment:

```bash
# Check nginx status
systemctl status nginx

# Check Airflow containers
cd /opt/qubinode_navigator/airflow
podman ps

# Test health endpoint
curl http://localhost/health

# Test Airflow UI
curl -I http://localhost/

# Check firewall rules
firewall-cmd --list-services
firewall-cmd --list-ports
```

### Expected Results:

```bash
$ systemctl status nginx
✅ Active: active (running)

$ podman ps
✅ airflow_airflow-webserver_1 (healthy)
✅ airflow_airflow-scheduler_1 (running)
✅ airflow_postgres_1 (healthy)
✅ qubinode-ai-assistant (running)

$ curl http://localhost/health
✅ {"metadatabase": {"status": "healthy"}, ...}

$ firewall-cmd --list-services
✅ http https ssh cockpit

$ firewall-cmd --list-ports
(empty - good! no direct port access)
```

## 🎓 Usage

### Access Airflow UI:

1. **Open browser:** `http://YOUR_SERVER_IP/`
1. **Login:** admin / admin
1. **Enable DAGs** you want to run
1. **Trigger test DAG** to verify VM creation

### Test VM Creation:

```bash
# From command line
cd /opt/qubinode_navigator/airflow
./scripts/test-kcli-create-vm.sh test-vm centos10stream 1024 1 10

# Or trigger via Airflow UI:
# - Go to DAGs page
# - Find "example_kcli_script_based"
# - Click play button ▶️
# - Watch it create a real VM!
```

### Check Logs:

```bash
# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Airflow logs
podman logs -f airflow_airflow-webserver_1
podman logs -f airflow_airflow-scheduler_1
```

## 🔐 Adding SSL/TLS

The deployment is **SSL-ready**. To add HTTPS:

### Option 1: Let's Encrypt (Recommended for production)

```bash
# Install certbot
dnf install -y certbot python3-certbot-nginx

# Get certificate (requires domain name)
certbot --nginx -d yourdomain.com

# Certbot will automatically update nginx config
# Firewall already has port 443 open!
```

### Option 2: Self-Signed Certificate (Testing)

```bash
# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/nginx.key \
  -out /etc/ssl/certs/nginx.crt

# Update nginx config
vim /etc/nginx/conf.d/airflow.conf
# Add SSL server block (see template in config file)

# Reload nginx
nginx -t && systemctl reload nginx
```

## 📊 Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                     Internet / Users                        │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Nginx :80     │  ← Single Entry Point
                  │  (Reverse Proxy)│
                  └────────┬────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
    ┌─────────────┐               ┌──────────────┐
    │  Airflow    │               │ AI Assistant │
    │  :8888      │◄──────────────┤    :8080     │
    │  (localhost)│   Network     │ (localhost)  │
    └──────┬──────┘   Connection  └──────────────┘
           │
           ▼
    ┌─────────────┐
    │  PostgreSQL │
    │    :5432    │
    └─────────────┘

    ┌─────────────┐
    │   libvirt   │  ← VM Management
    │   :qemu///  │
    └─────────────┘

Network: airflow_default (podman)
Security: Firewall (firewalld)
```

## 🛠️ Customization

### Change Nginx Port:

Edit `/etc/nginx/conf.d/airflow.conf`:

```nginx
server {
    listen 8080;  # Change from 80
    # ...
}
```

Update firewall:

```bash
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload
```

### Add IP Restrictions:

Edit nginx config to allow only specific IPs:

```nginx
server {
    # Existing config...

    allow 192.168.1.0/24;  # Internal network
    allow YOUR_IP_HERE;    # Your IP
    deny all;              # Block everyone else
}
```

### Add Basic Authentication:

```bash
# Create password file
htpasswd -c /etc/nginx/.htpasswd admin

# Update nginx config
location / {
    auth_basic "Airflow Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    # ... rest of proxy config
}
```

## 🔄 Updating

### Update Airflow:

```bash
cd /opt/qubinode_navigator/airflow
./deploy-airflow.sh rebuild
```

### Update Nginx Config:

```bash
vim /etc/nginx/conf.d/airflow.conf
nginx -t
systemctl reload nginx
```

### Re-run Full Deployment:

```bash
cd /opt/qubinode_navigator
./deploy-qubinode-with-airflow.sh
```

## 🚨 Troubleshooting

### Issue: Can't access Airflow UI

**Check nginx:**

```bash
systemctl status nginx
curl http://localhost/
```

**Check firewall:**

```bash
firewall-cmd --list-services | grep http
```

**Check Airflow:**

```bash
podman ps | grep airflow
curl http://localhost:8888/
```

### Issue: 502 Bad Gateway

**Cause:** Backend not responding

**Fix:**

```bash
# Restart Airflow
cd /opt/qubinode_navigator/airflow
podman-compose restart

# Check logs
podman logs airflow_airflow-webserver_1
```

### Issue: SSL Certificate Errors

**For Let's Encrypt:**

```bash
certbot renew --dry-run
```

**For self-signed:**

```bash
# Browsers will show warning (expected)
# Click "Advanced" → "Proceed anyway"
```

## 📚 Related Documentation

- `airflow/NGINX-REVERSE-PROXY-SETUP.md` - Detailed nginx guide
- `airflow/DEPLOYMENT-STATUS.md` - Current deployment status
- `airflow/FIREWALL-SETUP.md` - Firewall configuration
- `airflow/SUMMARY-AND-NEXT-STEPS.md` - Next steps

## ✅ Success Criteria

Deployment is successful when:

- [ ] All containers running
- [ ] Nginx active and serving
- [ ] Can access http://YOUR_IP/
- [ ] Airflow login page loads
- [ ] Can login with admin/admin
- [ ] DAGs are visible
- [ ] Health check returns healthy
- [ ] Direct ports 8888/8080 NOT accessible externally
- [ ] Only port 80/443 accessible

## 🎯 Production Checklist

Before going to production:

- [ ] Add SSL certificate (Let's Encrypt)
- [ ] Change default admin password
- [ ] Configure authentication (LDAP/OAuth)
- [ ] Set up monitoring/alerting
- [ ] Configure log rotation
- [ ] Set up backups (database, configs)
- [ ] Document runbooks
- [ ] Test disaster recovery
- [ ] Security scan/audit
- [ ] Performance testing

## 💡 Tips

1. **Use a domain name** instead of IP for SSL
1. **Change default passwords** immediately
1. **Enable HTTPS** for production
1. **Monitor logs** regularly
1. **Keep systems updated** (dnf update)
1. **Backup regularly** (postgres, configs)
1. **Test DAGs** in dev first
1. **Use version control** for DAG files

## 📞 Support

For issues:

1. Check logs (nginx, Airflow, podman)
1. Review documentation
1. Test components individually
1. Use AI Assistant for guidance

______________________________________________________________________

**Status:** Production-Ready ✅
**Security:** Nginx Reverse Proxy ✅
**SSL:** Ready to configure ✅
**Automation:** Single-script deployment ✅
