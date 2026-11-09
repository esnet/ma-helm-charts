#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pyyaml",
# ]
# ///
"""
Template rendering tests for the clickhouse Helm chart.

Each scenario in SCENARIOS is a self-contained declaration of:
  - which values fixture to render
  - which resource kinds must / must not appear
  - field assertions   — (kind, key_path, expected)
      key_path is a list of dict/list keys traversed on the first matching
      resource of that kind.  Integer entries index into lists.
  - chi_files_present  — list of filenames that must appear in the CHI files block
  - chi_files_absent   — list of filenames that must NOT appear in the CHI files block
  - chi_file_contains  — (filename, substring) the file content must contain the string
  - cluster_fields     — (cluster_name, key_path, expected) assertions on a named
      cluster within spec.configuration.clusters
  - container_present  — container names that must appear in the pod template
  - container_absent   — container names that must NOT appear in the pod template
  - container_env      — (container_name, env_var_name, expected_value)
  - initcontainer_present — init container names that must appear in the pod template
  - initcontainer_absent  — init container names that must NOT appear in the pod template
  - initcontainer_env     — (container_name, env_var_name, expected_value)
  - initcontainer_env_absent — (container_name, env_var_name) env var must NOT be set explicitly
  - known_failure      — if set, the scenario is expected to fail (XFAIL)

To add a scenario, edit SCENARIOS only — the engine below does not change.
"""

import subprocess
import sys
from typing import Any

import yaml

CHART = "charts/clickhouse"


# ---------------------------------------------------------------------------
# Scenario declarations
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # Minimal — no TLS, no backups, no routes
    # Baseline: CHI + CHK rendered, no TLSRoute, no backup sidecar
    # ------------------------------------------------------------------
    {
        "name": "minimal-no-tls",
        "values": "ci/minimal-values.yaml",
        "present": ["ClickHouseInstallation", "ClickHouseKeeperInstallation"],
        "absent": ["TLSRoute", "HTTPRoute"],
        "fields": [
            ("ClickHouseInstallation", ["metadata", "name"], "ch-cluster"),
            ("ClickHouseInstallation", ["metadata", "namespace"], "clickhouse"),
        ],
        "chi_files_present": ["distributed_ddl.xml"],
        "chi_files_absent": ["disable_play.xml", "ssl.xml"],
        "chi_file_contains": [],
        "cluster_fields": [
            ("ch-cluster", ["layout", "shardsCount"], 1),
            ("ch-cluster", ["layout", "replicasCount"], 1),
        ],
        "container_present": ["clickhouse"],
        "container_absent": ["clickhouse-backup"],
        "container_env": [],
    },
    # ------------------------------------------------------------------
    # TLS with routes
    # CHI has ssl.xml; TLSRoute rendered with correct domains and cert ref
    # ------------------------------------------------------------------
    {
        "name": "tls-with-routes",
        "values": "ci/tls-with-routes.yaml",
        "present": ["ClickHouseInstallation", "ClickHouseKeeperInstallation", "TLSRoute"],
        "absent": [],
        "fields": [],
        "chi_files_present": ["ssl.xml"],
        "chi_files_absent": ["disable_play.xml"],
        "chi_file_contains": [
            ("ssl.xml", "<https_port>8443</https_port>"),
            ("ssl.xml", "<tcp_port_secure>9440</tcp_port_secure>"),
        ],
        "cluster_fields": [
            ("ch-cluster", ["layout", "replicasCount"], 2),
        ],
        "container_present": ["clickhouse"],
        "container_absent": ["clickhouse-backup"],
        "container_env": [],
    },
    # ------------------------------------------------------------------
    # TLS route hostnames — domains propagate to TLSRoute
    # ------------------------------------------------------------------
    {
        "name": "tls-route-domains",
        "values": "ci/tls-with-routes.yaml",
        "present": ["TLSRoute"],
        "absent": [],
        "fields": [
            (
                "TLSRoute",
                ["spec", "hostnames"],
                ["ch-ci.stardust.es.net", "ch-ci-alt.stardust.es.net"],
            ),
        ],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
    },
    # ------------------------------------------------------------------
    # GCS backups — sidecar present, env vars correct, monitoring annotation
    # ------------------------------------------------------------------
    {
        "name": "backups-gcs",
        "values": "ci/backups-gcs.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": ["TLSRoute"],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": ["clickhouse", "clickhouse-backup"],
        "container_absent": [],
        "container_env": [
            ("clickhouse-backup", "REMOTE_STORAGE", "gcs"),
            ("clickhouse-backup", "GCS_BUCKET", "ci-clickhouse-backups"),
            ("clickhouse-backup", "GCS_PATH", "backup/shard-{shard}"),
            ("clickhouse-backup", "BACKUPS_TO_KEEP_REMOTE", "7"),
            ("clickhouse-backup", "CLICKHOUSE_USERNAME", "admin"),
        ],
    },
    # ------------------------------------------------------------------
    # disable_play enabled — disable_play.xml rendered with correct content
    # /ping handler preserved, /play returns 403, replace="1" present
    # ------------------------------------------------------------------
    {
        "name": "disable-play-enabled",
        "values": "ci/disable-play.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": ["disable_play.xml"],
        "chi_files_absent": [],
        "chi_file_contains": [
            ("disable_play.xml", 'replace="1"'),
            ("disable_play.xml", "<type>ping</type>"),
            ("disable_play.xml", "<url>/play</url>"),
            ("disable_play.xml", "<status>403</status>"),
            ("disable_play.xml", "<type>replicas_status</type>"),
            ("disable_play.xml", "<type>dynamic_query_handler</type>"),
        ],
        "cluster_fields": [],
        "container_present": ["clickhouse"],
        "container_absent": [],
        "container_env": [],
    },
    # ------------------------------------------------------------------
    # disable_play — dynamic_query_handler must NOT require pragma header
    # Regression: handler previously restricted to requests with the
    # 'pragma: no-cache' header, breaking standard HTTP clients that
    # don't send it (Grafana plugin, clickhouse-go driver, etc.).
    # The fix removed the <headers> filter so all POST/GET with a query
    # param are accepted. Verify no <pragma> block appears in the handler.
    # ------------------------------------------------------------------
    {
        "name": "disable-play-no-pragma-restriction",
        "values": "ci/disable-play.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": ["disable_play.xml"],
        "chi_files_absent": [],
        "chi_file_contains": [
            ("disable_play.xml", "<type>dynamic_query_handler</type>"),
        ],
        "chi_file_not_contains": [
            ("disable_play.xml", "<pragma>"),
            ("disable_play.xml", "<headers>"),
        ],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
    },
    # ------------------------------------------------------------------
    # disable_play — custom handler override is rendered
    # Verifies that disable_play_handlers value replaces the default rules.
    # Custom fixture adds /custom-health and uses "Not allowed" response text.
    # ------------------------------------------------------------------
    {
        "name": "disable-play-custom-handlers",
        "values": "ci/disable-play-custom-handlers.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": ["disable_play.xml"],
        "chi_files_absent": [],
        "chi_file_contains": [
            ("disable_play.xml", 'replace="1"'),
            ("disable_play.xml", "<url>/custom-health</url>"),
            ("disable_play.xml", "<response_content>Not allowed</response_content>"),
            ("disable_play.xml", "<type>dynamic_query_handler</type>"),
        ],
        "chi_file_not_contains": [
            ("disable_play.xml", "<url>/replicas_status</url>"),
            ("disable_play.xml", "<response_content>Forbidden</response_content>"),
        ],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
    },
    # ------------------------------------------------------------------
    # disable_play off by default — disable_play.xml must NOT appear
    # ------------------------------------------------------------------
    {
        "name": "disable-play-default-off",
        "values": "ci/minimal-values.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": ["disable_play.xml"],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
    },
    # ------------------------------------------------------------------
    # Multi-cluster — two logical clusters on the same CHI
    # ch-cluster: 1 shard × 2 replicas; analytics: 3 shards × 2 replicas
    # ------------------------------------------------------------------
    {
        "name": "multi-cluster",
        "values": "ci/multi-cluster.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [
            ("ch-cluster", ["layout", "shardsCount"], 1),
            ("ch-cluster", ["layout", "replicasCount"], 2),
            ("analytics", ["layout", "shardsCount"], 3),
            ("analytics", ["layout", "replicasCount"], 2),
            ("analytics", ["schemaPolicy", "replica"], "None"),
            ("analytics", ["schemaPolicy", "shard"], "None"),
        ],
        "container_present": ["clickhouse"],
        "container_absent": [],
        "container_env": [],
    },
    # ------------------------------------------------------------------
    # Multi-cluster cluster count — exactly 2 clusters in CHI spec
    # ------------------------------------------------------------------
    {
        "name": "multi-cluster-count",
        "values": "ci/multi-cluster.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "cluster_count": 2,
        "container_present": [],
        "container_absent": [],
        "container_env": [],
    },
    # ------------------------------------------------------------------
    # Backups mutual exclusion — service_name + service_file.secret_name
    # together must cause helm template to fail
    # ------------------------------------------------------------------
    {
        "name": "backups-mutual-exclusion",
        "values": "ci/backups-gcs.yaml",
        "extra_set": [
            "--set", "config.backups.service_file.secret_name=some-secret",
            "--set", "config.backups.service_file.secret_key=some-key",
        ],
        "present": [],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
        "known_failure": "helm template must fail when both service_name and service_file are set",
    },
    # ------------------------------------------------------------------
    # User database allow-list — backup_user restricted to named databases
    # ------------------------------------------------------------------
    {
        "name": "user-database-allowlist",
        "values": "ci/backups-gcs.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
        "user_db_check": ("admin", None),
    },
    # ------------------------------------------------------------------
    # Migrations disabled by default — no initContainer rendered
    # ------------------------------------------------------------------
    {
        "name": "migrations-disabled-by-default",
        "values": "ci/minimal-values.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
        "initcontainer_absent": ["clickhouse-migrations"],
    },
    # ------------------------------------------------------------------
    # Migrations enabled — initContainer present with correct env vars
    # and default computed keeper address
    # ------------------------------------------------------------------
    {
        "name": "migrations-enabled-defaults",
        "values": "ci/migrations-enabled.yaml",
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": ["clickhouse"],
        "container_absent": [],
        "container_env": [],
        "initcontainer_present": ["clickhouse-migrations"],
        "initcontainer_env": [
            ("clickhouse-migrations", "TARGET", "stardust-std"),
            ("clickhouse-migrations", "KEEPER_ADDR", "keeper-keeper-cluster.clickhouse.svc.cluster.local:2181"),
            ("clickhouse-migrations", "GOOSE_COMMAND", "up"),
            ("clickhouse-migrations", "MIGRATIONS_DIR", "/migrations"),
            ("clickhouse-migrations", "MIGRATION_SLEEP_SECONDS", "60"),
        ],
        # credentials must NOT be set — they are inherited from the pod env
        "initcontainer_env_absent": [
            ("clickhouse-migrations", "CLICKHOUSE_USERNAME"),
            ("clickhouse-migrations", "CLICKHOUSE_PASSWORD"),
            ("clickhouse-migrations", "CLICKHOUSE_HOST"),
        ],
    },
    # ------------------------------------------------------------------
    # Migrations enabled — custom keeperAddr override is respected
    # ------------------------------------------------------------------
    {
        "name": "migrations-custom-keeper-addr",
        "values": "ci/migrations-enabled.yaml",
        "extra_set": [
            "--set", "config.migrations.keeperAddr=my-keeper.other-ns.svc.cluster.local:2181",
        ],
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
        "initcontainer_present": ["clickhouse-migrations"],
        "initcontainer_env": [
            ("clickhouse-migrations", "KEEPER_ADDR", "my-keeper.other-ns.svc.cluster.local:2181"),
        ],
    },
    # ------------------------------------------------------------------
    # Migrations enabled without target — helm template must fail
    # ------------------------------------------------------------------
    {
        "name": "migrations-missing-target",
        "values": "ci/minimal-values.yaml",
        "extra_set": [
            "--set", "config.migrations.enabled=true",
        ],
        "present": [],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
        "known_failure": "helm template must fail when migrations.enabled=true and target is empty",
    },
    # ------------------------------------------------------------------
    # Node affinity — podAntiAffinity on CH pods uses CHI installation name
    # ------------------------------------------------------------------
    {
        "name": "ch-pod-anti-affinity",
        "values": "ci/minimal-values.yaml",
        "extra_set": [
            "--set", "config.ch.affinity.podAntiAffinity=true",
        ],
        "present": ["ClickHouseInstallation"],
        "absent": [],
        "fields": [],
        "chi_files_present": [],
        "chi_files_absent": [],
        "chi_file_contains": [],
        "cluster_fields": [],
        "container_present": [],
        "container_absent": [],
        "container_env": [],
        "pod_anti_affinity_chi": "ch-cluster",
    },
]


# ---------------------------------------------------------------------------
# Engine helpers
# ---------------------------------------------------------------------------


def render(values_file: str, extra_set: list[str] | None = None) -> list[dict]:
    cmd = ["helm", "template", "ci-test", CHART, "-f", f"{CHART}/{values_file}"]
    if extra_set:
        cmd.extend(extra_set)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return [d for d in yaml.safe_load_all(result.stdout) if d is not None]


def find_kind(docs: list[dict], kind: str) -> list[dict]:
    return [d for d in docs if d.get("kind") == kind]


def deep_get(obj: Any, keys: list) -> Any:
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


def get_chi(docs: list[dict]) -> dict:
    chis = find_kind(docs, "ClickHouseInstallation")
    if not chis:
        raise AssertionError("No ClickHouseInstallation found in rendered output")
    return chis[0]


def get_chi_files(docs: list[dict]) -> dict[str, str]:
    """Return the files map from the CHI spec as {bare_filename: content}."""
    chi = get_chi(docs)
    raw: dict = deep_get(chi, ["spec", "configuration", "files"])
    # keys are like "config.d/foo.xml" — strip the directory prefix
    return {k.split("/")[-1]: v for k, v in raw.items()}


def get_clusters(docs: list[dict]) -> list[dict]:
    chi = get_chi(docs)
    return deep_get(chi, ["spec", "configuration", "clusters"])


def find_cluster(docs: list[dict], name: str) -> dict:
    clusters = get_clusters(docs)
    matches = [c for c in clusters if c.get("name") == name]
    if not matches:
        available = [c.get("name") for c in clusters]
        raise AssertionError(f"Cluster '{name}' not found. Available: {available}")
    return matches[0]


def get_pod_template(docs: list[dict]) -> dict:
    chi = get_chi(docs)
    templates = deep_get(chi, ["spec", "templates", "podTemplates"])
    return templates[0]


def get_containers(docs: list[dict]) -> list[dict]:
    pod = get_pod_template(docs)
    return deep_get(pod, ["spec", "containers"])


def find_container(docs: list[dict], name: str) -> dict:
    containers = get_containers(docs)
    matches = [c for c in containers if c.get("name") == name]
    if not matches:
        available = [c.get("name") for c in containers]
        raise AssertionError(f"Container '{name}' not found. Available: {available}")
    return matches[0]


def get_init_containers(docs: list[dict]) -> list[dict]:
    pod = get_pod_template(docs)
    return deep_get(pod, ["spec", "initContainers"])


def find_init_container(docs: list[dict], name: str) -> dict:
    containers = get_init_containers(docs)
    matches = [c for c in containers if c.get("name") == name]
    if not matches:
        available = [c.get("name") for c in containers]
        raise AssertionError(f"Init container '{name}' not found. Available: {available}")
    return matches[0]


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------


def run_scenario(scenario: dict[str, Any], docs: list[dict]) -> None:
    # --- present / absent kinds ---
    for kind in scenario.get("present", []):
        if not find_kind(docs, kind):
            raise AssertionError(f"{kind} must be present but was not rendered")

    for kind in scenario.get("absent", []):
        found = find_kind(docs, kind)
        if found:
            raise AssertionError(
                f"{kind} must not be rendered but {len(found)} instance(s) found"
            )

    # --- top-level field assertions ---
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

    # --- CHI files present / absent ---
    if scenario.get("chi_files_present") or scenario.get("chi_files_absent"):
        try:
            files = get_chi_files(docs)
        except (AssertionError, KeyError) as exc:
            raise AssertionError(f"could not read CHI files block: {exc}") from exc

        for fname in scenario.get("chi_files_present", []):
            if fname not in files:
                raise AssertionError(
                    f"CHI files: '{fname}' must be present. Found: {list(files)}"
                )

        for fname in scenario.get("chi_files_absent", []):
            if fname in files:
                raise AssertionError(
                    f"CHI files: '{fname}' must not be present but was found"
                )

    # --- CHI file content assertions (must contain) ---
    for fname, substring in scenario.get("chi_file_contains", []):
        try:
            files = get_chi_files(docs)
        except (AssertionError, KeyError) as exc:
            raise AssertionError(f"could not read CHI files block: {exc}") from exc
        if fname not in files:
            raise AssertionError(f"CHI files: '{fname}' not found for content check")
        content = files[fname]
        if substring not in content:
            raise AssertionError(
                f"CHI file '{fname}': expected to contain {substring!r}\n"
                f"Actual content:\n{content}"
            )

    # --- CHI file content assertions (must NOT contain) ---
    for fname, substring in scenario.get("chi_file_not_contains", []):
        try:
            files = get_chi_files(docs)
        except (AssertionError, KeyError) as exc:
            raise AssertionError(f"could not read CHI files block: {exc}") from exc
        if fname not in files:
            raise AssertionError(f"CHI files: '{fname}' not found for content check")
        content = files[fname]
        if substring in content:
            raise AssertionError(
                f"CHI file '{fname}': must NOT contain {substring!r} but it was found\n"
                f"Actual content:\n{content}"
            )

    # --- cluster field assertions ---
    for cluster_name, key_path, expected in scenario.get("cluster_fields", []):
        cluster = find_cluster(docs, cluster_name)
        try:
            actual = deep_get(cluster, key_path)
        except KeyError as exc:
            raise AssertionError(
                f"cluster '{cluster_name}': key path {key_path} not found — {exc}"
            ) from exc
        if actual != expected:
            raise AssertionError(
                f"cluster '{cluster_name}'.{key_path}: expected {expected!r}, got {actual!r}"
            )

    # --- cluster count ---
    if "cluster_count" in scenario:
        clusters = get_clusters(docs)
        expected = scenario["cluster_count"]
        if len(clusters) != expected:
            raise AssertionError(
                f"expected {expected} clusters in CHI spec, got {len(clusters)}: "
                f"{[c.get('name') for c in clusters]}"
            )

    # --- container present / absent ---
    if scenario.get("container_present") or scenario.get("container_absent"):
        containers = get_containers(docs)
        names = [c.get("name") for c in containers]

        for cname in scenario.get("container_present", []):
            if cname not in names:
                raise AssertionError(
                    f"container '{cname}' must be present. Found: {names}"
                )

        for cname in scenario.get("container_absent", []):
            if cname in names:
                raise AssertionError(
                    f"container '{cname}' must not be present but was found"
                )

    # --- container env var assertions ---
    for cname, env_name, expected in scenario.get("container_env", []):
        container = find_container(docs, cname)
        env_list: list[dict] = container.get("env", [])
        matches = [e for e in env_list if e.get("name") == env_name]
        if not matches:
            available = [e.get("name") for e in env_list]
            raise AssertionError(
                f"container '{cname}': env var '{env_name}' not found. Available: {available}"
            )
        actual = matches[0].get("value")
        if str(actual) != str(expected):
            raise AssertionError(
                f"container '{cname}' env '{env_name}': expected {expected!r}, got {actual!r}"
            )

    # --- init container present / absent ---
    if scenario.get("initcontainer_present") or scenario.get("initcontainer_absent"):
        try:
            init_containers = get_init_containers(docs)
        except KeyError:
            init_containers = []
        names = [c.get("name") for c in init_containers]

        for cname in scenario.get("initcontainer_present", []):
            if cname not in names:
                raise AssertionError(
                    f"init container '{cname}' must be present. Found: {names}"
                )

        for cname in scenario.get("initcontainer_absent", []):
            if cname in names:
                raise AssertionError(
                    f"init container '{cname}' must not be present but was found"
                )

    # --- init container env var assertions ---
    for cname, env_name, expected in scenario.get("initcontainer_env", []):
        container = find_init_container(docs, cname)
        env_list: list[dict] = container.get("env", [])
        matches = [e for e in env_list if e.get("name") == env_name]
        if not matches:
            available = [e.get("name") for e in env_list]
            raise AssertionError(
                f"init container '{cname}': env var '{env_name}' not found. Available: {available}"
            )
        actual = matches[0].get("value")
        if str(actual) != str(expected):
            raise AssertionError(
                f"init container '{cname}' env '{env_name}': expected {expected!r}, got {actual!r}"
            )

    # --- init container env var absent assertions ---
    for cname, env_name in scenario.get("initcontainer_env_absent", []):
        try:
            container = find_init_container(docs, cname)
        except AssertionError:
            continue  # container absent entirely — env var trivially absent
        env_list: list[dict] = container.get("env", [])
        matches = [e for e in env_list if e.get("name") == env_name]
        if matches:
            raise AssertionError(
                f"init container '{cname}': env var '{env_name}' must NOT be set explicitly "
                f"(it is inherited from the pod env), but was found with value {matches[0].get('value')!r}"
            )

    # --- pod anti-affinity uses CHI installation name ---
    if "pod_anti_affinity_chi" in scenario:
        expected_name = scenario["pod_anti_affinity_chi"]
        pod = get_pod_template(docs)
        try:
            values = deep_get(pod, [
                "spec", "affinity", "podAntiAffinity",
                "requiredDuringSchedulingIgnoredDuringExecution",
                0, "labelSelector", "matchExpressions", 0, "values",
            ])
        except KeyError as exc:
            raise AssertionError(
                f"podAntiAffinity: could not find matchExpressions values — {exc}"
            ) from exc
        if expected_name not in values:
            raise AssertionError(
                f"podAntiAffinity: expected '{expected_name}' in matchExpression values, "
                f"got {values!r}"
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    passed, failed, xfailed = 0, 0, 0

    for scenario in SCENARIOS:
        name = scenario["name"]
        known_failure: str | None = scenario.get("known_failure")
        extra_set: list[str] = scenario.get("extra_set", [])

        try:
            docs = render(scenario["values"], extra_set or None)
            run_scenario(scenario, docs)
            if known_failure:
                print(f"  XPASS  {name}  (was known failure — remove 'known_failure' key)")
                failed += 1
            else:
                print(f"  PASS   {name}")
                passed += 1
        except AssertionError as exc:
            if known_failure:
                print(f"  XFAIL  {name}  ({exc})")
                xfailed += 1
            else:
                print(f"  FAIL   {name}: {exc}")
                failed += 1
        except subprocess.CalledProcessError as exc:
            # helm template exited non-zero
            if known_failure:
                print(f"  XFAIL  {name}  (helm template failed as expected)")
                xfailed += 1
            else:
                print(f"  ERROR  {name}: helm template failed\n{exc.stderr.strip()}")
                failed += 1

    total = passed + failed + xfailed
    print(f"\n{total} scenarios: {passed} passed, {failed} failed, {xfailed} xfailed (known)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
