# ChatOps Microservice (optional)

A tiny FastAPI service that executes intents defined in `/chatops/intents/*.yaml` **only after**:
- Intent exists in `main` (auditable).
- PR was approved by Gemini and a human.
- Quality gates are green.

Secure this behind Tailscale or your proxy.
