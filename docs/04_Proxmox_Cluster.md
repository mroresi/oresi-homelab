# ORESI // SYSTEMS — Section 4: Proxmox Cluster (whitebox / redbox / bloodbox)
**Version:** 1.0 • **Date:** 2025-10-29 • **Style:** Professional manual (NA Letter/“C”) • **Brand:** ORESI // SYSTEMS  
**Goal:** Build a stable 3-node Proxmox VE cluster backed by Synology (blackbox) NFS, reachable everywhere via Tailscale.

---

## 4.0 Topology (ASCII)

```
ORESI // SYSTEMS
───────────────────────────────────────────────────────────────────────────────
           🧠 Proxmox Cluster Architecture (3 nodes)
───────────────────────────────────────────────────────────────────────────────

                     ┌──────────────────────────────┐
                     │        Tailscale VPN         │
                     │     (MagicDNS + ACLs)        │
                     └──────────────────────────────┘
                                    │
          ┌───────────────────────────────────────────────────────────────┐
          │                      Local Network (192.168.0.0/24)           │
          └───────────────────────────────────────────────────────────────┘
                │             │               │                │
        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
        │  whitebox   │ │   redbox    │ │  bloodbox   │ │  blackbox   │
        │ Proxmox Node│ │ Proxmox Node│ │ Proxmox Node│ │ Synology NAS│
        │  .101       │ │  .100       │ │  .103       │ │  .40        │
        └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 4.1 Cluster Overview
This document defines the deployment standard for your **Proxmox VE cluster**, including node naming, network layout, and connectivity strategy.

**Cluster Name:** `oresi-cluster`  
**Primary Storage:** `blackbox:/volume2/data/docker_data` (NFS)  
**Nodes:**
- 🧱 **whitebox (192.168.0.101)** — Compute / Core infra
- 🔥 **redbox (192.168.0.100)** — Media / Download stack
- 💉 **bloodbox (192.168.0.103)** — Experimental / AI workloads
- 🗄️ **blackbox (192.168.0.40)** — Synology NAS (NFS, SMB, Tailscale)

---

## 4.2 Cluster Setup Steps (Command Sequence)

### Step 1 — Prepare Network
```bash
# On each node:
ip a show
hostnamectl set-hostname whitebox   # adjust for each node
echo "192.168.0.40 blackbox" >> /etc/hosts
echo "192.168.0.100 redbox" >> /etc/hosts
echo "192.168.0.101 whitebox" >> /etc/hosts
echo "192.168.0.103 bloodbox" >> /etc/hosts
```

### Step 2 — Install Tailscale
```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --authkey <your_auth_key> --hostname=$(hostname)
tailscale ip -4
```

### Step 3 — Create Cluster
```bash
# On whitebox (master)
pvecm create oresi-cluster

# On redbox + bloodbox
pvecm add 192.168.0.101
```

### Step 4 — Verify
```bash
pvecm status
pvecm nodes
```

---

## 4.3 Add Synology NFS Storage
```bash
# On each node
mkdir -p /mnt/blackbox_nfs
echo "192.168.0.40:/volume2/data/docker_data /mnt/blackbox_nfs nfs defaults 0 0" >> /etc/fstab
mount -a
df -h | grep blackbox
```

---

## 4.4 Health Monitoring (Proxmox Shell)
```bash
pveperf
systemctl status pve-cluster
tail -f /var/log/syslog | grep pve
```

✅ **At this stage:** Cluster nodes communicate, Tailscale provides remote access, and NFS shares are persistent.

**Next Step:** Proceed to Section 5 — VM Templates and Role-based Deployment.
