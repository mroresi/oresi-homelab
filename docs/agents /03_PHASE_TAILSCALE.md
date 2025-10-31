# Phase 3 — Tailscale Mesh & MagicDNS

**Inputs**
- 03_Networking_and_Tailscale.md

**Success Criteria**
- `tailscale status` shows all nodes.
- MagicDNS resolves `*.ts.net` names.

**Steps**
1) Install and start `tailscaled` on nodes.
2) `tailscale up --auth-key=<key> --hostname=$(hostname)` on each.
3) Configure advertised routes and (optional) exit node.
4) Approve routes in admin; verify `ping redbox.ts.net`.
