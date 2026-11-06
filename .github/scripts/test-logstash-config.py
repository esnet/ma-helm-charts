#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pyyaml",
# ]
# ///
"""
Template rendering tests for the logstash-config Helm chart.

Each scenario in SCENARIOS is a self-contained declaration of:
  - which values fixture to render
  - which resource kinds must / must not appear
  - which specific field values to assert
  - which metricsets must / must not appear in the metricbeat ConfigMap data

To add or modify a scenario, edit SCENARIOS only — no test functions change.
"""

import subprocess
import sys
from typing import Any

import yaml

CHART = "charts/logstash-config"

# ---------------------------------------------------------------------------
# Scenario declarations
# ---------------------------------------------------------------------------
# Each scenario is a dict with:
#   name             – unique label shown in test output
#   values           – path to values fixture relative to CHART
#   present          – resource kinds that must appear at least once
#   absent           – resource kinds that must not appear
#   fields           – field assertions as (kind, key_path, expected_value) tuples
#                      key_path is a list of dict keys to traverse on the first
#                      matching resource of that kind.
#   metricsets       – metricsets that must appear in the metricbeat ConfigMap
#   absent_metricsets– metricsets that must NOT appear in the metricbeat ConfigMap
#   known_failure    – optional string; marks an expected failure (XFAIL).

SCENARIOS: list[dict[str, Any]] = [
    {
        # Verifies that multiple Elasticsearch hosts are rendered with commas between
        # entries in the hosts => [...] array so Logstash can parse the config.
        "name": "elasticsearch-multi-host-commas",
        "values": "ci/multi-host-elasticsearch-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "metricbeat_cm_present": False,
        "metricsets": [],
        "absent_metricsets": [],
        "elasticsearch_hosts": [
            "https://10.0.0.1:9200",
            "https://10.0.0.2:9200",
            "https://10.0.0.3:9200",
        ],
    },
    {
        "name": "metricbeat-disabled",
        "values": "ci/minimal-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "metricbeat_cm_present": False,
        "metricsets": [],
        "absent_metricsets": [],
    },
    {
        "name": "metricbeat-default-metricsets",
        "values": "ci/with-metricbeat-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "metricbeat_cm_present": True,
        "metricsets": ["node", "node_stats"],
        "absent_metricsets": [],
    },
    {
        "name": "metricbeat-custom-metricsets",
        "values": "ci/metricbeat-custom-metricsets-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "metricbeat_cm_present": True,
        "metricsets": ["node_stats"],
        "absent_metricsets": ["node"],
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


def find_elasticsearch_output_configmap(docs: list[dict]) -> dict | None:
    for doc in docs:
        if doc.get("kind") == "ConfigMap" and "elasticsearch-output" in doc.get("metadata", {}).get("name", ""):
            return doc
    return None


def check_elasticsearch_hosts(docs: list[dict], expected_hosts: list[str]) -> None:
    """Assert that all expected hosts appear in the ES output ConfigMap and are
    separated by commas so the Logstash config DSL can parse the array."""
    cm = find_elasticsearch_output_configmap(docs)
    if cm is None:
        raise AssertionError("elasticsearch hosts check: no elasticsearch-output ConfigMap found")

    conf_text = "\n".join(cm.get("data", {}).values())

    for host in expected_hosts:
        if host not in conf_text:
            raise AssertionError(
                f"elasticsearch hosts check: {host!r} not found in rendered config"
            )

    # Verify that consecutive host entries are comma-separated.
    # Extract the hosts => [ ... ] block and check that each host (except the last)
    # is followed by a comma before the next host entry.
    import re
    hosts_block_match = re.search(r"hosts\s*=>\s*\[(.*?)\]", conf_text, re.DOTALL)
    if hosts_block_match is None:
        raise AssertionError("elasticsearch hosts check: could not find hosts => [...] block")

    hosts_block = hosts_block_match.group(1)
    # Strip whitespace and split on commas to count parsed entries.
    entries = [e.strip().strip('"') for e in hosts_block.split(",") if e.strip()]
    if len(entries) != len(expected_hosts):
        raise AssertionError(
            f"elasticsearch hosts check: expected {len(expected_hosts)} comma-separated entries, "
            f"got {len(entries)}: {entries!r}"
        )
    for actual, expected in zip(entries, expected_hosts):
        if actual != expected:
            raise AssertionError(
                f"elasticsearch hosts check: entry mismatch — expected {expected!r}, got {actual!r}"
            )


def find_metricbeat_configmap(docs: list[dict]) -> dict | None:
    for doc in docs:
        if doc.get("kind") == "ConfigMap" and "metricbeat" in doc.get("metadata", {}).get("name", ""):
            return doc
    return None


def check_metricsets(docs: list[dict], required: list[str], absent: list[str]) -> None:
    if not required and not absent:
        return

    cm = find_metricbeat_configmap(docs)
    if cm is None:
        raise AssertionError("metricsets check: no metricbeat ConfigMap found")

    raw = cm.get("data", {}).get("metricbeat.yml", "")
    parsed = yaml.safe_load(raw)
    # metricbeat.yml uses a dotted top-level key "metricbeat.modules" whose
    # value is a list; access it directly rather than traversing as nested dicts.
    try:
        modules = parsed["metricbeat.modules"]
        actual = modules[0]["metricsets"]
    except (KeyError, TypeError, IndexError) as exc:
        raise AssertionError(f"metricsets check: could not parse metricbeat.yml — {exc}") from exc

    for ms in required:
        if ms not in actual:
            raise AssertionError(f"metricset {ms!r} must be present but was not found in {actual!r}")

    for ms in absent:
        if ms in actual:
            raise AssertionError(f"metricset {ms!r} must not be present but was found in {actual!r}")


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
            raise AssertionError(f"field check on {kind}: no resource of that kind found")
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

    if "elasticsearch_hosts" in scenario:
        check_elasticsearch_hosts(docs, scenario["elasticsearch_hosts"])

    if "metricbeat_cm_present" in scenario:
        cm = find_metricbeat_configmap(docs)
        if scenario["metricbeat_cm_present"] and cm is None:
            raise AssertionError("metricbeat ConfigMap must be present but was not rendered")
        if not scenario["metricbeat_cm_present"] and cm is not None:
            raise AssertionError("metricbeat ConfigMap must not be rendered but was found")

    check_metricsets(
        docs,
        scenario.get("metricsets", []),
        scenario.get("absent_metricsets", []),
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
