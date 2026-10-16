#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml",
# ]
# ///
"""
Template rendering tests for the kafka-config Helm chart.

Each scenario in SCENARIOS is a self-contained declaration of:
  - which values fixture to render
  - which resource kinds must / must not appear
  - field assertions   — (kind, key_path, expected)
      key_path is a list of dict/list keys traversed on the first matching
      resource of that kind.  Integer entries index into lists.
  - pool_fields        — assertions on a named KafkaNodePool
      (pool_name, key_path, expected)
  - listener_fields    — assertions on a named listener within spec.kafka.listeners
      (listener_name, key_path, expected)
  - listener_broker_count — (listener_name, expected_count)
      checks len(spec.kafka.listeners[name].configuration.brokers)
  - broker_ids         — (listener_name, expected_id_list)
      checks the exact broker IDs rendered for a listener

To add a scenario, edit SCENARIOS only — the engine below does not change.
"""

import subprocess
import sys
from typing import Any

import yaml

CHART = "charts/kafka-config"


# ---------------------------------------------------------------------------
# Scenario declarations
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # Minimal — internal listeners only, no external config
    # ------------------------------------------------------------------
    {
        "name": "minimal-internal-only",
        "values": "ci/minimal-values.yaml",
        "present": ["Kafka", "KafkaNodePool"],
        "absent": [],
        "fields": [
            ("Kafka", ["spec", "kafka", "version"], "4.1.0"),
        ],
        "pool_fields": [
            # broker pool carries the node-ID range annotation
            ("kafka", ["metadata", "annotations", "strimzi.io/next-node-ids"], "[100-199]"),
        ],
        "listener_fields": [
            ("plain", ["port"], 9092),
            ("plain", ["type"], "internal"),
            ("plain", ["tls"], False),
            ("tls",   ["port"], 9093),
            ("tls",   ["tls"], True),
            ("tls",   ["authentication", "type"], "tls"),
        ],
        "listener_broker_count": [],
        "broker_ids": [],
    },
    # ------------------------------------------------------------------
    # External SCRAM — IPv4 single-stack, 3 brokers with per-broker IPs
    # ------------------------------------------------------------------
    {
        "name": "extusers-ipv4",
        "values": "ci/extusers-ipv4-values.yaml",
        "present": ["Kafka", "KafkaNodePool"],
        "absent": [],
        "fields": [],
        "pool_fields": [
            ("kafka", ["metadata", "annotations", "strimzi.io/next-node-ids"], "[100-199]"),
        ],
        "listener_fields": [
            ("extusers", ["port"], 9095),
            ("extusers", ["type"], "loadbalancer"),
            ("extusers", ["authentication", "type"], "scram-sha-512"),
            ("extusers", ["authentication", "sasl"], True),
            ("extusers", ["configuration", "ipFamilyPolicy"], "SingleStack"),
            ("extusers", ["configuration", "ipFamilies"], ["IPv4"]),
            # bootstrap annotations
            (
                "extusers",
                ["configuration", "bootstrap", "annotations", "cloud.google.com/l4-rbs"],
                "enabled",
            ),
            (
                "extusers",
                ["configuration", "bootstrap", "annotations",
                 "networking.gke.io/load-balancer-ip-addresses"],
                "kafka-ci-bootstrap-ipv4",
            ),
            # first broker (ID 100) carries both annotations
            (
                "extusers",
                ["configuration", "brokers", 0, "broker"],
                100,
            ),
            (
                "extusers",
                ["configuration", "brokers", 0, "annotations", "cloud.google.com/l4-rbs"],
                "enabled",
            ),
            (
                "extusers",
                ["configuration", "brokers", 0, "annotations",
                 "networking.gke.io/load-balancer-ip-addresses"],
                "kafka-ci-broker-100-ipv4",
            ),
            # last broker (ID 102)
            (
                "extusers",
                ["configuration", "brokers", 2, "broker"],
                102,
            ),
            (
                "extusers",
                ["configuration", "brokers", 2, "annotations",
                 "networking.gke.io/load-balancer-ip-addresses"],
                "kafka-ci-broker-102-ipv4",
            ),
        ],
        "listener_broker_count": [("extusers", 3)],
        "broker_ids": [("extusers", [100, 101, 102])],
    },
    # ------------------------------------------------------------------
    # External SCRAM — IPv6 single-stack, l4-rbs on bootstrap + brokers
    # ------------------------------------------------------------------
    {
        "name": "extusers-ipv6",
        "values": "ci/extusers-ipv6-values.yaml",
        "present": ["Kafka", "KafkaNodePool"],
        "absent": [],
        "fields": [],
        "pool_fields": [],
        "listener_fields": [
            ("extusers6", ["port"], 9096),
            ("extusers6", ["configuration", "ipFamilyPolicy"], "SingleStack"),
            ("extusers6", ["configuration", "ipFamilies"], ["IPv6"]),
            (
                "extusers6",
                ["configuration", "bootstrap", "annotations", "cloud.google.com/l4-rbs"],
                "enabled",
            ),
            (
                "extusers6",
                ["configuration", "bootstrap", "annotations",
                 "networking.gke.io/load-balancer-ip-addresses"],
                "kafka-ci-bootstrap-ipv6",
            ),
            # every broker must carry l4-rbs
            (
                "extusers6",
                ["configuration", "brokers", 0, "annotations", "cloud.google.com/l4-rbs"],
                "enabled",
            ),
            (
                "extusers6",
                ["configuration", "brokers", 1, "annotations", "cloud.google.com/l4-rbs"],
                "enabled",
            ),
            (
                "extusers6",
                ["configuration", "brokers", 2, "annotations", "cloud.google.com/l4-rbs"],
                "enabled",
            ),
        ],
        "listener_broker_count": [("extusers6", 3)],
        "broker_ids": [("extusers6", [100, 101, 102])],
    },
    # ------------------------------------------------------------------
    # Broker scaling — 4 replicas produce broker IDs 100-103, not 0-3
    # ------------------------------------------------------------------
    {
        "name": "broker-scaling-4-replicas",
        "values": "ci/broker-scaling-values.yaml",
        "present": ["Kafka", "KafkaNodePool"],
        "absent": [],
        "fields": [],
        "pool_fields": [
            ("kafka", ["spec", "replicas"], 4),
        ],
        "listener_fields": [
            (
                "extusers",
                ["configuration", "brokers", 3, "broker"],
                103,
            ),
            (
                "extusers",
                ["configuration", "brokers", 3, "annotations",
                 "networking.gke.io/load-balancer-ip-addresses"],
                "kafka-ci-broker-103-ipv4",
            ),
        ],
        "listener_broker_count": [("extusers", 4)],
        "broker_ids": [("extusers", [100, 101, 102, 103])],
    },
    # ------------------------------------------------------------------
    # No broker IPs — brokerAnnotations only, no per-broker IP annotation
    # ------------------------------------------------------------------
    {
        "name": "no-broker-ips",
        "values": "ci/no-broker-ips-values.yaml",
        "present": ["Kafka", "KafkaNodePool"],
        "absent": [],
        "fields": [],
        "pool_fields": [],
        "listener_fields": [
            (
                "extusers",
                ["configuration", "brokers", 0, "annotations", "cloud.google.com/l4-rbs"],
                "enabled",
            ),
        ],
        "listener_broker_count": [("extusers", 3)],
        "broker_ids": [("extusers", [100, 101, 102])],
        # separate check: IP annotation must be absent from brokers
        "broker_ip_absent": ["extusers"],
    },
    # ------------------------------------------------------------------
    # Anti-affinity — pool-name label, not cluster-name label
    # Regression test: strimzi.io/name is cluster-scoped (shared by both
    # controllers and brokers), causing controllers to block broker
    # scheduling. Must use strimzi.io/pool-name which is pool-scoped.
    # ------------------------------------------------------------------
    {
        "name": "anti-affinity-uses-pool-name",
        "values": "ci/minimal-values.yaml",
        "present": ["KafkaNodePool"],
        "absent": [],
        "fields": [],
        "pool_fields": [
            (
                "controller",
                [
                    "spec", "template", "pod", "affinity",
                    "podAntiAffinity",
                    "requiredDuringSchedulingIgnoredDuringExecution",
                    0, "labelSelector", "matchExpressions", 0, "key",
                ],
                "strimzi.io/pool-name",
            ),
            (
                "controller",
                [
                    "spec", "template", "pod", "affinity",
                    "podAntiAffinity",
                    "requiredDuringSchedulingIgnoredDuringExecution",
                    0, "labelSelector", "matchExpressions", 0, "values",
                ],
                ["controller"],  # matches values.yaml keeper.controller.name
            ),
            (
                "kafka",
                [
                    "spec", "template", "pod", "affinity",
                    "podAntiAffinity",
                    "requiredDuringSchedulingIgnoredDuringExecution",
                    0, "labelSelector", "matchExpressions", 0, "key",
                ],
                "strimzi.io/pool-name",
            ),
            (
                "kafka",
                [
                    "spec", "template", "pod", "affinity",
                    "podAntiAffinity",
                    "requiredDuringSchedulingIgnoredDuringExecution",
                    0, "labelSelector", "matchExpressions", 0, "values",
                ],
                ["kafka"],
            ),
        ],
        "listener_fields": [],
        "listener_broker_count": [],
        "broker_ids": [],
    },
]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def render(values_file: str) -> list[dict]:
    result = subprocess.run(
        ["helm", "template", "ci-test", CHART, "-f", f"{CHART}/{values_file}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [d for d in yaml.safe_load_all(result.stdout) if d is not None]


def find_kind(docs: list[dict], kind: str) -> list[dict]:
    return [d for d in docs if d.get("kind") == kind]


def find_pool(docs: list[dict], name: str) -> dict:
    """Return the KafkaNodePool whose metadata.name matches."""
    pools = [
        d for d in docs
        if d.get("kind") == "KafkaNodePool"
        and d.get("metadata", {}).get("name") == name
    ]
    if not pools:
        raise AssertionError(f"KafkaNodePool '{name}' not found in rendered output")
    return pools[0]


def find_listener(docs: list[dict], name: str) -> dict:
    """Return the listener entry from spec.kafka.listeners whose name matches."""
    kafkas = find_kind(docs, "Kafka")
    if not kafkas:
        raise AssertionError("No Kafka resource found in rendered output")
    listeners: list[dict] = kafkas[0]["spec"]["kafka"]["listeners"]
    matches = [l for l in listeners if l.get("name") == name]
    if not matches:
        available = [l.get("name") for l in listeners]
        raise AssertionError(
            f"Listener '{name}' not found. Available: {available}"
        )
    return matches[0]


def deep_get(obj: Any, keys: list) -> Any:
    """Traverse a nested dict/list using a list of string or integer keys."""
    for key in keys:
        if isinstance(key, int):
            if not isinstance(obj, list):
                raise KeyError(f"expected list for index {key}, got {type(obj).__name__}")
            obj = obj[key]
        else:
            if not isinstance(obj, dict):
                raise KeyError(f"expected dict at key {key!r}, got {type(obj).__name__}")
            obj = obj[key]
    return obj


def run_scenario(scenario: dict[str, Any], docs: list[dict]) -> None:
    name = scenario["name"]

    # --- present / absent ---
    for kind in scenario.get("present", []):
        if not find_kind(docs, kind):
            raise AssertionError(f"{kind} must be present but was not rendered")

    for kind in scenario.get("absent", []):
        found = find_kind(docs, kind)
        if found:
            raise AssertionError(
                f"{kind} must not be rendered but {len(found)} instance(s) found"
            )

    # --- top-level field assertions on first matching resource ---
    for kind, key_path, expected in scenario.get("fields", []):
        matches = find_kind(docs, kind)
        if not matches:
            raise AssertionError(f"field check on {kind}: no resource of that kind found")
        try:
            actual = deep_get(matches[0], key_path)
        except KeyError as exc:
            raise AssertionError(f"{kind}: key path {key_path} not found — {exc}") from exc
        if actual != expected:
            raise AssertionError(
                f"{kind}.{key_path}: expected {expected!r}, got {actual!r}"
            )

    # --- KafkaNodePool assertions by pool name ---
    for pool_name, key_path, expected in scenario.get("pool_fields", []):
        pool = find_pool(docs, pool_name)
        try:
            actual = deep_get(pool, key_path)
        except KeyError as exc:
            raise AssertionError(
                f"KafkaNodePool '{pool_name}': key path {key_path} not found — {exc}"
            ) from exc
        if actual != expected:
            raise AssertionError(
                f"KafkaNodePool '{pool_name}'.{key_path}: expected {expected!r}, got {actual!r}"
            )

    # --- listener field assertions by listener name ---
    for listener_name, key_path, expected in scenario.get("listener_fields", []):
        listener = find_listener(docs, listener_name)
        try:
            actual = deep_get(listener, key_path)
        except KeyError as exc:
            raise AssertionError(
                f"listener '{listener_name}': key path {key_path} not found — {exc}"
            ) from exc
        if actual != expected:
            raise AssertionError(
                f"listener '{listener_name}'.{key_path}: expected {expected!r}, got {actual!r}"
            )

    # --- broker count per listener ---
    for listener_name, expected_count in scenario.get("listener_broker_count", []):
        listener = find_listener(docs, listener_name)
        try:
            brokers = deep_get(listener, ["configuration", "brokers"])
        except KeyError as exc:
            raise AssertionError(
                f"listener '{listener_name}': configuration.brokers not found — {exc}"
            ) from exc
        if len(brokers) != expected_count:
            raise AssertionError(
                f"listener '{listener_name}': expected {expected_count} brokers, "
                f"got {len(brokers)}"
            )

    # --- exact broker ID sequence per listener ---
    for listener_name, expected_ids in scenario.get("broker_ids", []):
        listener = find_listener(docs, listener_name)
        try:
            brokers = deep_get(listener, ["configuration", "brokers"])
        except KeyError as exc:
            raise AssertionError(
                f"listener '{listener_name}': configuration.brokers not found — {exc}"
            ) from exc
        actual_ids = [b["broker"] for b in brokers]
        if actual_ids != expected_ids:
            raise AssertionError(
                f"listener '{listener_name}': expected broker IDs {expected_ids}, "
                f"got {actual_ids}"
            )

    # --- IP annotation must be absent from all brokers ---
    for listener_name in scenario.get("broker_ip_absent", []):
        listener = find_listener(docs, listener_name)
        try:
            brokers = deep_get(listener, ["configuration", "brokers"])
        except KeyError as exc:
            raise AssertionError(
                f"listener '{listener_name}': configuration.brokers not found — {exc}"
            ) from exc
        ip_key = "networking.gke.io/load-balancer-ip-addresses"
        for broker in brokers:
            annotations = broker.get("annotations", {})
            if ip_key in annotations:
                raise AssertionError(
                    f"listener '{listener_name}' broker {broker['broker']}: "
                    f"'{ip_key}' should not be present when brokerIpAddresses is omitted"
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
                print(f"  XPASS  {name}  (was known failure — remove 'known_failure' key)")
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
    print(f"\n{total} scenarios: {passed} passed, {failed} failed, {xfailed} xfailed (known)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
