# Review Rubric (Score 0–5 per category)

- Security: secrets handling, least privilege, image provenance.
- Reproducibility: pinned versions, idempotence, deterministic steps.
- Observability: Kuma checks, logs, alerts wired to Discord/Telegram.
- Backup/DR: snapshot schedule, offsite sync, restore test updated.
- Networking: ports, TLS, MagicDNS/Tailscale routes.
- Data Safety: NFS mounts, permissions, migration steps.
- Rollback: clear procedure tied to the change.
- Docs Parity: core docs + agents updated.

**Scoring**
0=missing, 1=poor, 2=fair, 3=adequate, 4=good, 5=excellent.
Overall score = average * 20. Block if any category ≤1 or overall < 80.
