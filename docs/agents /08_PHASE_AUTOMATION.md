# Phase 8 — Automation & Self-Healing

**Inputs**
- 08_Automation.md

**Success Criteria**
- Watchtower scheduled; cron jobs ping Healthchecks.io.
- Proxmox backup job exists for all VMs.

**Steps**
1) Add Watchtower service on whitebox/redbox with 4AM schedule.
2) Create cron entries for prune, rsync, and container health; add healthcheck pings.
3) Configure vzdump job (3AM, zstd, keep 5).
4) Add optional watchdog script for crashed containers.
