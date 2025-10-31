# ORESI Homelab — Project Analysis Report (2025-10-30)

### Summary

Your repository is a clean, GitOps-oriented homelab handbook with strong documentation and useful operational scripts. The ChatOps microservice is a promising bridge from "docs as code" to "actions," but currently lacks critical security hardening and test/CI scaffolding. With a few targeted upgrades (authN/authZ, command allowlisting, dependency pinning, and CI), you'll have a safe and reproducible automation surface.

### What I reviewed

- Repo docs: `README.md`, `RELEASE_PROCESS.md`, stack checklists (AI/Content/Media), Monitoring (Section 7), Automation (Section 8)
- ChatOps service: `chatops/main.py`, `chatops/requirements.txt`, `chatops/intents/scale_stack.yaml`, `chatops/README.md`
- Operational scripts: `scripts/collect_metrics.sh`, `scripts/dockge_rollout.sh`, `scripts/drift_probe.sh`, `scripts/redact_env.py`
- Policies: `docs/policies/guardrails.md`, `docs/policies/rubric.md`

---

## Strengths

- Documentation-first design with clear GitOps workflows and post-release validation steps
- Practical stack checklists per domain (AI, Content, Media) with pre/post checks and maintenance
- Monitoring and automation guidance (Uptime Kuma, Netdata, Watchtower, Healthchecks.io, Proxmox) is detailed and actionable
- Useful operational scripts: metrics, rollout, drift detection, and environment redaction
- ChatOps "intent" pattern aligns with auditable infrastructure actions

## Gaps and Risks

1) ChatOps API surface — security and safety
   - No authentication or network restriction at the API level (docs say "secure behind Tailscale/proxy" but not enforced)
   - Executes YAML-provided shell commands with `shell=True` and unbounded input; no allowlist, no working-dir sandbox, no user/namespace isolation
   - Label check is shallow: compares a string instead of validating an approved label state from source control or a PR system
   - No logging/observability, rate limits, or audit trail (who/when/what)

2) Reliability engineering
   - No unit tests or integration tests; no health endpoint for the FastAPI app
   - No CI pipeline to run lint/type/test gates on PRs; no pre-commit hooks
   - Dependencies are unpinned; potential for drift and supply-chain risk

3) Reproducibility and packaging
   - No Dockerfile for `chatops/`; unclear deployment method
   - No typed contract for intents (schema validation, versioning, backward compatibility)

4) Policy alignment gaps
   - Guardrails recommend redaction and human approval, but ChatOps doesn't enforce: redaction at boundary, multi-party approval, or "doc update required" checks

## Quality gates (quick triage)

- Build: N/A (no build artifacts) → Status: FAIL (missing Dockerfile/package build for ChatOps)
- Lint/Typecheck: Not configured → Status: FAIL (no flake8/ruff/mypy in CI)
- Tests: None present → Status: FAIL (no pytest and no tests)

Recommendation: Add a minimal CI that lint-checks, type-checks, and runs one unit test within a day.

## Prioritized Recommendations (7–10 day plan)

Day 1–2: Secure and stabilize ChatOps

- Add HTTP auth (at minimum an `X-API-Key` header checked against an environment variable) and document reverse proxy/Tailscale requirement
- Replace `subprocess.run(..., shell=True)` with argv list and a strict allowlist of command templates (e.g., only docker compose invocations for known stacks)
- Validate intents via Pydantic schema (name, label_required, command enum or structured parameters)
- Add structured logging (JSON) with request-id and caller IP; include audit log of executed intent

Day 3–4: Reproducible packaging and dependencies

- Create `chatops/Dockerfile` and pin dependencies in `requirements.txt` (or `requirements.lock`)
- Add a `HEALTHCHECK` route (`/healthz`) and readiness endpoint

Day 5–6: Testing and CI

- Introduce `pytest` with minimal tests: intent load success, auth enforcement, allowlist rejection, happy-path command mock
- Add a GitHub Actions workflow running: ruff/flake8, mypy (if you add types), pytest on Python 3.12

Day 7+: Policy & docs parity

- Update `chatops/README.md` with runbook, auth model, and example intents
- Wire logs/alerts to Uptime Kuma/Discord for failure notifications
- Add a simple scorecard using `docs/policies/rubric.md` on PRs (manual or automated comment)

## Concrete To-Do’s

- Security
  - [ ] Add API key auth to FastAPI and optional IP allowlist
  - [ ] Replace shell execution with allowlisted argv form; drop `shell=True`
  - [ ] Emit structured audit logs and correlate to intent name + requester

- Reliability
  - [ ] Add `/healthz` GET endpoint returning app status
  - [ ] Pin dependencies (e.g., `fastapi==0.115.*`, `pydantic==2.9.*`, `pyyaml==6.0.*`, `uvicorn[standard]==0.32.*`)
  - [ ] Add `pytest`, one happy-path and two failure-path tests

- CI & Packaging
  - [ ] Add `Dockerfile` for ChatOps with non-root user and `uvicorn` supervisor
  - [ ] Add `.github/workflows/ci.yml` to lint, type-check, and test on PRs to `main`

- Documentation
  - [ ] Expand `chatops/README.md` (auth, intents schema, deployment)
  - [ ] Reference guardrails explicitly and link to the rubric in PR template

## Observations by file

- `chatops/main.py`
  - Uses FastAPI and Pydantic; direct YAML load + shell command execution; no auth; no logs; minimal error handling
  - Risk: remote code execution if exposed; even internal exposure is risky without allowlist

- `chatops/requirements.txt`
  - No version pins; recommend pinning and adding `uvicorn[standard]`, `python-dotenv` (optional), `pytest`, `ruff`/`flake8`, and `mypy` if you add types

- `chatops/intents/scale_stack.yaml`
  - Demonstrates the pattern; prefer structured schema (e.g., `action: scale`, `service: plex`, `replicas: 2`, `stack: stack-media`), then assemble the argv in code

- `scripts/collect_metrics.sh`
  - Portable and safe; uses `jq` to emit JSON; good macOS/Linux fallback for CPU count

- `scripts/dockge_rollout.sh`
  - Simple and useful; consider logging and optional `--no-pull`/`--dry-run` flags

- `scripts/drift_probe.sh`
  - Useful heuristic; consider also checking for unpinned digests and mismatches with compose files

- `scripts/redact_env.py`
  - Handy redactor; extend the safe key list or load from a policy file; add unit tests

- `RELEASE_PROCESS.md`
  - Clear steps; consider adding a rollback tag strategy and automated Dockge sync via webhook/CI

## Suggested Artifacts to Add (non-breaking)

- chatops/Dockerfile (multi-stage, non-root, pinned base)
- .github/workflows/ci.yml (ruff/flake8, mypy, pytest on Python 3.12)
- chatops/tests/test_run_intent.py (auth required, allowlist enforced, happy path)
- chatops/intent_schema.py (Pydantic model for intent files)
- chatops/logging.json (or code-based JSON logging config)

## Try it (optional)

When the above changes are in, you'll be able to:

- Run ChatOps locally in Docker
- Hit `/healthz` for k8s/Docker health checks
- Submit a validated intent and see structured logs in stdout and your log collector

## Final word

You've got strong documentation and practical ops scripts. By shoring up the ChatOps surface and adding a tiny CI/testing backbone, you'll reach a safe, auditable, and repeatable automation loop that matches your GitOps philosophy.
