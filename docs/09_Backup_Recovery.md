# 🧯 ORESI // SYSTEMS — Section 9: Backup, Disaster Recovery & Documentation  
**Version:** 1.0  •  **Date:** 2025-10-29  
**Applies to:** whitebox (.101), redbox (.100), bloodbox (.103), blackbox (.40)  
**Linked Systems:** Synology DSM (NFS), Tailscale Mesh  
**Objective:** Implement reliable, redundant, and automated backup systems that ensure full recoverability of VMs, containers, and configurations within 30 minutes of catastrophic failure.  

---

## 9.0 💡 Design Intent  
You don’t have a “homelab” until you have backups that restore cleanly.  
This phase focuses on:
- 🧱 Immutable backup infrastructure (Synology + offsite).  
- 🔁 Versioned snapshots for VMs and containers.  
- 📦 GitOps documentation for reproducibility.  
- 🧰 Automation hooks for restore and validation.  
- ☁️ Optional offsite sync to cloud storage (B2 / S3 / rclone).

---

## 9.1 🧩 Backup Topology

```
──────────────────────────────────────────────────────────────
          ORESI // SYSTEMS — BACKUP & RECOVERY LAYOUT
──────────────────────────────────────────────────────────────
         [ whitebox (.101) ]
           ├─ vzdump → NFS (blackbox:/volume2/backups)
           ├─ rsync configs → blackbox:/volume2/docker_data
           ├─ Git push → github.com/oresi/homelab-configs.git
           └─ Tailscale Mesh → remote access

         [ redbox (.100) ]
           ├─ Daily media stack backup → blackbox
           ├─ qBittorrent session autosave
           └─ Restore via Dockge

         [ bloodbox (.103) ]
           ├─ Ollama model backup → Synology
           └─ restore.sh (auto-pull latest models)

         [ blackbox (.40) ]
           ├─ Synology Hyper Backup → Backblaze B2 (offsite)
           ├─ SnapReplicate docker_data hourly
           └─ Backup Integrity Monitor
──────────────────────────────────────────────────────────────
```

---

## 9.2 💾 VM Backups — Proxmox vzdump  

### 1️⃣ Create Backup Job (GUI)
**Proxmox → Datacenter → Backup → Add**
- Node: all  
- Schedule: daily @ 3AM  
- Storage: `synology_backups`  
- Mode: snapshot  
- Compression: `zstd`  
- Max backups: `5`  

### 2️⃣ Command Line (for quick check)
```bash
vzdump 101 102 103 --compress zstd --storage synology_backups --quiet 1
```

### 3️⃣ Restore Example
```bash
pct restore 101 /mnt/pve/synology_backups/dump/vzdump-lxc-101-*.tar.zst --storage local-lvm
```

---

## 9.3 📦 Container Configuration Backups  

**Synced Daily from Docker hosts to Synology:**
```bash
rsync -avz --delete /srv/config/ blackbox:/volume2/docker_data/config/
rsync -avz --delete /srv/media/ blackbox:/volume2/docker_data/media/
```

Schedule with `cron`:
```bash
0 2 * * * /usr/bin/rsync -avz /srv/config/ blackbox:/volume2/docker_data/config/
```

💡 *Tip:* Use Healthchecks.io to track if the rsync job stops unexpectedly.

---

## 9.4 🗃️ GitOps Configuration Backups  

### 1️⃣ Version your docker-compose structure:
```bash
cd /opt/stacks
git add .
git commit -m "Automated update - $(date +%F)"
git push origin main
```

### 2️⃣ Create `.env.template` for sensitive variables  
Never push credentials — store them separately in your **Vault or iCloud Secure Notes**.

---

## 9.5 ☁️ Offsite Backups (Optional but Recommended)

### Option A — Synology Hyper Backup to Backblaze B2
- Package Center → Install **Hyper Backup**  
- Source: `/volume2/backups`  
- Destination: Backblaze B2  
- Schedule: nightly at 3:30 AM  
- Retention Policy: Smart versioning (30 days)  

### Option B — rclone on Proxmox
```bash
rclone sync /mnt/pve/synology_backups b2:oresi-backups --progress --transfers=8
```

📦 **Alternative Destinations:**  
Dropbox, Google Drive, or another remote Synology NAS.

---

## 9.6 🧰 Restore Procedures

| Scenario | Action | Estimated Recovery Time |
|-----------|---------|------------------------|
| Lost container configs | `rsync -avz blackbox:/volume2/docker_data/config/ /srv/config/` | 5 min |
| Corrupted Docker volume | `docker compose down && docker compose up -d` | 2 min |
| VM corruption | `pct restore` from Synology NFS | 10–15 min |
| Synology failure | Hyper Backup → Backblaze restore | 30–60 min |
| Total network failure | Rejoin nodes via Tailscale MagicDNS | 10 min |

---

## 9.7 🧠 Disaster Simulation Checklist  
- [ ] Unplug Synology for 10 minutes — ensure local cache continues running.  
- [ ] Simulate full VM restore from vzdump file.  
- [ ] Test a manual `rsync` restore for `/srv/config/`.  
- [ ] Validate offsite recovery from B2 using rclone.  
- [ ] Verify Tailscale access persists post-reboot.  

---

## 9.8 📘 Documentation & Runbook  

**Every system change → document it.**  
Keep your operational history versioned alongside your Docker configs.

🗂️ Suggested structure for your Obsidian vault:
```
ORESI_HOMELAB/
├── 01_Vision_Overview.md
├── 02_Hardware_Architecture.md
├── 03_Networking_Tailscale.md
├── 04_Virtualization_Proxmox.md
├── 05_Storage_NFS.md
├── 06_Deployment_Docker.md
├── 07_Monitoring.md
├── 08_Automation.md
└── 09_Backup_Recovery.md
```

---

## 9.9 🧾 Quick Command Cheat-Sheet  
```bash
# Check vzdump job results
grep vzdump /var/log/syslog | tail -n 10

# Restore container config
rsync -avz blackbox:/volume2/docker_data/config/ /srv/config/

# Test remote backup sync
rclone check /mnt/pve/synology_backups b2:oresi-backups

# Verify tail-scale connectivity
tailscale status
```

---

✅ **End of Section 9 — Backup, Disaster Recovery & Documentation**  
**ORESI // SYSTEMS — PHASE I COMPLETE**  
> Your homelab is now: monitored, automated, and self-restoring.  
> From this point onward — you’re running an enterprise-grade system, built to survive chaos.
