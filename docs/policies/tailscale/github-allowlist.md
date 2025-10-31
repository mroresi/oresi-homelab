# GitHub → Tailscale Allowlist

This guide documents how to generate and maintain a Tailscale ACL snippet that
lets GitHub services (webhooks, Actions runners, Copilot, and more) reach the
ChatOps API running inside the homelab.

## Why this exists

- The ChatOps FastAPI service restricts inbound traffic by IP when
  `CHATOPS_IP_ALLOWLIST` is configured.
- GitHub sends traffic from a large, frequently changing set of addresses. The
  allowlist must stay in sync with GitHub's published ranges to avoid webhook
  failures or flaky CI/CD jobs.
- Tailscale ACLs support CIDR-based selectors, so we can explicitly grant
  GitHub's source networks access to the ChatOps listener on
  `whitebox:8000` (or any other tagged node/port).

## Generation workflow

1. Activate the virtual environment: `source ~/.oresi_venv/bin/activate`
2. Run the generator script:

   ```bash
   python scripts/github_tailscale_acl.py \
     --dest whitebox:8000 \
     --tag-owner user:oresi@example.com \
     --output docs/policies/tailscale/github-allow-github.json
   ```

   - The script pulls the latest metadata from `https://api.github.com/meta`.
   - Categories included by default: hooks, actions, web, api, git, packages,
     codespaces, copilot, dependabot.
   - Override categories with `--categories hooks actions` if a smaller scope is
     needed.

3. Inspect the resulting policy file and upload it to the Tailscale Admin UI
   (`Access Controls → Edit policy`).
4. Optionally commit the generated file so changes are tracked in GitOps.

## Policy contents

The generated policy includes:

- `autogroup:admin` access to the configured destinations (for manual
  troubleshooting).
- `tag:automation` access (so existing automation runners keep working).
- A rule that accepts traffic from each GitHub CIDR range to the selected
  destination selectors.
- A `tagOwners` entry for `tag:github-ingress`, assignable to your account.

Example excerpt (abridged for readability):

```json
{
  "$schema": "https://tailscale.com/schemas/tailnet-policy.v1.json",
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:admin"],
      "dst": ["whitebox:8000"]
    },
    {
      "action": "accept",
      "src": [
        "192.30.252.0/22",
        "185.199.108.0/22",
        "140.82.112.0/20"
      ],
      "dst": ["whitebox:8000"]
    }
  ],
  "tagOwners": {
    "tag:github-ingress": [
      "user:oresi@example.com"
    ]
  }
}
```

When loading the file in the Tailscale UI, verify the destination selector
matches the node that terminates GitHub traffic (for example, a `tailscale
serve --https` listener or a reverse proxy that proxies to ChatOps).

## Maintenance

- Re-run the generator whenever GitHub publishes updated network ranges (review
  the weekly `github/meta` changelog or schedule a CI job).
- Keep the generated policy under version control so changes can be audited.
- If a new GitHub surface (for example, `artifact`) appears in the meta payload,
  add it to the `--categories` list so its ranges are included.
- After updating the policy, remember to reload ChatOps if its
  `CHATOPS_IP_ALLOWLIST` mirrors the same CIDRs.
