# AI Agents for Infrastructure

This directory contains **agent-executable documentation** for the ORESI homelab. Each phase is a structured playbook that can be run by humans or AI agents with tool access.

## Philosophy

- **Documentation as Executable Workflow**: Every operational step is markdown with validation gates.
- **Sequential Phases**: Each phase depends on the previous; agents stop if gates fail.
- **Auditable & Reproducible**: All changes go through Git; no manual edits to live systems.
- **Human-Readable, Agent-Parsable**: Markdown is both a handbook and a runbook.

## Phase Structure

Each phase file follows this pattern:

1. **Objective**: What this phase achieves
2. **Prerequisites**: Previous phases and validation checks
3. **Steps**: Ordered tasks with exact commands
4. **Validation**: Tests to confirm success before proceeding
5. **Rollback**: Recovery steps if validation fails

## Available Phases

| Phase | File | Purpose | Status |
|-------|------|---------|--------|
| 0 | `00_SYSTEM_PROMPT.md` | Agent system message and context | Planned |
| 1 | `01_PHASE_VISION.md` | Define goals and architecture | Planned |
| 2 | `02_PHASE_HARDWARE_NETWORK.md` | Document hardware and network topology | Planned |
| 3 | `03_PHASE_TAILSCALE.md` | Set up Tailscale mesh VPN | Planned |
| 4 | `04_PHASE_PROXMOX_CLUSTER.md` | Configure Proxmox cluster | Planned |
| 5 | `05_PHASE_VM_TEMPLATES.md` | Create reusable VM templates | Planned |
| 6 | `06_PHASE_GITOPS_DOCKGE.md` | Deploy GitOps with Dockge | Planned |
| 7 | `07_PHASE_MONITORING.md` | Set up observability stack | Planned |
| 8 | `08_PHASE_AUTOMATION.md` | Implement automation and self-healing | Planned |
| 9 | `09_PHASE_BACKUP_DR.md` | Configure backup and disaster recovery | Planned |

## Quality Gates

Before advancing to the next phase, agents must validate:

- All commands executed successfully (exit code 0)
- Health checks return green
- Documentation updated with actual values
- Git commit with descriptive message

See `QUALITY_GATES.md` for detailed criteria.

## Tools Reference

Agents have access to:
- Shell execution (via safe allowlisted commands)
- File read/write (with protection for sensitive paths)
- Git operations (commit, tag, push)
- API calls (Proxmox, Docker, Tailscale)

See `TOOLS_REFERENCE.md` for capabilities and constraints.

## Usage

**For Humans**:
```bash
# Read phases in order
cat docs/agents/01_PHASE_VISION.md
# Execute commands manually
# Validate before moving to next phase
```

**For AI Agents**:
```
SYSTEM_PROMPT = load("docs/agents/00_SYSTEM_PROMPT.md")
for phase in [01..09]:
    execute_phase(phase)
    if not validate():
        halt_and_report()
```

## Contributing

- Phases should be deterministic and idempotent
- Use exact commands (no placeholders like `<your-value-here>`)
- Include rollback steps for destructive operations
- Validation must be automatable (no "check manually")

## References

- Core documentation: `/docs/01_Vision_Overview.md` through `/docs/09_Backup_Recovery.md`
- Policies: `/docs/policies/guardrails.md`, `/docs/policies/rubric.md`
- Checklists: `/STACK_*_CHECKLIST.md`

---

**Status**: Infrastructure in progress. Phases will be created as the homelab evolves.
