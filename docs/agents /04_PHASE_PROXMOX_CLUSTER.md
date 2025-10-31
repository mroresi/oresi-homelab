# Phase 4 — Proxmox Cluster

**Inputs**
- 04_Proxmox_Cluster.md

**Success Criteria**
- `pvecm status` healthy; nodes joined.
- Synology NFS storage mounted on each host.

**Steps**
1) Set hostnames and /etc/hosts entries.
2) `pvecm create oresi-cluster` (whitebox); `pvecm add 192.168.0.101` (others).
3) Add NFS storage line to `/etc/fstab`; `mount -a`.
4) Verify with `df -h | grep blackbox`.
