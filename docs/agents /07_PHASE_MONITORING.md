# Phase 7 — Monitoring & Alerts

**Inputs**
- 07_Monitoring.md

**Success Criteria**
- Uptime Kuma online with checks for core services.
- Netdata reachable; Tautulli connected to Plex.

**Steps**
1) Deploy Uptime Kuma on whitebox; add HTTP/Ping/TCP checks from the table.
2) Deploy Netdata on redbox; confirm dashboards.
3) Deploy Tautulli; connect to Plex via token.
4) Wire Discord/Telegram notifications for critical checks.
