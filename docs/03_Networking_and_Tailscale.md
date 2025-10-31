---
title: "ORESI // SYSTEMS — Networking & Tailscale Configuration"
tags: [homelab, networking, tailscale, proxmox, synology, macmini]
date: 2025-10-29
author: "ORESI"
theme: auto
---

# 🌐 Networking & Tailscale Configuration

> ⚙️ The backbone of **secure, zero-trust networking** for your homelab — connecting every node seamlessly through encrypted peer-to-peer links.

---

## 🗺️ Table of Contents

1. [Overview](#1-overview)
2. [Network Design](#2-network-design)
3. [Installation Steps](#3-installation-steps)
4. [Advanced Configuration](#4-advanced-configuration)
5. [Verification & Troubleshooting](#5-verification--troubleshooting)
6. [Cheatsheet](#6-cheatsheet)

---

## 1. 🌍 Overview

**Tailscale** is the secure overlay network connecting all your nodes across Proxmox, Synology, and macOS.  
It provides:

- 🔒 **Zero-trust mesh VPN** (WireGuard-based)  
- 🧭 **MagicDNS** for easy hostname resolution  
- 🌉 **Subnet routing** for exposing internal LANs  
- 🚪 **Exit nodes** for remote access to your network  
- 💡 **Auto-authentication** via reusable auth keys

### Architecture Diagram

```
                     ┌────────────────────────────────┐
                     │        Tailscale Mesh VPN       │
                     └────────────────────────────────┘
                       │              │             │
     ┌─────────────────┘              │             └──────────────────┐
     ▼                                ▼                                ▼
┌────────────┐               ┌────────────┐                 ┌────────────┐
│  whitebox  │──────────────▶│  redbox    │◀───────────────▶│  bloodbox  │
│  192.168.0.101 │           │  192.168.0.100 │             │  192.168.0.103 │
└────────────┘               └────────────┘                 └────────────┘
       │                             │                               │
       ▼                             ▼                               ▼
   ┌───────────┐              ┌────────────┐                  ┌────────────┐
   │ blackbox  │              │ mac mini M4│                  │ mac mini intel │
   │ 192.168.0.40│            │ 192.168.0.53│                 │ TBD            │
   └───────────┘              └────────────┘                  └────────────┘
```

---

## 2. 🧩 Network Design

| Node | Role | LAN IP | Tailscale Name | Notes |
|------|------|--------|----------------|-------|
| 🟥 **redbox** | Media Host (Proxmox) | 192.168.0.100 | redbox.ts.net | Advertises 192.168.0.0/24 |
| ⬜ **whitebox** | Core Host (Proxmox) | 192.168.0.101 | whitebox.ts.net | Cluster leader |
| 🩸 **bloodbox** | Compute Host | 192.168.0.103 | bloodbox.ts.net | AI and GPU workloads |
| ⚫ **blackbox** | Synology NAS | 192.168.0.40 | blackbox.ts.net | Data + NFS shares |
| 🍏 **Mac Mini M4** | AI Assistant | 192.168.0.53 | macmini.ts.net | Ollama + OpenWebUI |
| 💻 **Mac Mini Intel** | Utility | TBD | minibox.ts.net | Zigbee / Home Assistant |

---

## 3. ⚙️ Installation Steps

### 🧠 Phase 1 — Create Auth Key
From [https://login.tailscale.com/admin/settings/keys](https://login.tailscale.com/admin/settings/keys):

```bash
# Generate a reusable server auth key
tskey-auth-XXXXXXXXXXXXXX
```

> 📝 Use this key for headless installs (Proxmox, Docker VMs, Synology).

---

### 🟥 Proxmox Nodes (redbox, whitebox, bloodbox)

```bash
apt update && apt install -y tailscale
systemctl enable --now tailscaled

# Authenticate & advertise local subnet
tailscale up --auth-key=tskey-auth-XXXXXXXXXXXXXX   --hostname=$(hostname)   --advertise-exit-node   --advertise-routes=192.168.0.0/24   --ssh
```

> ✅ Repeat on each node with its hostname.

---

### ⚫ Synology (blackbox)

**Option 1: Synology Package Center**
1. Search for **Tailscale** → Install.
2. Login via browser popup.
3. In the Tailscale admin panel, mark it as a **subnet router**.

**Option 2: Docker**
```bash
docker run -d --name=tailscale   --net=host   --privileged   -v /var/lib/tailscale:/var/lib/tailscale   tailscale/tailscale tailscaled
```

---

### 🍏 Mac Mini (M4 & Intel)
#### macOS GUI:
1. Install from [https://tailscale.com/download](https://tailscale.com/download)
2. Login with your account.
3. Enable **“Allow LAN access”** and **“Use as Exit Node”** if desired.

#### macOS CLI:
```bash
sudo tailscale up --ssh --accept-routes
```

---

### 🐳 Docker Containers (inside VMs)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscaled &
tailscale up --auth-key=tskey-auth-XXXXXXXXXXXXXX --ssh --hostname=$(hostname)
```

---

## 4. 🧠 Advanced Configuration

### 🔮 MagicDNS
In **Tailscale Admin → DNS → MagicDNS**, enable:
- ✅ MagicDNS
- ✅ Split DNS for local domains

Then you can resolve nodes like:
```
ping redbox.ts.net
ping blackbox.ts.net
```

---

### 🌉 Subnet Routing

Enable routing from redbox to your internal network:
```bash
tailscale up --advertise-routes=192.168.0.0/24 --accept-dns=false
```

Approve in the admin console:
> ✅ *Machines → redbox → Routes → Approve 192.168.0.0/24*

---

### 🚪 Exit Node (for remote access)

Designate redbox as the exit node:
```bash
tailscale up --advertise-exit-node --ssh
```

From your laptop or Mac Mini:
```bash
tailscale set --exit-node=redbox.ts.net --exit-node-allow-lan-access=true
```

---

### 🔐 Access Control Lists (ACLs)

Example policy snippet (`tailscale.json`):
```json
{
  "acls": [
    { "action": "accept", "src": ["user:oresi"], "dst": ["*:*"] }
  ],
  "tagOwners": {
    "tag:proxmox": ["user:oresi"]
  }
}
```

Upload via [Tailscale Admin → Access Controls](https://login.tailscale.com/admin/acls).

---

## 5. 🧰 Verification & Troubleshooting

### Check Status
```bash
tailscale status
tailscale ip
tailscale ping <hostname>
```

### Restart Service
```bash
systemctl restart tailscaled
```

### Logs
```bash
journalctl -u tailscaled -n 100 --no-pager
```

### Re-authenticate
```bash
tailscale up --reset
```

### Common Fixes
| Problem | Fix |
|----------|-----|
| “Permission denied” on routes | Re-authenticate with `sudo tailscale up --advertise-routes` |
| Machine missing in dashboard | Restart `tailscaled` service |
| Exit node unreachable | Disable “Allow LAN access” toggle on client |

---

## 6. 📜 Cheatsheet

| Task | Command |
|------|----------|
| Install on Linux | `curl -fsSL https://tailscale.com/install.sh | sh` |
| Start service | `systemctl enable --now tailscaled` |
| Connect node | `tailscale up --auth-key=<key> --ssh` |
| List peers | `tailscale status` |
| Ping peer | `tailscale ping redbox.ts.net` |
| Exit node enable | `tailscale up --advertise-exit-node` |
| Subnet routing | `tailscale up --advertise-routes=192.168.0.0/24` |
| Reset connection | `tailscale logout && tailscale up --reset` |
| Show MagicDNS | `tailscale netcheck` |

---

> 💡 *At this point, your entire ORESI network is now unified, encrypted, and remotely accessible via Tailscale’s global mesh. The next phase: container orchestration.*

---
