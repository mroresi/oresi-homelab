# ♊ ORESI Gemini Supervisor

This bundle adds an AI supervisor layer ("Gemini") that critiques changes, gates releases, probes drift, and proposes improvements — all within GitOps. Drop these folders into your repo root.

**Folders**
- `docs/policies/` — scoring rubric + guardrails used by the AI reviewer.
- `docs/prompts/` — prompts for reviewer, planner, and post-deploy analyst.
- `scripts/` — tiny helpers for metrics, drift checks, redaction, and Dockge rollout.
- `reports/` — nightly JSON/YAML outputs (kept in git as artifacts or ignored).
- `.github/workflows/` — CI gates (PR review, pre-release, post-deploy, nightly reflection).
- `chatops/` — optional FastAPI microservice to execute approved intents.

> No secrets committed. Use CI secrets for API keys and SSH.
