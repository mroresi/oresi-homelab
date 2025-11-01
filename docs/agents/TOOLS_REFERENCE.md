# Tools & Commands Reference

- Docker:
  - `docker compose up -d`
  - `docker compose logs --tail 100 -f`
  - `docker exec watchtower --run-once`

- Proxmox:
  - `pvecm status`, `qm clone`, `vzdump`

- Tailscale:
  - `tailscale status`, `tailscale up`, `tailscale ping`

- NFS:
  - `/etc/fstab` entries per docs; `mount -a`, `df -h | grep /srv/`
