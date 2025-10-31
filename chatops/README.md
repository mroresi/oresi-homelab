# ChatOps Microservice (hardened)

FastAPI service to execute auditable intents from `/chatops/intents/*.yaml`.

## Security

- Requires `X-API-Key` header. Set server key via `CHATOPS_API_KEY` env var.
- Validates `label_required` matches `APPROVED_LABEL` (default `approved-by-gemini`).
- Executes only structured, allowlisted actions; no shell execution.
- **Rate limiting**: 10 requests per minute per IP (prevents abuse, configurable).
- **Discord audit alerts** (optional): Set `DISCORD_WEBHOOK_URL` to receive real-time alerts for:
  - 🚨 Auth failures (invalid API key)
  - 🚨 IP allowlist violations
  - 🚨 Label mismatches
  - ❌ Command failures with stderr output
  - ✅ Successful deployments
- Recommended: run behind Tailscale or reverse proxy with IP allowlist.

## Endpoints

- `GET /healthz` → `{ "status": "ok" }`
- `GET /status` → Service version, uptime, loaded intents, features
- `GET /metrics` → Prometheus metrics (intents executed, failures, auth rejections)
- `GET /intents` → List all available intents with metadata
- `POST /validate` → Validate intent YAML without executing (returns errors/warnings)
- `POST /run` → `{ ok: true, stdout: "..." }` (requires `X-API-Key`)
  - Add `"dry_run": true` to preview commands without execution
- `POST /orchestrate` → Execute multiple intents in sequence with dependency resolution (requires `X-API-Key`)
  - Supports `depends_on` field in intents for automatic ordering
  - `"stop_on_failure": true` to halt on first error
- `GET /schedules` → List loaded schedules (requires `X-API-Key`)
- `POST /schedules/reload` → Reload schedules from file (requires `X-API-Key`)
- `POST /schedules/run_now` → Run an intent immediately (requires `X-API-Key`)
- `POST /webhook/github` → GitHub webhook receiver (HMAC-SHA256)
- `POST /webhook/gitlab` → GitLab webhook receiver (X-Gitlab-Token)

## RBAC (optional)

Fine-grained access control can restrict which API keys may call which endpoints and which intents (by action/stack). When RBAC is enabled, requests must use an API key defined in the RBAC config; the global `CHATOPS_API_KEY` is only used if RBAC is not configured.

Enable RBAC by providing either environment variable:

- `CHATOPS_RBAC_JSON`: inline JSON object
- `CHATOPS_RBAC_FILE`: path to a JSON file with the same structure

Schema:

```json
{
  "keys": {
    "<api-key>": {
      "endpoints": ["run", "orchestrate", "schedules", "schedules_reload", "schedules_run_now", "*"] ,
      "actions": ["rollout", "scale", "*"],
      "stacks": ["stack-media", "stack-content", "stack-ai", "*"]
    }
  }
}
```

Rules:

- Wildcards `*` are supported in each list.
- Endpoint checks happen first; then per-intent checks use `action` and `stack` from the target intent.
- If RBAC is not configured, any request with the global API key is allowed (subject to IP allowlist/rate limit).

Examples:

Permit a key to trigger only media rollouts via schedules run-now:

```json
{
  "keys": {
    "media-key": {
      "endpoints": ["schedules_run_now"],
      "actions": ["rollout"],
      "stacks": ["stack-media"]
    }
  }
}
```

Deny listing schedules when the key lacks the `schedules` endpoint. A `403` is returned with message like "RBAC: schedules not permitted".

## Intent schema

```yaml

## Intent schema

```yaml
label_required: approved-by-gemini
action: scale | rollout
stack: stack-name
depends_on:  # Optional: list of intent names to execute first
  - prerequisite_intent
stack: stack-media
service: plex            # required for action=scale
replicas: 2              # required for action=scale
compose: "/opt/stacks/stack-media/docker-compose.yml"  # optional override
```

## Local dev

```bash
export CHATOPS_API_KEY=devkey
uvicorn chatops.main:app --reload --port 8000

# Test dry-run mode
curl -X POST http://localhost:8000/run \
  -H "X-API-Key: devkey" \
  -H "Content-Type: application/json" \
  -d '  -d '{"name": "scale_stack", "dry_run": true}'
```

## Docker

```bash
docker build -t oresi-chatops:dev -f chatops/Dockerfile .
docker run -e CHATOPS_API_KEY=devkey -p 8000:8000 oresi-chatops:dev
```

### From GHCR

```bash
docker pull ghcr.io/mroresi/oresi-chatops:main
docker run -e CHATOPS_API_KEY=devkey -p 8000:8000 ghcr.io/mroresi/oresi-chatops:main
```

### Compose example

See `chatops/docker-compose.example.yml` and `chatops/.env.example`.

```bash
cp chatops/.env.example .env
# edit .env to set CHATOPS_API_KEY=...
docker compose -f chatops/docker-compose.example.yml up -d
```

## Multi-Stack Orchestration

Execute multiple intents in sequence with automatic dependency resolution:

```bash
# Orchestrate rollout across multiple stacks
curl -X POST http://chatops:8000/orchestrate \
  -H "X-API-Key: $CHATOPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "intents": ["rollout_stack_content", "rollout_stack_media", "rollout_stack_ai"],
    "stop_on_failure": true,
    "dry_run": false
  }'

# Response:
# {
#   "ok": true,
#   "results": [
#     {"intent": "rollout_stack_content", "ok": true, "action": "rollout", "stack": "stack-content"},
#     {"intent": "rollout_stack_media", "ok": true, "action": "rollout", "stack": "stack-media"},
#     {"intent": "rollout_stack_ai", "ok": true, "action": "rollout", "stack": "stack-ai"}
#   ],
#   "summary": {
#     "total": 3,
#     "success": 3,
#     "failed": 0
#   }
# }
```

Intents can declare dependencies via `depends_on` field - these are automatically executed first.

## Scheduling (optional)

Scheduling is disabled by default and enabled only when both conditions are true:

- `ENABLE_SCHEDULER=true` env var is set
- APScheduler is installed (`pip install apscheduler`)

Schedules are read from a JSON file (default: `chatops/schedules.json`, configurable via `CHATOPS_SCHEDULES_FILE`).

Example `schedules.json`:

```json
{
  "schedules": [
    {"name": "rollout-media-hourly", "intent": "rollout_stack_media", "cron": "0 * * * *", "enabled": true, "dry_run": false},
    {"name": "scale-ai-nightly", "intent": "scale_stack_ai", "cron": "0 3 * * *", "enabled": false, "dry_run": true}
  ]
}
```

Run an intent immediately (bypass scheduler):

```bash
curl -X POST http://chatops:8000/schedules/run_now \
  -H "X-API-Key: $CHATOPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"intent": "rollout_stack_media", "dry_run": false}'
```

## Webhooks (CI/CD triggers)

Securely trigger intents from GitHub/GitLab by adding markers to commit messages or PR descriptions:

- Marker format: `[chatops:intent=<intent_name>]`
- Example: `feat(media): refresh stack [chatops:intent=rollout_stack_media]`

Enable and secure the endpoints via environment variables:

- GitHub: set `GITHUB_WEBHOOK_SECRET` to your webhook secret. The service validates `X-Hub-Signature-256` using HMAC-SHA256.
- GitLab: set `GITLAB_WEBHOOK_TOKEN` to your webhook token. The service validates `X-Gitlab-Token`.

Notes:

- Supported events: GitHub `push` and `pull_request` (body markers). Unsupported events are acknowledged and ignored.
- Multiple markers in a push will execute intents in order (deduplicated).
- Normal API key auth is not required for webhook endpoints; signatures/tokens are mandatory instead.

## Tests

```bash
pip install -r chatops/requirements.txt
pytest -q chatops
```

## Operations runbook

### Discord webhook setup

1. In Discord: Server Settings → Integrations → Webhooks → New Webhook
2. Copy webhook URL (format: `https://discord.com/api/webhooks/{id}/{token}`)
3. Set `DISCORD_WEBHOOK_URL` env var or add to `.env`
4. Test: trigger an auth failure or successful deploy to verify alerts

### Troubleshooting

- Auth failures (401):
  - Ensure `CHATOPS_API_KEY` is set in the service and you pass `X-API-Key` on requests.
  - If behind a proxy, confirm headers are forwarded unmodified.

- Blocked (403) with message "Client IP not allowed":
  - Set `CHATOPS_IP_ALLOWLIST` env (supports `*`, exact IP/host, or CIDR, comma-separated).
  - If using a proxy, ensure `X-Forwarded-For` is set; we use the first address if present.
- Healthcheck failing:
  - Check container logs for startup errors.
  - Hit `/healthz` locally inside the container: `curl -fsS http://127.0.0.1:8000/healthz`.
  - Confirm port mapping and network ACLs.

- Intent errors:
  - Validate YAML schema (action, stack, service/replicas for scale, compose path).
  - Check logs for `executing` and `command_failed` JSON entries.
  - Test command manually on the host to isolate Docker or compose issues.
