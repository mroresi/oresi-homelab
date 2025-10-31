# End-to-End GitOps Workflow Example

This guide demonstrates the complete workflow from code change to automated deployment using ChatOps.

## Workflow Overview

```
1. Developer changes docker-compose.yml
2. Create PR with updated intent
3. CI validates intent schema
4. Human approves PR with label
5. PR merged to main
6. GitHub Action triggers ChatOps
7. ChatOps executes rollout
8. Discord alert confirms deployment
9. Uptime Kuma verifies health
```

## Example Scenario: Update Plex Container

### Step 1: Developer makes change

**Branch and edit:**
```bash
git checkout -b update-plex-image
cd stacks/stack-media
nano docker-compose.yml
```

**Change in `docker-compose.yml`:**
```yaml
services:
  plex:
    image: plexinc/pms-docker:1.40.5.8897  # was: 1.40.4.8679
    # ... rest of config
```

### Step 2: Update intent file

**Edit intent:**
```bash
cd ../../chatops/intents
nano rollout_stack_media.yaml
```

**Add comment documenting change:**
```yaml
# Rollout Media Stack - Plex Update
# Purpose: Deploy Plex 1.40.5.8897 with subtitle rendering fixes
# Stack: stack-media (Plex, Sonarr, Radarr, Prowlarr, Transmission)
# Reference: STACK_MEDIA_CHECKLIST.md
# Post-deploy: Verify Plex :32400 responds and Uptime Kuma check passes

label_required: approved-by-gemini
action: rollout
stack: stack-media
service: plex
compose: "/opt/stacks/stack-media/docker-compose.yml"
```

### Step 3: Create PR

```bash
git add stacks/stack-media/docker-compose.yml chatops/intents/rollout_stack_media.yaml
git commit -m "Update Plex to 1.40.5.8897 - subtitle rendering fixes"
git push origin update-plex-image
```

**Create PR on GitHub with description:**
```markdown
## Update Plex Container

**Changes:**
- Update Plex image from 1.40.4.8679 to 1.40.5.8897
- Fixes subtitle rendering bug (upstream issue #12345)

**Intent:** `rollout_stack_media`

**Pre-deploy checklist:**
- [x] Tested in dev environment
- [x] Reviewed changelog: https://forums.plex.tv/t/plex-media-server/30447/999
- [x] Verified NFS mounts accessible
- [x] Current Plex users notified of brief downtime

**Post-deploy validation:**
- [ ] Plex responds on :32400
- [ ] Library scan completes
- [ ] Uptime Kuma check green within 5 minutes
- [ ] Discord alert confirms success
```

### Step 4: CI validates intent

**GitHub Actions runs automatically:**
- ✅ Lint/type/test (`ci.yml`)
- ✅ Validate intent schema (`validate-intents.yml`)
- ✅ Security scans (Trivy, Bandit)

**Example output from `validate-intents.yml`:**
```
Validating 6 intent files...
  ✓ rollout_stack_media.yaml (doc 1/1): rollout on stack-media
✅ All 6 intent files are valid!
```

### Step 5: Human approval

**Reviewer checks:**
1. Image tag matches tested version
2. Intent file correctly references new compose
3. Checklist items completed
4. CI passes

**Approve PR and add label:**
- Label: `approved-by-gemini` (matches `label_required` in intent)

### Step 6: Merge PR

```bash
# Reviewer or developer merges PR
# GitHub Actions triggers on push to main
```

### Step 7: GitHub Action triggers ChatOps

**Workflow file:** `.github/workflows/deploy-media-stack.yml`

```yaml
name: Deploy Media Stack

on:
  push:
    branches: [main]
    paths:
      - 'stacks/stack-media/**'
      - 'chatops/intents/rollout_stack_media.yaml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Tailscale
        uses: tailscale/github-action@v2
        with:
          oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}
          oauth-secret: ${{ secrets.TS_OAUTH_SECRET }}
          tags: tag:automation
      
      - name: Wait for Tailscale connection
        run: |
          until tailscale status | grep -q "whitebox"; do
            echo "Waiting for Tailscale connection..."
            sleep 2
          done
          tailscale status
      
      - name: Trigger ChatOps rollout
        run: |
          response=$(curl -X POST http://whitebox.ts.net:8000/run \
            -H "X-API-Key: ${{ secrets.CHATOPS_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d '{"name": "rollout_stack_media"}' \
            -w "\n%{http_code}" -o response.json)
          
          http_code=$(echo "$response" | tail -n1)
          
          if [ "$http_code" -ne 200 ]; then
            echo "❌ ChatOps request failed with status $http_code"
            cat response.json
            exit 1
          fi
          
          echo "✅ ChatOps rollout triggered successfully"
          cat response.json | jq .
      
      - name: Post-deploy validation
        run: |
          echo "Waiting 30s for containers to stabilize..."
          sleep 30
          
          # Check Plex health
          if ! curl -fsS --connect-timeout 10 http://192.168.0.41:32400/web; then
            echo "❌ Plex health check failed"
            exit 1
          fi
          
          echo "✅ Plex is responding on :32400"
```

### Step 8: ChatOps executes rollout

**ChatOps service logs (JSON):**
```json
{
  "name": "root",
  "intent": "rollout_stack_media",
  "action": "rollout",
  "stack": "stack-media",
  "service": "plex",
  "argv": ["docker", "compose", "-f", "/opt/stacks/stack-media/docker-compose.yml", "pull"],
  "client": "100.64.0.5",
  "ts": "2025-10-30 22:30:45,123",
  "level": "INFO",
  "msg": "executing"
}
```

**Docker output:**
```
Pulling plex ... done
Recreating stack-media_plex_1 ... done
```

### Step 9: Discord alert confirms deployment

**Discord message:**
```
🤖 ChatOps Audit
✅ SUCCESS: rollout on stack stack-media (intent: rollout_stack_media)
Today at 10:30 PM
```

### Step 10: Uptime Kuma verifies health

**Uptime Kuma monitor:**
- Check: `Plex Media Server`
- URL: `http://192.168.0.41:32400/web`
- Status: 🟢 UP (200 OK)
- Last check: 30s ago

**Discord notification (from Uptime Kuma):**
```
✅ [Plex Media Server] is UP
Response time: 45ms
Today at 10:31 PM
```

## Rollback Procedure

If deployment fails or introduces issues:

### Option 1: Revert PR
```bash
git revert <commit-hash>
git push origin main
# GitHub Action triggers ChatOps to rollback
```

### Option 2: Manual rollback via ChatOps
```bash
# Create emergency rollback intent
cat > chatops/intents/rollback_plex.yaml << 'EOF'
label_required: approved-by-gemini
action: rollout
stack: stack-media
service: plex
compose: "/opt/stacks/stack-media/docker-compose.yml"
EOF

# Edit docker-compose.yml to previous version
cd stacks/stack-media
git checkout HEAD~1 -- docker-compose.yml

# Commit and push
git add docker-compose.yml chatops/intents/rollback_plex.yaml
git commit -m "ROLLBACK: Revert Plex to 1.40.4.8679"
git push origin main
```

### Option 3: Direct SSH rollback (emergency)
```bash
ssh whitebox.ts.net
cd /opt/stacks/stack-media
git checkout HEAD~1 -- docker-compose.yml
docker compose up -d --force-recreate plex
```

## Monitoring During Rollout

### Real-time monitoring commands:
```bash
# Watch Docker events
docker events --filter type=container --filter container=plex

# Watch logs
docker logs -f stack-media_plex_1

# Watch Uptime Kuma status
curl -s http://uptime-kuma.ts.net:3001/api/badge/1/status | jq .

# Watch ChatOps logs
ssh whitebox.ts.net sudo journalctl -u chatops.service -f
```

### Success criteria:
- ✅ Docker pull completes without errors
- ✅ Container recreates and enters "running" state
- ✅ Plex web UI responds within 60 seconds
- ✅ Uptime Kuma check goes green
- ✅ Discord shows success alert
- ✅ No errors in ChatOps logs

## Security Considerations

1. **Label enforcement**: Only PRs with `approved-by-gemini` label can trigger deployments
2. **Tailscale auth**: GitHub Actions must authenticate via Tailscale OAuth
3. **API key**: ChatOps requires valid `X-API-Key` header (stored in GitHub secrets)
4. **IP allowlist**: ChatOps restricts access to Tailscale CGNAT range (100.64.0.0/10)
5. **Audit trail**: All deployments logged with intent, client IP, timestamps
6. **Rollback ready**: Git history allows instant revert

## Extending the Workflow

### Multi-stack deployments:
Use multi-document YAML intent (`rollout_all_stacks.yaml`) to deploy multiple stacks in sequence.

### Canary deployments:
1. Scale new version to 1 replica
2. Wait for health checks
3. Scale to full replicas if healthy

### Scheduled maintenance:
Use GitHub Actions scheduled workflows:
```yaml
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly Sunday 2 AM
```

### Blue-green deployments:
1. Deploy to "blue" environment
2. Validate health and smoke tests
3. Switch traffic via Nginx Proxy Manager
4. Tear down "green" environment

---

**Key Takeaways:**
- Every deployment is auditable via Git history
- CI validates changes before human approval
- Automation happens only after explicit approval (label + merge)
- Multiple layers of validation (CI, ChatOps, Uptime Kuma)
- Discord provides real-time visibility
- Rollback is simple and fast (revert + push)
