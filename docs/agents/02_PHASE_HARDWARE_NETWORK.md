# Phase 2 — Hardware & Network Baseline

**Inputs**
- 02_Hardware_Architecture.md

**Success Criteria**
- Nodes reachable by IP and hostname.
- NFS shares mounted at /srv/* on target VMs.

**Steps**
1) Verify inventory and IPs match the table.
2) On VMs: `sudo mkdir -p /srv/{media,downloads,backups,docker_data}`
3) Add NFS entries to `/etc/fstab` per docs and `mount -a`.
4) Record `df -h | grep /srv/` output in logs.
