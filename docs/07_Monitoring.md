# 🧠 ORESI // SYSTEMS — Section 7: Monitoring, Observability & Alerting

**Version:** 1.0  •  **Date:** 2025-10-29  
**Applies to:** whitebox (.101), redbox (.100), bloodbox (.103)  
**Linked Systems:** blackbox (.40 Synology NFS) + Tailscale Mesh  
**Objective:** Centralize real-time monitoring, historical performance, and incident alerts using Uptime Kuma, Glances, Netdata, and Tautulli.

---

## 7.0 🎯 Design Intent

Monitoring should:  

- 🩺 Detect failures within 60 seconds.  
- 📈 Track CPU / RAM / I/O usage for each VM and container.  
- 🚨 Send alerts through Discord or Telegram.  
- 🌎 Be accessible via Tailscale MagicDNS (e.g., whitebox.bombay-porgy.ts.net).  
- 💾 Store logs and metrics on Synology for retention and backups.

---

## 7.1 🧱 Monitoring Architecture

```
─────────────────────────────────────────────────────────────
          ORESI // SYSTEMS — MONITORING LAYOUT
─────────────────────────────────────────────────────────────
        [ whitebox (.101) ]
        ├─ Uptime Kuma  (Web checks, API monitors)
        ├─ Glances      (Node resource metrics)
        └─ Dockge       (Stack orchestration)

        [ redbox (.100) ]
        ├─ Netdata Node (Container metrics collector)
        ├─ Tautulli     (Plex activity analytics)
        └─ Media Stack health export

        [ bloodbox (.103) ]
        └─ Netdata Node (AI workload stats)

        [ blackbox (.40) ]
        └─ NFS Backups / Metrics archive

        Dash Access:
  • http://whitebox.bombay-porgy.ts.net:3001
  • http://redbox.bombay-porgy.ts.net:19999
─────────────────────────────────────────────────────────────
```

---

## 7.2 🚦 Uptime Kuma (whitebox)

### Compose snippet (`/opt/stacks/stack-infra/docker-compose.yml`)

```yaml
uptimekuma:
  image: louislam/uptime-kuma:latest
  container_name: uptimekuma
  ports:
    - "3001:3001"
  volumes:
    - /srv/config/uptimekuma:/app/data
  restart: unless-stopped
  environment:
    - TZ=America/Vancouver
```

Access → 🌐 <http://192.168.0.101:3001>  

**Checks to add:**

| Type | Target | Notes |
|------|---------|-------|
| HTTP | <http://redbox.bombay-porgy.ts.net:7878> | Radarr availability |
| Ping | 192.168.0.40 | Synology status |
| TCP | 22 @ whitebox | SSH reachable |
| Docker Container | qBittorrent | via Docker integration |
| HTTP | <http://whitebox.bombay-porgy.ts.net:8000/healthz> | ChatOps health endpoint (200 OK) |

**Notifications:** connect Discord Webhook or Telegram Bot.  

### ChatOps observability notes

- Protect ChatOps behind Tailscale or a reverse proxy. Prefer MagicDNS (e.g., `whitebox.bombay-porgy.ts.net`).
- Add the HTTP check to `/healthz` with 60s interval and 10s timeout.
- Consider adding a keyword check for `{"status":"ok"}` for extra assurance.

---

## 7.3 📊 Glances (Node Dashboard)

### Install on each VM

```bash
sudo apt install -y glances python3-pip
sudo glances -w &
```

WebUI: `http://<vm-ip>:61208`

**Add reverse proxy in Dockge** to expose through MagicDNS for secure access.  

---

## 7.4 📡 Netdata (Advanced Monitoring)

### Docker Compose on redbox

```yaml
netdata:
  image: netdata/netdata:latest
  container_name: netdata
  hostname: redbox
  ports:
    - "19999:19999"
  volumes:
    - /srv/config/netdata:/etc/netdata
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
    - /etc/os-release:/host/etc/os-release:ro
  cap_add:
    - SYS_PTRACE
  security_opt:
    - apparmor:unconfined
  restart: unless-stopped
```

**Dash:** <http://redbox.bombay-porgy.ts.net:19999>  
**Tip:** Add “Cloud Aggregation Node” on whitebox to centralize metrics from all nodes.  

---

## 7.5 🎞️ Tautulli (Plex Analytics)

### Compose on redbox

```yaml
tautulli:
  image: lscr.io/linuxserver/tautulli:latest
  container_name: tautulli
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Vancouver
  volumes:
    - /srv/config/tautulli:/config
  ports:
    - "8181:8181"
  restart: unless-stopped
```

Connect to your Plex server via API token for detailed user and play stats.  

---

## 7.6 📈 Metrics Aggregation and Alerts

| Tool | Purpose | Retention | Alert Destination |
|------|-----------|------------|------------------|
| Uptime Kuma | Availability checks | 30 days | Discord / Email |
| Netdata | Performance metrics | 7 days rolling | Browser + Webhook |
| Glances | Quick resource view | real-time | Local only |
| Tautulli | Media usage | persistent | Discord / Telegram |

---

## 7.7 🧠 Maintenance Checklist

- [ ] Update all monitoring containers monthly.  
- [ ] Test alert triggers via mock failures.  
- [ ] Review logs weekly (`docker logs --tail 100`).  
- [ ] Export reports to `/srv/config/reports/`.  
- [ ] Backup Uptime Kuma and Netdata configs to Synology.  

---

## 7.8 ⚙️ Quick Command Cheat-Sheet

```bash
# View container status
docker ps --format "table {{.Names}} {{.Status}} {{.Ports}}"

# Stream Uptime Kuma logs
docker logs -f uptimekuma

# System stats via Glances CLI
glances --stdout cpu,mem,load --time 5

# Force container update
docker compose pull && docker compose up -d
```

---

✅ **End of Section 7 — Monitoring, Observability & Alerting**  
Next: **Section 8 — Automation & Self-Healing (Stack Restart + Smart Backups + Recovery)**
