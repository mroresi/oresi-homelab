# ⚙️ ORESI // SYSTEMS — Section 8: Automation & Self-Healing  
**Version:** 1.0  •  **Date:** 2025-10-29  
**Applies to:** whitebox (.101), redbox (.100), bloodbox (.103), blackbox (.40)  
**Linked Systems:** Synology (NFS), Tailscale Mesh  
**Objective:** Automate updates, backups, and recovery using Watchtower, Healthcheck.io, Cron, and Proxmox hooks.

---

## 8.0 🧠 Design Intent  
Your homelab should be **predictably resilient** — not manually recoverable.  
Automation should:  
- 🔁 Restart or rebuild containers automatically.  
- ⏱️ Perform timed updates off-peak (nightly or weekly).  
- 🧩 Sync config backups to Synology.  
- 🧱 Snapshot VMs automatically on schedule.  
- 📡 Alert you when automation fails.  

---

## 8.1 🧩 Automation Architecture Overview  

```
──────────────────────────────────────────────────────────────
           ORESI // SYSTEMS — AUTOMATION STACK
──────────────────────────────────────────────────────────────
     [ whitebox (.101) ] — Primary Scheduler
       ├─ Watchtower      → Auto-update containers
       ├─ Cron Jobs       → Run daily/weekly scripts
       ├─ Healthchecks.io → Report task success/failure
       └─ Dockge          → Stack management interface

     [ redbox (.100) ] — Media Stack
       ├─ Watchtower
       └─ rsync → blackbox:/volume2/backups/docker_data

     [ bloodbox (.103) ] — AI Stack
       └─ ollama-auto-pull (nightly models refresh)

     [ blackbox (.40) ] — Synology Storage
       └─ Hyper Backup → Cloud replication
──────────────────────────────────────────────────────────────
```

---

## 8.2 🧠 Watchtower: Auto-Update Containers  

**Install on each Docker VM:**

```yaml
watchtower:
  image: containrrr/watchtower
  container_name: watchtower
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - /srv/config/watchtower:/config
  environment:
    - TZ=America/Vancouver
    - WATCHTOWER_CLEANUP=true
    - WATCHTOWER_SCHEDULE=0 0 4 * * *    # 4 AM daily
    - WATCHTOWER_NOTIFICATIONS=shoutrrr
    - WATCHTOWER_NOTIFICATION_URL=discord://<your-webhook>
  restart: unless-stopped
```

🧾 **How it works:**  
- Checks for image updates every day at 4 AM.  
- Gracefully stops → updates → restarts containers.  
- Sends report via Discord webhook.  

💡 Tip: Place Watchtower on *whitebox* and *redbox* only — let AI and Plex nodes update manually.

---

## 8.3 🕐 Cron & Healthchecks.io Integration  

### 1️⃣ Create a free account at [https://healthchecks.io](https://healthchecks.io)  
Generate UUID pings for each task (example: `https://hc-ping.com/<uuid>`)

### 2️⃣ Add Cron Jobs (via `crontab -e`)

```bash
# Daily Docker Cleanup
0 3 * * * docker system prune -af && curl -fsS -m 10 --retry 3 https://hc-ping.com/uuid-cleanup

# Weekly Backups to Synology
30 2 * * 0 rsync -avz /srv/config/ blackbox:/volume2/backups/docker_config/ && curl -fsS -m 10 --retry 3 https://hc-ping.com/uuid-backup

# Container Health Check
*/15 * * * * docker ps -a --format "{{.Names}}" | grep -v healthy && curl -fsS -m 10 --retry 3 https://hc-ping.com/uuid-alert
```

🧠 **Pro Tip:**  
Healthchecks.io will alert you via email or Discord if a job misses its expected schedule.

---

## 8.4 💾 Proxmox Backup Automation  

### 1️⃣ On whitebox (PVE host):
Create backup storage entry for Synology:
```bash
pvesm add nfs synology_backups --server 192.168.0.40 --export /volume2/backups --content backup --maxfiles 5
```

### 2️⃣ Create Scheduled Backup Job:
```bash
vzdump --quiet 1 --compress zstd --mailto admin@oresi.lan --storage synology_backups --all 1
```

Or via GUI:  
**Datacenter → Backup → Add → Node: all → Storage: synology_backups → Schedule: 3AM**

🧩 Recommended frequency:  
- Daily incremental snapshots for active VMs.  
- Weekly full backup (Sunday).  

---

## 8.5 ♻️ Smart Recovery & Rollback  

### On container crash:
```bash
docker ps -a --filter "status=exited" --format "{{.Names}}" | while read c; do
  echo "Restarting $c"
  docker restart $c
done
```

### To restore configuration:
```bash
rsync -avz blackbox:/volume2/backups/docker_config/ /srv/config/
docker compose up -d
```

---

## 8.6 🧰 Optional Tools for Power Automation  

| Tool | Purpose | Location | Notes |
|------|----------|-----------|-------|
| **Watchtower** | Auto-update containers | whitebox/redbox | Discord alerts |
| **Cron + Healthchecks.io** | Script monitoring | whitebox | Missed-job detection |
| **Proxmox vzdump** | VM backups | whitebox | ZSTD compression |
| **rsync** | Config sync | whitebox → blackbox | Daily |
| **Watchdog Script** | Self-healing Docker monitor | all nodes | Restart crashed containers |

---

## 8.7 🧠 Maintenance Checklist  
- [ ] Verify Watchtower logs weekly: `docker logs watchtower`  
- [ ] Test Healthchecks via `curl -I https://hc-ping.com/<uuid>`  
- [ ] Ensure Synology NFS is mounted before backups run.  
- [ ] Confirm vzdump job runs successfully via Proxmox mail report.  
- [ ] Sync and test backup restore once per month.  

---

## 8.8 🧾 Quick Command Cheat Sheet  
```bash
# Manually trigger Watchtower
docker exec watchtower --run-once

# Run local backup
rsync -avz /srv/config/ blackbox:/volume2/backups/docker_config/

# Check last vzdump job
grep vzdump /var/log/syslog | tail -n 10

# List failed containers
docker ps -a --filter "status=exited"
```

---

✅ **End of Section 8 — Automation & Self-Healing**  
Next: **Section 9 — Backup, Disaster Recovery & Documentation (Final Phase)**  
