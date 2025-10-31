# 🧩 ORESI // SYSTEMS — Section 6: GitOps Workflow & Dockge Management

**Version:** 1.0 • **Date:** 2025-10-29  
**Applies to:** whitebox, redbox, bloodbox  
**Linked System:** blackbox (Synology NAS)  
**Objective:** Implement a reproducible, version-controlled deployment system using GitOps principles, Dockge, and NFS-backed Docker volumes.

---

## 6.0 🔍 Design Intent

Your homelab should be:  

- 🌀 **Stateless at compute level** — everything can be rebuilt via Git.  
- 💾 **Persistent at data level** — all app configs and databases live on NFS.  
- 📡 **Accessible anywhere** — every VM joins the Tailscale mesh.  
- 🧱 **Composable** — stacks deploy independently, update atomically, and recover instantly.

Each VM uses a Git-based directory mounted at `/opt/stacks`, synchronized from your central repository.  
Each stack represents a **functional domain** (Infra, Media, Content, AI, SmartHome).

---

## 6.1 🏗️ Folder Layout in Git Repo

```
/my-homelab-configs/
├── .gitignore
├── stack-infra/
│   ├── docker-compose.yml
│   └── .env.template
├── stack-media/
│   ├── docker-compose.yml
│   └── .env.template
├── stack-content/
│   ├── docker-compose.yml
│   └── .env.template
├── stack-ai/
│   ├── docker-compose.yml
│   └── .env.template
└── stack-smarthome/
    ├── docker-compose.yml
    └── .env.template
```

### `.gitignore`

```bash
# Ignore all .env files and secrets
**/.env
# Ignore Dockge data
**/data/
```

### Example `.env.template`

```bash
TZ=America/Vancouver
PUID=1000
PGID=1000
DOCKER_DATA=/srv/config
MEDIA_PATH=/srv/media
DOWNLOAD_PATH=/srv/downloads
```

---

## 6.2 🪄 Bootstrapping GitOps on Each VM

### Step 1 — Install Core Tools

```bash
sudo apt update && sudo apt install -y git docker.io docker-compose tailscale
sudo systemctl enable docker
```

### Step 2 — Clone Config Repository

```bash
sudo mkdir -p /opt/stacks
sudo chown -R $USER:$USER /opt/stacks
cd /opt/stacks
git clone https://github.com/YOUR_USERNAME/my-homelab-configs.git .
```

### Step 3 — Enable Auto-Sync (Optional)

```bash
# Pull updates from git hourly
echo "0 * * * * cd /opt/stacks && git pull" | sudo tee /etc/cron.d/gitops-sync
sudo systemctl restart cron
```

---

## 6.3 🧭 Deploy Dockge (Container Stack Manager)

### Create Dockge Compose File `/opt/stacks/stack-infra/docker-compose.yml`

```yaml
version: "3.9"
services:
  dockge:
    image: louislam/dockge:latest
    container_name: dockge
    restart: unless-stopped
    ports:
      - "5001:5001"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /opt/stacks:/opt/stacks
      - /srv/config/dockge:/app/data
    environment:
      - TZ=America/Vancouver
      - PUID=1000
      - PGID=1000
```

### Start Dockge

```bash
cd /opt/stacks/stack-infra
docker compose up -d
```

Access via:  
🌐 <http://192.168.0.101:5001> or <http://whitebox.local:5001>

Dockge will autodiscover other stacks from `/opt/stacks/*/docker-compose.yml`.

---

## 6.4 🧰 Deploy Example: Media Stack

```bash
cd /opt/stacks/stack-media
docker compose up -d
```

### Example Compose (Simplified)

```yaml
version: "3.9"
services:
  sonarr:
    image: lscr.io/linuxserver/sonarr:latest
    container_name: sonarr
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/Vancouver
    volumes:
      - /srv/config/sonarr:/config
      - /srv/media/tv:/tv
      - /srv/downloads/complete/sonarr:/downloads
    ports:
      - "8989:8989"
    restart: unless-stopped
```

✅ Repeat the pattern for `radarr`, `prowlarr`, `qbittorrent`, etc.

---

## 6.5 🧠 Visual Workflow Diagram

```
──────────────────────────────────────────────────────────────────────
            GITOPS AUTOMATION FLOW  —  ORESI // SYSTEMS
──────────────────────────────────────────────────────────────────────
   [GitHub Repo: my-homelab-configs]
             ↓ (pull)
      ┌────────────────┐
      │  VM (whitebox) │
      │   vm-infra     │──────► Dockge
      └────────────────┘
             ↓
   [ docker compose up -d ]
             ↓
   All volumes mapped to:
      /srv/config   (NFS: Synology/docker_data)
      /srv/media    (NFS: Synology/media)
      /srv/downloads (NFS: Synology/downloads)
──────────────────────────────────────────────────────────────────────
```

---

## 6.6 🧩 Integration with Tailscale & MagicDNS

- Each VM should register its hostname (auto via `tailscale up --hostname=$(hostname)`).
- Example:
  - `whitebox.bombay-porgy.ts.net` → Dockge
  - `redbox.bombay-porgy.ts.net` → Media stack
  - `bloodbox.bombay-porgy.ts.net` → AI stack
- Access remotely via MagicDNS:
  - `https://dockge.whitebox.bombay-porgy.ts.net:5001`
  - `https://radarr.redbox.bombay-porgy.ts.net:7878`

---

## 6.7 🔄 Updating Stacks

### Manual Update

```bash
cd /opt/stacks
git pull
docker compose pull
docker compose up -d
```

### Automated (Watchtower)

Add this service to `stack-infra/docker-compose.yml`:

```yaml
watchtower:
  image: containrrr/watchtower
  container_name: watchtower
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  restart: unless-stopped
  command: --cleanup --interval 21600  # every 6 hours
```

---

## 6.8 🧾 Maintenance

- Backup `/srv/config` weekly (on Synology Hyper Backup).
- Run `git commit` + `git push` after any change in Docker YAMLs.
- Monitor all stack health from **Dockge → Overview Dashboard**.
- Log errors with:

  ```bash
  docker compose logs --tail 100 -f
  ```

- Re-deploy a full stack from scratch:

  ```bash
  docker compose down -v
  docker compose up -d
  ```

---

✅ **End of Section 6 — GitOps Workflow & Dockge Management**
Next up: **Section 7 — Monitoring, Observability & Alerting (Uptime Kuma, Tautulli, Glances, Netdata)**
