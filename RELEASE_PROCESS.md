# Release Process — GitOps & Dockge Rollouts

**Purpose**
Maintain consistent and traceable releases across stacks using Git tags and Dockge.

## Workflow

1. **Commit Changes**
   - Update `.env` or `docker-compose.yml` files as needed.
   - Commit with clear message:
     ```bash
     git commit -am "Update stack-media compose to v2.3.1"
     ```

2. **Tag the Release**
   - Create a version tag:
     ```bash
     git tag -a vX.Y.Z -m "Release vX.Y.Z"
     git push origin vX.Y.Z
     ```

3. **Trigger Dockge Rollout**
   - Dockge auto-syncs hourly (or run manually):
     ```bash
     docker exec dockge git pull && docker compose up -d
     ```

4. **Verify Rollout**
   - Check Dockge dashboard for updated container versions.
   - Run healthchecks defined in phase 07 Monitoring.

5. **Post-Release Validation**
   - Confirm all Kuma checks green.
   - Review container logs for errors.
   - If rollback required:
     ```bash
     git checkout v(previous_version)
     docker compose up -d
     ```

## Notes
- Never edit live containers manually; all updates go through Git.
- Keep CHANGELOG.md at repo root for release summaries.

---

## ChatOps Service Release (GHCR)

The ChatOps microservice container is built automatically and published to GitHub Container Registry (GHCR).

1. Merge to `main` or push a tag `vX.Y.Z`.
2. GitHub Actions will build and push:
   - `ghcr.io/<owner>/oresi-chatops:main` (for branch)
   - `ghcr.io/<owner>/oresi-chatops:<git-sha>` (for commit)
   - `ghcr.io/<owner>/oresi-chatops:vX.Y.Z` (for tags)
3. Deploy with Docker Compose:
   ```bash
   # example
   docker pull ghcr.io/<owner>/oresi-chatops:vX.Y.Z
   docker compose -f chatops/docker-compose.example.yml up -d
   ```
4. Healthcheck: `/healthz` should return `{status: ok}`; container should report healthy.

Security notes:
- Set `CHATOPS_API_KEY` and (optionally) `CHATOPS_IP_ALLOWLIST` in environment.
- Mount `chatops/intents` read-only into the container.
- Keep service behind Tailscale or a reverse proxy with IP allowlist.
