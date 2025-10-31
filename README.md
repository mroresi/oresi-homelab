# 🧠 ORESI Homelab

Welcome to the ORESI Homelab — a fully documented, GitOps-driven environment for self-hosted infrastructure, automation, and observability.

This repository is structured to serve both **humans** and **AI agents**.  
Humans use it as a technical handbook; agents use it as an executable runbook that enforces sequence, validation, and reproducibility.

## Repository Structure

```
/docs/
  01_Vision_Overview.md
  02_Hardware_Architecture.md
  03_Networking_and_Tailscale.md
  04_Proxmox_Cluster.md
  05_VM_Templates.md
  06_GitOps_Workflow.md
  07_Monitoring.md
  08_Automation.md
  09_Backup_Recovery.md
  /agents/
    (AI operational files)
```
## Philosophy

**Infrastructure as Documentation** — every operational action, from provisioning to backup, exists as markdown.  
**GitOps First** — if it’s not in git, it doesn’t exist.  
**Reproducibility over improvisation** — identical builds anywhere, anytime.  
**Observability & Resilience** — no black boxes, no silent failures.

## For Humans
Follow `/docs/agents/` phases manually or with automation. Each file contains ordered steps with validation gates.

## For AI Agents
Use `docs/agents/00_SYSTEM_PROMPT.md` as your system message.  
Run the numbered phases sequentially, referencing the core docs for inputs. Stop on missing data — never invent.

## Quickstart

```bash
git clone https://github.com/<your-org>/oresi-homelab.git
cd oresi-homelab/docs/agents
cat 01_PHASE_VISION.md
```
or for agents:

```
SYSTEM_PROMPT = contents of 00_SYSTEM_PROMPT.md
```

## License
All documentation © ORESI Homelab contributors — usable for education or personal infra.

*"Every reliable system starts as a well-written markdown file."*
