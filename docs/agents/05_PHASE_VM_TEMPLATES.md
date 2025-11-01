# Phase 5 — VM Templates & Role Clones

**Inputs**
- 05_VM_Templates.md

**Success Criteria**
- Template 9000 created and converted.
- Role VMs running with NFS mounts and Tailscale.

**Steps**
1) Download Ubuntu 24.04 ISO on whitebox.
2) Create VM 9000 with qemu-guest-agent; install minimal server + SSH.
3) Install `nfs-common`, `tailscale`, `qemu-guest-agent`; enable services.
4) `qm template 9000`.
5) Clone VMs (e.g., `vm-infra`, `vm-media`, `vm-ai`) with IPs.
6) Run `/root/init_base.sh` to install docker, compose, NFS mounts and Tailscale join.
