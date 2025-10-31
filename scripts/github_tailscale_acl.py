#!/usr/bin/env python3
"""Generate a Tailscale ACL snippet that allowlists GitHub network ranges.

The script pulls the latest network metadata from the GitHub meta API and
produces a Tailnet policy (HuJSON-compatible JSON) that grants inbound access
from selected GitHub IP ranges to one or more Tailscale destinations.

Example:
    python scripts/github_tailscale_acl.py \
        --dest whitebox:8000 \
        --tag-owner user:oresi@example.com \
        --output docs/policies/tailscale/github-allow-github.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from ipaddress import ip_network
from pathlib import Path
from typing import Iterable, List, Sequence, Set
from urllib import request

META_ENDPOINT = "https://api.github.com/meta"
DEFAULT_CATEGORIES: Sequence[str] = (
    "hooks",
    "actions",
    "web",
    "api",
    "git",
    "packages",
    "codespaces",
    "copilot",
    "dependabot",
)


def fetch_meta(url: str, timeout: float) -> dict:
    """Fetch GitHub network metadata from the API."""
    with request.urlopen(url, timeout=timeout) as resp:  # nosec B310
        if resp.status != 200:
            raise RuntimeError(f"Failed to fetch {url}: status={resp.status}")
        data = resp.read()
    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("Invalid JSON payload from GitHub meta API") from exc


def load_meta(meta_file: Path | None, timeout: float) -> dict:
    """Load GitHub network metadata from file or remote API."""
    if meta_file:
        text = meta_file.read_text(encoding="utf-8")
        return json.loads(text)
    return fetch_meta(META_ENDPOINT, timeout)


def collect_networks(meta: dict, categories: Iterable[str]) -> List[str]:
    """Collect unique IPv4/IPv6 ranges for the given GitHub categories."""
    networks: Set[str] = set()
    for category in categories:
        values = meta.get(category)
        if not values:
            logging.warning("Category '%s' missing in GitHub meta payload", category)
            continue
        if not isinstance(values, list):
            logging.warning("Category '%s' payload is not a list", category)
            continue
        for item in values:
            try:
                ip_network(item, strict=False)
            except ValueError:
                logging.debug("Skipping non-network entry '%s' in %s", item, category)
                continue
            networks.add(item)
    return sorted(networks, key=lambda value: (":" in value, value))


def build_policy(
    github_networks: Sequence[str],
    destinations: Sequence[str],
    tag: str,
    tag_owners: Sequence[str],
    include_admin_rule: bool,
    include_automation_tag: bool,
) -> dict:
    """Compose the Tailnet policy document."""
    acls = []
    if include_admin_rule:
        acls.append(
            {
                "action": "accept",
                "src": ["autogroup:admin"],
                "dst": list(destinations),
            }
        )
    if include_automation_tag:
        acls.append(
            {
                "action": "accept",
                "src": ["tag:automation"],
                "dst": list(destinations),
            }
        )
    if github_networks:
        acls.append(
            {
                "action": "accept",
                "src": list(github_networks),
                "dst": list(destinations),
            }
        )
    policy: dict[str, object] = {
        "$schema": "https://tailscale.com/schemas/tailnet-policy.v1.json",
        "acls": acls,
    }
    if tag:
        policy.setdefault("tagOwners", {})  # type: ignore[arg-type]
        policy["tagOwners"][tag] = list(tag_owners) if tag_owners else []  # type: ignore[index]
    return policy


def write_policy(document: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--categories",
        nargs="+",
        default=list(DEFAULT_CATEGORIES),
        help=(
            "GitHub meta API categories to include "
            "(default: hooks actions web api git packages codespaces copilot dependabot)"
        ),
    )
    parser.add_argument(
        "--dest",
        dest="destinations",
        nargs="+",
        default=["whitebox:8000"],
        help="Tailnet destination selectors (hostname:port or tag:tagname:port)",
    )
    parser.add_argument(
        "--tag",
        default="tag:github-ingress",
        help="Tag assigned to nodes that will receive GitHub traffic",
    )
    parser.add_argument(
        "--tag-owner",
        dest="tag_owners",
        nargs="+",
        default=[],
        help="Tailnet identities allowed to assign the tag (e.g. user:admin@example.com)",
    )
    parser.add_argument(
        "--meta-file",
        type=Path,
        default=None,
        help="Optional path to a cached GitHub meta JSON payload",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds when fetching the GitHub meta endpoint",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/policies/tailscale/github-allow-github.json"),
        help=(
            "Where to write the generated policy "
            "(default: docs/policies/tailscale/github-allow-github.json)"
        ),
    )
    parser.add_argument(
        "--no-admin-rule",
        action="store_true",
        help="Do not include the default autogroup:admin allow rule",
    )
    parser.add_argument(
        "--no-automation-tag",
        action="store_true",
        help="Do not include the tag:automation allow rule",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    try:
        meta = load_meta(args.meta_file, args.timeout)
    except Exception as exc:  # pragma: no cover - network failures
        logging.error("Unable to load GitHub metadata: %s", exc)
        return 1

    networks = collect_networks(meta, args.categories)
    if not networks:
        logging.error("No GitHub networks found for the requested categories")
        return 1

    policy = build_policy(
        github_networks=networks,
        destinations=args.destinations,
        tag=args.tag,
        tag_owners=args.tag_owners,
        include_admin_rule=not args.no_admin_rule,
        include_automation_tag=not args.no_automation_tag,
    )
    write_policy(policy, args.output)
    logging.info("Wrote policy with %d GitHub networks to %s", len(networks), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
