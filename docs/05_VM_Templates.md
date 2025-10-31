# ORESI // SYSTEMS — Section 5: VM Templates & Role-Based Deployment
**Version:** 1.0 • **Date:** 2025-10-29  
**Applies to:** whitebox (.101), redbox (.100), bloodbox (.103)  
**Linked System:** blackbox (Synology .40 — NFS storage)  
**Objective:** Create reusable Proxmox templates for consistent VM rollout — optimized for performance, backups, and automation.

---

## 5.0 🎯 Design Intent

Templates should:
- Deploy in <30 seconds.  
- Auto-connect to Synology NFS and Tailscale.  
- Use consistent file systems, naming, and users.  
- Be **immutable** (convert to template) and cloned for roles.

**Template Base:** `Ubuntu Server 24.04 LTS (cloud-init ready)`  
**Naming Convention:**  
`vm-[role]-[node]-[purpose]` → e.g., `vm-media-redbox-docker`  
**Network Mode:** `virtio, bridge=vmbr0`  
**Storage:** ZFS-backed (`zmedia`)  
**Management Tools:** Tailscale + qemu-guest-agent + nfs-common

---

## 5.1 🧱 Create Base Template VM

### Step 1 — Download ISO
```bash
# On whitebox
cd /var/lib/vz/template/iso
wget https://cdimage.ubuntu.com/releases/24.04/release/ubuntu-24.04-live-server-amd64.iso
```

### Step 2 — Create the VM
```bash
qm create 9000   --name ubuntu-template   --memory 4096   --cores 2   --net0 virtio,bridge=vmbr0   --scsihw virtio-scsi-pci   --sata0 zmedia:32   --cdrom local:iso/ubuntu-24.04-live-server-amd64.iso   --boot c --bootdisk sata0   --agent 1
```

### Step 3 — Install Ubuntu  
- Choose **Minimal Installation**  
- Enable **OpenSSH Server**  
- Create user: `oresi`  
- Auto-login disabled  
- Hostname: `template-ubuntu`

### Step 4 — Prepare Post-Install Tools
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y qemu-guest-agent nfs-common tailscale curl
sudo systemctl enable qemu-guest-agent
```

### Step 5 — Convert to Template
```bash
qm shutdown 9000
qm template 9000
```

---

## 5.2 ⚙️ Deploy Role-Based VMs

| Role | Node | Purpose | Resources | Notes |
|------|------|----------|------------|--------|
| vm-infra | whitebox | Dockge / Uptime Kuma / Guacamole | 4C / 8GB | Core infra |
| vm-media | redbox | Sonarr / Radarr / Jellyseerr / qBittorrent | 6C / 12GB | Media stack |
| vm-content | bloodbox | ArchiveBox / DokuWiki / Firefly III | 4C / 8GB | Content management |
| vm-ai | bloodbox | Ollama / OpenWebUI / Meilisearch | 8C / 16GB | AI workloads |
| vm-smarthome | redbox | Home Assistant / Zigbee2MQTT | 4C / 8GB | Smart home automation |

### Clone from Template
```bash
# Example: create vm-media on redbox
qm clone 9000 200 --name vm-media-redbox --full true --target redbox
qm set 200 --ipconfig0 ip=192.168.0.120/24,gw=192.168.0.1
qm start 200
```

---

## 5.3 🧩 Base Configuration Script (cloud-init or manual)

```bash
#!/bin/bash
# Base setup for cloned VMs
sudo apt update && sudo apt install -y docker.io docker-compose git nfs-common tailscale
sudo systemctl enable docker

# Mount NFS shares
sudo mkdir -p /srv/{media,downloads,config}
echo "192.168.0.40:/volume2/data/media /srv/media nfs defaults,nofail 0 0" | sudo tee -a /etc/fstab
echo "192.168.0.40:/volume2/data/downloads /srv/downloads nfs defaults,nofail 0 0" | sudo tee -a /etc/fstab
sudo mount -a

# Tailscale
sudo tailscale up --authkey tskey-auth-XXXX --hostname $(hostname)
```

Save as `/root/init_base.sh` and run after cloning.

---

## 5.4 🧠 Visual Deployment Map (ASCII)

```
ORESI // SYSTEMS — VM Deployment
──────────────────────────────────────────────────────────────
                   [ whitebox (.101) ]
                   ├── vm-infra
                   │     ├─ dockge
                   │     ├─ uptimekuma
                   │     └─ guacamole
                   │
                   [ redbox (.100) ]
                   ├── vm-media
                   │     ├─ sonarr
                   │     ├─ radarr
                   │     ├─ qbittorrent
                   │     └─ jellyseerr
                   │
                   [ bloodbox (.103) ]
                   ├── vm-content
                   │     ├─ fireflyIII
                   │     ├─ dokuwiki
                   │     └─ archivebox
                   ├── vm-ai
                   │     ├─ ollama
                   │     └─ openwebui
                   │
                   [ synology blackbox (.40) ]
                   └── NFS + Backup Hub
```

---

## 5.5 🛠️ Maintenance & Versioning
- Convert all modified VMs → new template version (`9001`, `9002`, etc.)
- Maintain a changelog `/mnt/docker_data/docs/templates.log`
- Periodically verify cloud-init + network config:
  ```bash
  qm cloudinit dump 200
  ```

---

✅ **End of Section 5**  
Next: **Section 6 — GitOps Workflow (Configuration & Dockge Management)**
