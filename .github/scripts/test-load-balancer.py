#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pyyaml",
# ]
# ///
"""
Template rendering tests for the load-balancer Helm chart.

Each scenario in SCENARIOS is a self-contained declaration of:
  - which values fixture to render
  - which resource kinds must / must not appear
  - which specific field values to assert

To add or modify a scenario, edit SCENARIOS only — no test functions change.
"""

import subprocess
import sys
from typing import Any

import yaml

CHART = "charts/load-balancer"

# ---------------------------------------------------------------------------
# Scenario declarations
# ---------------------------------------------------------------------------
# Each scenario is a dict with:
#   name          – unique label shown in test output
#   values        – path to values fixture relative to CHART
#   present       – resource kinds that must appear at least once
#   absent        – resource kinds that must not appear
#   fields        – field assertions as (kind, key_path, expected_value) tuples
#                   key_path is a list of dict keys to traverse on the first
#                   matching resource of that kind.  A list (rather than dot-
#                   notation) lets annotation keys like "networking.gke.io/..."
#                   work without any escaping.
#   known_failure – optional string; marks an expected failure (XFAIL).
#                   Remove the key once the underlying issue is resolved.

_LB_ADDR = [
    "spec",
    "provider",
    "kubernetes",
    "envoyService",
    "annotations",
    "networking.gke.io/load-balancer-ip-addresses",
]

SCENARIOS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # Envoy — IP family
    # ------------------------------------------------------------------
    {
        "name": "envoy-ipv4",
        "values": "ci/envoy-ipv4-values.yaml",
        "present": ["EnvoyProxy", "GatewayClass", "Gateway", "ClientTrafficPolicy"],
        "absent": ["GCPGatewayPolicy"],
        "fields": [
            ("EnvoyProxy", ["spec", "ipFamily"], "IPv4"),
            ("EnvoyProxy", _LB_ADDR, "10.0.0.1"),
            (
                "GatewayClass",
                ["spec", "controllerName"],
                "gateway.envoyproxy.io/gatewayclass-controller",
            ),
            ("Gateway", ["spec", "gatewayClassName"], "envoy"),
        ],
    },
    {
        "name": "envoy-ipv6",
        "values": "ci/envoy-ipv6-values.yaml",
        "present": ["EnvoyProxy", "GatewayClass", "Gateway", "ClientTrafficPolicy"],
        "absent": ["GCPGatewayPolicy"],
        "fields": [
            ("EnvoyProxy", ["spec", "ipFamily"], "IPv6"),
            ("EnvoyProxy", _LB_ADDR, "2001:db8::1"),
        ],
    },
    {
        "name": "envoy-dualstack",
        "values": "ci/envoy-dualstack-values.yaml",
        "present": ["EnvoyProxy", "GatewayClass", "Gateway", "ClientTrafficPolicy"],
        "absent": ["GCPGatewayPolicy"],
        "fields": [
            ("EnvoyProxy", ["spec", "ipFamily"], "DualStack"),
            ("EnvoyProxy", _LB_ADDR, "10.0.0.1,2001:db8::1"),
        ],
    },
    # ------------------------------------------------------------------
    # Envoy — TLS policy
    # ------------------------------------------------------------------
    {
        "name": "envoy-tls-policy-enabled",
        "values": "ci/envoy-ipv4-values.yaml",  # tlsPolicy.enabled: true
        "present": ["ClientTrafficPolicy"],
        "absent": ["GCPGatewayPolicy"],
        "fields": [],
    },
    {
        "name": "envoy-tls-policy-disabled",
        "values": "ci/envoy-tls-policy-disabled-values.yaml",
        "present": ["EnvoyProxy", "GatewayClass", "Gateway"],
        "absent": ["ClientTrafficPolicy", "GCPGatewayPolicy"],
        "fields": [],
    },
    # ------------------------------------------------------------------
    # GKE — IP family
    # ------------------------------------------------------------------
    {
        "name": "gke-ipv4",
        "values": "ci/gke-ipv4-values.yaml",
        "present": ["Gateway"],
        "absent": [
            "EnvoyProxy",
            "GatewayClass",
            "ClientTrafficPolicy",
            "GCPGatewayPolicy",
        ],
        "fields": [
            ("Gateway", ["spec", "gatewayClassName"], "gke-l7-global-external-managed"),
            (
                "Gateway",
                ["spec", "addresses"],
                [{"type": "NamedAddress", "value": "test-staging-ipv4"}],
            ),
        ],
    },
    {
        "name": "gke-ipv6",
        "values": "ci/gke-ipv6-values.yaml",
        "present": ["Gateway"],
        "absent": [
            "EnvoyProxy",
            "GatewayClass",
            "ClientTrafficPolicy",
            "GCPGatewayPolicy",
        ],
        "fields": [
            ("Gateway", ["spec", "gatewayClassName"], "gke-l7-global-external-managed"),
            (
                "Gateway",
                ["spec", "addresses"],
                [{"type": "NamedAddress", "value": "test-staging-ipv6"}],
            ),
        ],
    },
    {
        "name": "gke-dualstack",
        "values": "ci/gke-dualstack-values.yaml",
        "present": ["Gateway"],
        "absent": [
            "EnvoyProxy",
            "GatewayClass",
            "ClientTrafficPolicy",
            "GCPGatewayPolicy",
        ],
        "fields": [
            ("Gateway", ["spec", "gatewayClassName"], "gke-l7-global-external-managed"),
            (
                "Gateway",
                ["spec", "addresses"],
                [
                    {"type": "NamedAddress", "value": "test-staging-ipv4"},
                    {"type": "NamedAddress", "value": "test-staging-ipv6"},
                ],
            ),
        ],
    },
    # ------------------------------------------------------------------
    # GKE — TLS policy
    # ------------------------------------------------------------------
    {
        "name": "gke-tls-policy",
        "values": "ci/gke-tls-policy-values.yaml",
        "present": ["Gateway", "GCPGatewayPolicy"],
        "absent": ["EnvoyProxy", "GatewayClass", "ClientTrafficPolicy"],
        "fields": [
            ("Gateway", ["spec", "gatewayClassName"], "gke-l7-global-external-managed"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Engine — nothing below needs to change when adding scenarios
# ---------------------------------------------------------------------------


def render(values_file: str) -> list[dict]:
    result = subprocess.run(
        ["helm", "template", "ci-test", CHART, "-f", f"{CHART}/{values_file}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [d for d in yaml.safe_load_all(result.stdout) if d is not None]


def find(docs: list[dict], kind: str) -> list[dict]:
    return [d for d in docs if d.get("kind") == kind]


def deep_get(obj: Any, keys: list[str]) -> Any:
    for key in keys:
        if not isinstance(obj, dict):
            raise KeyError(f"expected dict at {key!r}, got {type(obj).__name__}")
        obj = obj[key]
    return obj


def run_scenario(scenario: dict[str, Any], docs: list[dict]) -> None:
    for kind in scenario.get("present", []):
        if not find(docs, kind):
            raise AssertionError(f"{kind} must be present but was not rendered")

    for kind in scenario.get("absent", []):
        found = find(docs, kind)
        if found:
            raise AssertionError(
                f"{kind} must not be rendered but {len(found)} instance(s) found"
            )

    for kind, key_path, expected in scenario.get("fields", []):
        matches = find(docs, kind)
        if not matches:
            raise AssertionError(
                f"field check on {kind}: no resource of that kind found"
            )
        try:
            actual = deep_get(matches[0], key_path)
        except KeyError as exc:
            raise AssertionError(
                f"{kind}: key path {key_path} not found — {exc}"
            ) from exc
        if actual != expected:
            path_label = ".".join(key_path)
            raise AssertionError(
                f"{kind}.{path_label}: expected {expected!r}, got {actual!r}"
            )


def main() -> None:
    passed, failed, xfailed = 0, 0, 0

    for scenario in SCENARIOS:
        name = scenario["name"]
        known_failure: str | None = scenario.get("known_failure")
        try:
            docs = render(scenario["values"])
            run_scenario(scenario, docs)
            if known_failure:
                print(
                    f"  XPASS  {name}  (was known failure — remove 'known_failure' key)"
                )
            else:
                print(f"  PASS   {name}")
            passed += 1
        except AssertionError as e:
            if known_failure:
                print(f"  XFAIL  {name}  ({e})")
                xfailed += 1
            else:
                print(f"  FAIL   {name}: {e}")
                failed += 1
        except subprocess.CalledProcessError as e:
            print(f"  ERROR  {name}: helm template failed\n{e.stderr.strip()}")
            failed += 1

    total = passed + failed + xfailed
    print(
        f"\n{total} scenarios: {passed} passed, {failed} failed, {xfailed} xfailed (known)"
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
