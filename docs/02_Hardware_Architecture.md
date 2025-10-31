---
title: "ORESI // SYSTEMS — Hardware & Network Architecture"
tags: [homelab, hardware, proxmox, synology, macmini]
date: 2025-10-29
author: "ORESI"
theme: auto
---

# ⚙️ Hardware & Network Architecture

> 🧩 The backbone of your homelab — resilient, scalable, and elegant.

---

## 🗺️ Table of Contents
1. [Hardware Inventory](#hardware-inventory)
2. [Network Topology](#network-topology)
3. [Storage Infrastructure](#storage-infrastructure)
4. [Proxmox Cluster Layout](#proxmox-cluster-layout)
5. [VM Role Matrix](#vm-role-matrix)
6. [Synology Mount Strategy](#synology-mount-strategy)
7. [Maintenance Cheatsheet](#maintenance-cheatsheet)

---

## 1. 🧱 Hardware Inventory

| Device | Hostname | Role | IP | Notes |
|---------|-----------|------|----|-------|
| 🟥 Redbox | redbox | Proxmox Node (Media) | 192.168.0.100 | 6 cores, 32GB RAM |
| ⬜ Whitebox | whitebox | Proxmox Node (Core) | 192.168.0.101 | 8 cores, 64GB RAM |
| 🩸 Bloodbox | bloodbox | Proxmox Node (Compute) | 192.168.0.103 | 8 cores, 64GB RAM |
| ⚫ Blackbox | blackbox | Synology NAS | 192.168.0.40 | DS model, 59TB RAID |
| 🍏 Mac Mini M4 | m4mini | AI / LLM Node | 192.168.0.53 | M4 SoC, 16GB RAM |
| 💻 Mac Mini Intel | minibox | Utility Node | TBD | Intel i5, 8GB RAM |

---

## 2. 🌐 Network Topology

**Physical Network**
```
+-------------+          +-------------+          +-------------+
|  Whitebox   |──vmbr0──>|   Switch    |──LAN────>|  Blackbox   |
|  (Core)     |          |             |          |  Synology   |
+-------------+          +-------------+          +-------------+
       │                        │                        │
       ├────vmbr0───────────────┘                        │
       │                                                 │
+-------------+                                    +-------------+
|  Redbox     |───────────── LAN ─────────────────>|  Bloodbox   |
|  (Media)    |                                    |  (Compute)  |
+-------------+                                    +-------------+

```

**Tailscale Mesh Overlay**
```
Whitebox.ts.net <──> Redbox.ts.net <──> Bloodbox.ts.net
       │                      │                    │
       └─────── Blackbox.ts.net ──────── MacMini.ts.net
```

---

## 3. 💾 Storage Infrastructure

**NAS Export Table**
| Share | NFS Path | Purpose |
|--------|-----------|---------|
| docker_data | `/volume2/data/docker_data` | All persistent app data |
| media | `/volume2/data/media` | Movies, music, books |
| downloads | `/volume2/data/downloads` | Torrent output |
| backups | `/volume2/data/backups` | VM + config backups |

Mounted into VMs under `/srv/` or `/mnt/`:
```
/srv/
├── media/
├── downloads/
├── backups/
└── config/
```

---

## 4. 🧠 Proxmox Cluster Layout

| Node | Role | Example VM | Function |
|------|------|-------------|----------|
| Whitebox | Core | vm-infra | Dockge, Uptime Kuma, Authelia |
| Redbox | Media | vm-media | Radarr, Sonarr, Prowlarr |
| Bloodbox | Compute | vm-ai | Ollama, OpenWebUI |
| Blackbox | Storage | NFS Host | Central data & backups |
| Mac Minis | Edge | HA + Automation | Home Assistant, Zigbee2MQTT |

---

## 5. 🧩 VM Role Matrix

| VM | Purpose | Stack | Example Apps |
|----|----------|-------|---------------|
| vm-infra | Infrastructure Layer | stack-infra | Dockge, Uptime Kuma |
| vm-media | Media Services | stack-media | Radarr, Sonarr, Jellyseerr |
| vm-content | Content Tools | stack-content | DokuWiki, Ghost, Wallabag |
| vm-ai | AI Compute | stack-ai | Ollama, OpenWebUI |
| vm-smarthome | IoT Layer | stack-smarthome | Home Assistant, Zigbee2MQTT |

---

## 6. 🔗 Synology Mount Strategy

**Mount via /etc/fstab:**
```bash
sudo mkdir -p /srv/media /srv/downloads /srv/backups /srv/docker_data
sudo nano /etc/fstab
```

Add:
```
blackbox.ts.net:/volume2/data/media       /srv/media       nfs  defaults,nofail  0  0
blackbox.ts.net:/volume2/data/downloads   /srv/downloads   nfs  defaults,nofail  0  0
blackbox.ts.net:/volume2/data/backups     /srv/backups     nfs  defaults,nofail  0  0
blackbox.ts.net:/volume2/data/docker_data /srv/docker_data nfs  defaults,nofail  0  0
```

Then:
```bash
sudo mount -a && df -h | grep /srv/
```

---

## 7. 🧰 Maintenance Cheatsheet

| Task | Command | Notes |
|------|----------|-------|
| Check node health | `pvecm status` | Verify cluster sync |
| List all VMs | `qm list` | Ensure all guests visible |
| Restart cluster service | `systemctl restart pve-cluster` | Rarely needed |
| Check NAS mounts | `df -h | grep /srv/` | Verify NFS integrity |
| Update all containers | `docker compose pull && docker compose up -d` | Run inside each VM |
| Backup VMs | `vzdump <VMID> --storage synology_backups` | Weekly rotation |

---

> 💡 *All other hardware configuration builds from this foundation. Keep this file synced to Git to track hardware changes.*

---
