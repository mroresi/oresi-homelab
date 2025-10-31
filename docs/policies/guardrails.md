# Guardrails

- Never invent credentials or IPs; ask for missing inputs via PR comment.
- Redact `.env` values before sending to AI.
- Large logs -> aggregate counts; no raw PII.
- Human approval required even if AI approves.
- Only propose actions covered by docs or add "doc update required".
