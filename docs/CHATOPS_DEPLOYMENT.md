# ChatOps Deployment Guide

## Overview

Deploy ChatOps service to `whitebox.ts.net` (192.168.0.102) as a systemd service accessible via Tailscale.

## Prerequisites

- Python 3.12+ installed on whitebox
- Tailscale running with MagicDNS enabled
- API key generated (`make genkey` or `openssl rand -base64 32`)
- Discord webhook URL (optional, for audit alerts)

## Installation Steps

### 1. Clone repository

```bash
ssh whitebox.ts.net
cd /opt
sudo git clone https://github.com/mroresi/oresi-homelab.git
cd oresi-homelab
```

### 2. Create virtual environment

```bash
cd /opt/oresi-homelab
python3.12 -m venv .venv
.venv/bin/pip install -r chatops/requirements.txt
```

### 3. Configure environment

```bash
sudo mkdir -p /etc/chatops
sudo cp chatops/.env.example /etc/chatops/.env
sudo nano /etc/chatops/.env
```

Edit `/etc/chatops/.env`:

```bash
CHATOPS_API_KEY=<generate with: openssl rand -base64 32>
CHATOPS_IP_ALLOWLIST=192.168.0.0/24,100.64.0.0/10  # LAN + Tailscale CGNAT
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN
APPROVED_LABEL=approved-by-gemini
LOG_LEVEL=INFO
```

### 4. Create systemd service

```bash
sudo nano /etc/systemd/system/chatops.service
```

Add:

```ini
[Unit]
Description=ChatOps Microservice
After=network.target tailscaled.service
Wants=tailscaled.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/oresi-homelab
EnvironmentFile=/etc/chatops/.env
ExecStart=/opt/oresi-homelab/.venv/bin/uvicorn chatops.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10s

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/oresi-homelab

[Install]
WantedBy=multi-user.target
```

### 5. Enable and start service

```bash
sudo systemctl daemon-reload
sudo systemctl enable chatops.service
sudo systemctl start chatops.service
sudo systemctl status chatops.service
```

### 6. Verify health

```bash
# Local check
curl -fsS http://localhost:8000/healthz

# Tailscale check
curl -fsS http://whitebox.ts.net:8000/healthz
```

## Tailscale ACL Configuration

Add to your Tailscale ACL (`tailscale.com/admin/acls`):

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:admin"],
      "dst": ["whitebox:8000"]
    },
    {
      "action": "accept",
      "src": ["tag:automation"],
      "dst": ["whitebox:8000"]
    }
  ],
  "tagOwners": {
    "tag:automation": ["your-email@example.com"]
  }
}
```

This allows:

- Admins to access ChatOps from any Tailscale device
- Tagged automation clients (GitHub Actions, CI/CD) to trigger intents
- See `docs/policies/tailscale/github-allowlist.md` for generating an expanded
  ACL that allowlists GitHub webhook and Actions source networks.

## Usage

### Test API with curl

```bash
export CHATOPS_API_KEY="your-key-here"

# Health check
curl http://whitebox.ts.net:8000/healthz

# Execute intent (scale)
curl -X POST http://whitebox.ts.net:8000/run \
  -H "X-API-Key: $CHATOPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "scale_stack_media"}'

# Execute intent (rollout)
curl -X POST http://whitebox.ts.net:8000/run \
  -H "X-API-Key: $CHATOPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "rollout_stack_ai"}'
```

### GitHub Actions integration

```yaml
name: Deploy Stack
on:
  push:
    branches: [main]
    paths:
      - 'stacks/stack-media/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Tailscale
        uses: tailscale/github-action@v2
        with:
          oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}
          oauth-secret: ${{ secrets.TS_OAUTH_SECRET }}
          tags: tag:automation
      
      - name: Trigger rollout
        run: |
          curl -X POST http://whitebox.ts.net:8000/run \
            -H "X-API-Key: ${{ secrets.CHATOPS_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d '{"name": "rollout_stack_media"}'
```

## Monitoring

### Uptime Kuma

Import the preconfigured monitor:

```bash
# In Uptime Kuma UI: Settings → Backup → Import
# Upload: monitoring/uptime_kuma_chatops.json
```

Or create manually:

- **Type**: HTTP(s)
- **URL**: `http://whitebox.ts.net:8000/healthz`
- **Interval**: 60 seconds
- **Accepted status codes**: 200
- **Keyword**: `ok`

### Discord Alerts

Discord webhook receives real-time alerts for:

- 🚨 Security violations (auth failures, IP blocks, label mismatches)
- ❌ Command failures with stderr output (truncated to 500 chars)
- ✅ Successful deployments

### Logs

```bash
# Live logs
sudo journalctl -u chatops.service -f

# Last 100 lines
sudo journalctl -u chatops.service -n 100

# JSON structured logs
sudo journalctl -u chatops.service -o json-pretty
```

## Maintenance

### Update service

```bash
cd /opt/oresi-homelab
sudo git pull
.venv/bin/pip install -r chatops/requirements.txt --upgrade
sudo systemctl restart chatops.service
```

### Rotate API key

```bash
# Generate new key
openssl rand -base64 32

# Update /etc/chatops/.env
sudo nano /etc/chatops/.env

# Restart service
sudo systemctl restart chatops.service

# Update all clients (GitHub secrets, curl scripts, etc.)
```

### Add new intent

```bash
cd /opt/oresi-homelab
sudo nano chatops/intents/my_new_intent.yaml
# Add intent YAML following schema
sudo systemctl restart chatops.service  # Optional: intents are loaded on-demand
```

## Security Hardening

### Firewall (optional)

If not using Tailscale exclusively:

```bash
# Allow only Tailscale subnet
sudo ufw allow from 100.64.0.0/10 to any port 8000
sudo ufw deny 8000
```

### Audit trail

All operations are logged with:

- Intent name
- Action (scale/rollout)
- Stack and service
- Executed command (argv)
- Client IP (from X-Forwarded-For or direct)
- Exit code and stderr on failure

Search logs:

```bash
# Find all failed deployments
sudo journalctl -u chatops.service | grep command_failed

# Find deployments by specific client
sudo journalctl -u chatops.service | grep '"client": "192.168.0.5"'

# Find all scale actions
sudo journalctl -u chatops.service | grep '"action": "scale"'
```

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u chatops.service -n 50

# Common issues:
# - Missing .env file: check /etc/chatops/.env exists
# - Python import errors: reinstall requirements
# - Port already in use: check with `sudo lsof -i :8000`
```

### Health check fails

```bash
# Test locally
curl -v http://localhost:8000/healthz

# Check service status
sudo systemctl status chatops.service

# Check if process is running
ps aux | grep uvicorn
```

### Intent execution fails

```bash
# Validate intent YAML
python3 -c "import yaml; print(yaml.safe_load(open('chatops/intents/my_intent.yaml')))"

# Test docker compose manually
docker compose -f /opt/stacks/stack-media/docker-compose.yml config

# Check docker daemon
sudo systemctl status docker
```

---

**Deployment checklist:**

- [ ] Python 3.12+ and git installed
- [ ] Repository cloned to `/opt/oresi-homelab`
- [ ] Virtual environment created and requirements installed
- [ ] `/etc/chatops/.env` configured with API key and allowlist
- [ ] Systemd service created and enabled
- [ ] Service started and health check passes
- [ ] Tailscale ACLs configured
- [ ] Uptime Kuma monitor added
- [ ] Discord webhook tested (optional)
- [ ] GitHub Actions secrets configured (if using CI/CD)
