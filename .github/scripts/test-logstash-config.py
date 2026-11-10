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
    {
        "name": "from-image-sources-init-container-rendered",
        "values": "ci/with-image-sources-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "metricbeat_cm_present": False,
        "metricsets": [],
        "absent_metricsets": [],
        "init_containers": ["tls-cert-extractor", "pipeline-copy"],
        "volumes": ["pipeline-app", "tls-certs"],
        "volume_mount_paths": [
            "/usr/share/logstash/pipeline/custom/001",
            "/usr/share/logstash/pipeline/custom/app",
        ],
        "pipeline_copy_files": [
            "/usr/share/logstash/pipeline-src/snow-020-initial-format.conf",
            "/usr/share/logstash/pipeline-src/snow-999-outputs.conf",
        ],
        "extra_env": ["elastic_hosts"],
    },
    {
        "name": "inline-sources-configmap-rendered",
        "values": "ci/with-inline-sources-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "metricbeat_cm_present": False,
        "metricsets": [],
        "absent_metricsets": [],
        "init_containers": [],
        "absent_init_containers": ["pipeline-copy"],
        "inline_indices": [50],
        "volumes": ["pipeline-050"],
        "volume_mount_paths": [
            "/usr/share/logstash/pipeline/custom/050",
        ],
        "absent_volumes": ["pipeline-app"],
    },
    {
        "name": "mixed-sources-all-types",
        "values": "ci/with-mixed-sources-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "metricbeat_cm_present": False,
        "metricsets": [],
        "absent_metricsets": [],
        "init_containers": ["pipeline-copy"],
        "absent_init_containers": ["tls-cert-extractor"],
        "inline_indices": [50],
        "volumes": ["pipeline-020", "pipeline-050", "pipeline-app"],
        "volume_mount_paths": [
            "/usr/share/logstash/pipeline/custom/001",
            "/usr/share/logstash/pipeline/custom/020",
            "/usr/share/logstash/pipeline/custom/050",
            "/usr/share/logstash/pipeline/custom/app",
        ],
        "pipeline_copy_files": [
            "/usr/share/logstash/pipeline-src/mix-080-custom.conf",
        ],
    },
    {
        "name": "backward-compat-transforms-still-work",
        "values": "ci/with-transforms-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "metricbeat_cm_present": False,
        "metricsets": [],
        "absent_metricsets": [],
        "absent_init_containers": ["pipeline-copy"],
        "volumes": ["pipeline-020", "pipeline-090", "pipeline-100"],
        "absent_volumes": ["pipeline-app"],
    },
    {
        "name": "no-image-sources-no-pipeline-copy",
        "values": "ci/minimal-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "metricbeat_cm_present": False,
        "metricsets": [],
        "absent_metricsets": [],
        "absent_init_containers": ["pipeline-copy"],
        "absent_volumes": ["pipeline-app"],
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


def find_logstash_cr(docs: list[dict]) -> dict | None:
    for doc in docs:
        if doc.get("kind") == "Logstash":
            return doc
    return None


def get_init_container_names(docs: list[dict]) -> list[str]:
    cr = find_logstash_cr(docs)
    if cr is None:
        return []
    init_containers = (
        cr.get("spec", {})
        .get("podTemplate", {})
        .get("spec", {})
        .get("initContainers", [])
    )
    return [c.get("name", "") for c in init_containers]


def get_volume_names(docs: list[dict]) -> list[str]:
    cr = find_logstash_cr(docs)
    if cr is None:
        return []
    volumes = (
        cr.get("spec", {})
        .get("podTemplate", {})
        .get("spec", {})
        .get("volumes", [])
    )
    return [v.get("name", "") for v in volumes]


def get_volume_mount_paths(docs: list[dict]) -> list[str]:
    cr = find_logstash_cr(docs)
    if cr is None:
        return []
    containers = (
        cr.get("spec", {})
        .get("podTemplate", {})
        .get("spec", {})
        .get("containers", [])
    )
    for c in containers:
        if c.get("name") == "logstash":
            return [vm.get("mountPath", "") for vm in c.get("volumeMounts", [])]
    return []


def get_pipeline_copy_command(docs: list[dict]) -> str:
    cr = find_logstash_cr(docs)
    if cr is None:
        return ""
    init_containers = (
        cr.get("spec", {})
        .get("podTemplate", {})
        .get("spec", {})
        .get("initContainers", [])
    )
    for c in init_containers:
        if c.get("name") == "pipeline-copy":
            cmd = c.get("command", [])
            return " ".join(cmd) if isinstance(cmd, list) else str(cmd)
    return ""


def get_env_names(docs: list[dict]) -> list[str]:
    cr = find_logstash_cr(docs)
    if cr is None:
        return []
    containers = (
        cr.get("spec", {})
        .get("podTemplate", {})
        .get("spec", {})
        .get("containers", [])
    )
    for c in containers:
        if c.get("name") == "logstash":
            return [e.get("name", "") for e in c.get("env", [])]
    return []


def check_init_containers(docs: list[dict], required: list[str], absent: list[str]) -> None:
    names = get_init_container_names(docs)
    for name in required:
        if name not in names:
            raise AssertionError(f"init container {name!r} must be present but was not found in {names!r}")
    for name in absent:
        if name in names:
            raise AssertionError(f"init container {name!r} must not be present but was found in {names!r}")


def check_volumes(docs: list[dict], required: list[str], absent: list[str]) -> None:
    names = get_volume_names(docs)
    for name in required:
        if name not in names:
            raise AssertionError(f"volume {name!r} must be present but was not found in {names!r}")
    for name in absent:
        if name in names:
            raise AssertionError(f"volume {name!r} must not be present but was found in {names!r}")


def check_volume_mounts(docs: list[dict], required: list[str], absent: list[str]) -> None:
    paths = get_volume_mount_paths(docs)
    for path in required:
        if path not in paths:
            raise AssertionError(f"volumeMount {path!r} must be present but was not found in {paths!r}")
    for path in absent:
        if path in paths:
            raise AssertionError(f"volumeMount {path!r} must not be present but was found in {paths!r}")


def check_pipeline_copy_copies(docs: list[dict], expected_files: list[str]) -> None:
    """Assert that the pipeline-copy init container copies each expected file."""
    cr = find_logstash_cr(docs)
    if cr is None:
        raise AssertionError("pipeline-copy check: no Logstash CR found")
    init_containers = (
        cr.get("spec", {})
        .get("podTemplate", {})
        .get("spec", {})
        .get("initContainers", [])
    )
    copy_container = next((c for c in init_containers if c.get("name") == "pipeline-copy"), None)
    if copy_container is None:
        raise AssertionError("pipeline-copy check: pipeline-copy init container not found")
    # command is [sh, -c, <script>]
    cmd_list = copy_container.get("command", [])
    script = cmd_list[2] if len(cmd_list) >= 3 else ""
    for f in expected_files:
        if f not in script:
            raise AssertionError(f"pipeline-copy check: {f!r} not found in init container script")


def check_inline_configmaps(docs: list[dict], expected_indices: list[int]) -> None:
    """Assert that inline ConfigMaps are rendered for each expected index."""
    for idx in expected_indices:
        padded = str(idx).zfill(3)
        found = any(
            doc.get("kind") == "ConfigMap" and f"inline-{padded}" in doc.get("metadata", {}).get("name", "")
            for doc in docs
        )
        if not found:
            raise AssertionError(f"inline ConfigMap for index {idx} (inline-{padded}) not found")


def check_extra_env(docs: list[dict], required: list[str]) -> None:
    names = get_env_names(docs)
    for name in required:
        if name not in names:
            raise AssertionError(f"extraEnv {name!r} must be present but was not found in {names!r}")


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

    if "init_containers" in scenario or "absent_init_containers" in scenario:
        check_init_containers(
            docs,
            scenario.get("init_containers", []),
            scenario.get("absent_init_containers", []),
        )

    if "volumes" in scenario or "absent_volumes" in scenario:
        check_volumes(
            docs,
            scenario.get("volumes", []),
            scenario.get("absent_volumes", []),
        )

    if "volume_mount_paths" in scenario or "absent_volume_mount_paths" in scenario:
        check_volume_mounts(
            docs,
            scenario.get("volume_mount_paths", []),
            scenario.get("absent_volume_mount_paths", []),
        )

    if "pipeline_copy_files" in scenario:
        check_pipeline_copy_copies(docs, scenario["pipeline_copy_files"])

    if "inline_indices" in scenario:
        check_inline_configmaps(docs, scenario["inline_indices"])

    if "extra_env" in scenario:
        check_extra_env(docs, scenario["extra_env"])


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
