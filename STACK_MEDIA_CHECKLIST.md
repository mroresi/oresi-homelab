# Stack Checklist — Media

**Purpose**
Manage Plex, Sonarr, Radarr, Prowlarr, and Transmission stacks.

**Pre-deploy Checks**
- NFS mounts for `/srv/media` and `/srv/downloads` available.
- PUID/PGID match `mediauser`.
- Compose `.env` present and correct.

**Post-deploy Validation**
- Plex accessible on :32400
- Sonarr/Radarr connected to indexers and download client.
- Permissions on `/srv/media` verified via test file.

**Maintenance**
- Weekly container updates through Watchtower.
- Verify DB backups stored in `/srv/backups/media/`.
- Add Uptime Kuma check for Plex port 32400
