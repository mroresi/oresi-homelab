# Phase 9 — Backup & Disaster Recovery

**Inputs**
- 09_Backup_Recovery.md

**Success Criteria**
- Nightly VM backups to Synology.
- Daily rsync of /srv/config to Synology docker_data.
- Successful restore simulation logs.

**Steps**
1) Confirm Proxmox job: snapshot @ 3AM, storage synology_backups.
2) Cron rsync jobs for /srv/config (and media if required).
3) Enable Hyper Backup → Backblaze B2 (optional) or rclone job.
4) Run monthly disaster simulation checklist and record outcomes.
