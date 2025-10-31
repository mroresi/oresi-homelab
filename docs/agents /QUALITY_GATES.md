# Quality Gates & Exit Criteria

**Gate A — Cluster Health**
- `pvecm status` quorum
- NFS mounted on all nodes

**Gate B — GitOps & Stacks**
- Dockge lists all stacks
- `docker compose pull && up -d` succeeds in each stack dir

**Gate C — Observability**
- All Kuma checks green 24h
- Netdata shows metric ingestion from target nodes

**Gate D — Automation**
- Watchtower logs confirm update windows
- Healthchecks.io shows all cron jobs on schedule

**Gate E — Backups**
- Last vzdump within 24h, restore tested in the last 30 days
- Offsite copy confirms last sync < 48h (if enabled)
