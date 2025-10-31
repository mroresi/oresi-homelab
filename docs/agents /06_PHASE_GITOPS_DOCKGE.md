# Phase 6 — GitOps & Dockge

**Inputs**
- 06_GitOps_Workflow.md

**Success Criteria**
- `/opt/stacks` cloned from repo on each Docker VM.
- Dockge reachable at http://whitebox:5001 and sees all stacks.

**Steps**
1) On each VM: create `/opt/stacks`, clone repo.
2) Optional cron: hourly `git pull`.
3) Deploy Dockge from `stack-infra/docker-compose.yml` and bring it up.
4) Place compose files for each stack and test `docker compose up -d`.
