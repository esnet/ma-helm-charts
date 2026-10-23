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
  - optional helm_fail: expected substring in helm template's stderr (for hard-fail tests)

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
#   name         – unique label shown in test output
#   values       – path to values fixture relative to CHART (omit for helm_fail tests
#                  that pass --set flags directly via extra_args)
#   extra_args   – optional list of extra helm template args (e.g. --set flags)
#   present      – resource kinds that must appear at least once
#   absent       – resource kinds that must not appear
#   fields       – field assertions as (kind, key_path, expected_value) tuples
#                  key_path is a list of dict/list keys to traverse on the first
#                  matching resource of that kind
#   helm_fail    – if set, helm template is expected to fail and this string must
#                  appear in stderr; no present/absent/fields assertions are run
#   known_failure – optional string; marks an expected failure (XFAIL)

SCENARIOS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # Minimal — no transforms, namespace created
    # ------------------------------------------------------------------
    {
        "name": "minimal-renders-all-resources",
        "values": "ci/minimal-values.yaml",
        "present": ["Namespace", "ConfigMap", "Logstash"],
        "absent": ["ExternalSecret"],
        "fields": [
            ("Namespace", ["metadata", "name"], "bmp-pipeline"),
            ("Logstash", ["spec", "count"], 1),
        ],
    },
    # ------------------------------------------------------------------
    # Namespace not created when create_ns: false
    # ------------------------------------------------------------------
    {
        "name": "no-namespace-resource-when-create-ns-false",
        "values": "ci/no-create-ns-values.yaml",
        "present": ["ConfigMap", "Logstash"],
        "absent": ["Namespace", "ExternalSecret"],
        "fields": [],
    },
    # ------------------------------------------------------------------
    # Inputs ConfigMap — filename key follows prefix-001 convention
    # ------------------------------------------------------------------
    {
        "name": "inputs-configmap-key-naming",
        "values": "ci/minimal-values.yaml",
        "present": ["ConfigMap"],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "bmp-001-inputs.conf", "kafka"),
        ],
    },
    # ------------------------------------------------------------------
    # Outputs ConfigMap — filename key follows prefix-999 convention
    # ------------------------------------------------------------------
    {
        "name": "outputs-configmap-key-naming",
        "values": "ci/minimal-values.yaml",
        "present": ["ConfigMap"],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "bmp-999-outputs.conf", "elasticsearch"),
        ],
    },
    # ------------------------------------------------------------------
    # Outputs ConfigMap — ES 9.x SSL syntax (no legacy ssl/cacert keys)
    # ------------------------------------------------------------------
    {
        "name": "outputs-uses-logstash-9x-ssl-syntax",
        "values": "ci/minimal-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "content_checks": [
            # Must use new syntax
            ("ConfigMap", "bmp-999-outputs.conf", "ssl_enabled => true"),
            ("ConfigMap", "bmp-999-outputs.conf", "ssl_certificate_authorities"),
            ("ConfigMap", "bmp-999-outputs.conf", "ssl_verification_mode"),
            # Must NOT use old syntax
        ],
        "content_absent": [
            ("ConfigMap", "bmp-999-outputs.conf", 'ssl => "true"'),
            ("ConfigMap", "bmp-999-outputs.conf", "cacert =>"),
            ("ConfigMap", "bmp-999-outputs.conf", "ssl_certificate_verification"),
        ],
    },
    # ------------------------------------------------------------------
    # Outputs ConfigMap — ssl_certificate_authorities omitted when cacert unset
    # ------------------------------------------------------------------
    {
        "name": "outputs-omits-ssl-cert-authorities-when-cacert-unset",
        "values": "ci/no-create-ns-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "bmp-999-outputs.conf", "ssl_enabled => true"),
            ("ConfigMap", "bmp-999-outputs.conf", "ssl_verification_mode"),
        ],
        "content_absent": [
            ("ConfigMap", "bmp-999-outputs.conf", "ssl_certificate_authorities"),
        ],
    },
    # ------------------------------------------------------------------
    # Inputs ConfigMap — SASL auth (no SSL keystore keys)
    # ------------------------------------------------------------------
    {
        "name": "inputs-uses-sasl-not-ssl-keystore",
        "values": "ci/minimal-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "bmp-001-inputs.conf", "SASL_SSL"),
            ("ConfigMap", "bmp-001-inputs.conf", "SCRAM-SHA-512"),
            ("ConfigMap", "bmp-001-inputs.conf", "sasl_jaas_config"),
        ],
        "content_absent": [
            ("ConfigMap", "bmp-001-inputs.conf", "ssl_keystore_location"),
            ("ConfigMap", "bmp-001-inputs.conf", 'security_protocol => "SSL"'),
        ],
    },
    # ------------------------------------------------------------------
    # No hardcoded secrets in outputs
    # ------------------------------------------------------------------
    {
        "name": "outputs-no-hardcoded-credentials",
        "values": "ci/minimal-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "bmp-999-outputs.conf", "${elastic_user}"),
            ("ConfigMap", "bmp-999-outputs.conf", "${elastic_password}"),
        ],
        "content_absent": [],
    },
    # ------------------------------------------------------------------
    # Transforms — pipeline volume order (inputs → transforms → outputs)
    # ------------------------------------------------------------------
    {
        "name": "pipeline-volume-order-inputs-transforms-outputs",
        "values": "ci/with-transforms-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "pipeline_volume_order": ["test-release-inputs", "bmp-initial-format", "bmp-afi-safi", "bmp-dns", "test-release-outputs"],
    },
    # ------------------------------------------------------------------
    # Transforms declared out-of-order are sorted by index in pipeline volumes
    # ------------------------------------------------------------------
    {
        "name": "transforms-sorted-by-index",
        "values": "ci/out-of-order-transforms-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "pipeline_volume_order": ["test-release-inputs", "bmp-initial-format", "bmp-afi-safi", "bmp-dns", "test-release-outputs"],
    },
    # ------------------------------------------------------------------
    # Multi-host ES — all hosts appear in outputs ConfigMap
    # ------------------------------------------------------------------
    {
        "name": "multi-host-elasticsearch",
        "values": "ci/with-transforms-values.yaml",
        "present": ["ConfigMap"],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "bmp-999-outputs.conf", "34.136.91.137"),
            ("ConfigMap", "bmp-999-outputs.conf", "35.223.57.250"),
            ("ConfigMap", "bmp-999-outputs.conf", "35.202.182.99"),
        ],
        "content_absent": [],
    },
    # ------------------------------------------------------------------
    # Replica count is reflected in the Logstash CR
    # ------------------------------------------------------------------
    {
        "name": "replica-count",
        "values": "ci/with-transforms-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [
            ("Logstash", ["spec", "count"], 3),
        ],
    },
    # ------------------------------------------------------------------
    # JVM heap is reflected in the jvm-options ConfigMap
    # ------------------------------------------------------------------
    {
        "name": "jvm-heap-settings",
        "values": "ci/with-transforms-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "jvm.options", "-Xms16g"),
            ("ConfigMap", "jvm.options", "-Xmx16g"),
        ],
        "content_absent": [],
    },
    # ------------------------------------------------------------------
    # Chart does not create a Secret or ExternalSecret — credentials.secretName
    # must be referenced as-is via envFrom
    # ------------------------------------------------------------------
    {
        "name": "no-externalsecret-rendered",
        "values": "ci/minimal-values.yaml",
        "present": ["Logstash"],
        "absent": ["ExternalSecret"],
        "fields": [
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 0, "envFrom", 0, "secretRef", "name"],
                "bmp-pipeline-credentials",
            ),
        ],
    },
    # ------------------------------------------------------------------
    # tlsCertExtractor disabled by default — no initContainers, no tls-certs volume
    # ------------------------------------------------------------------
    {
        "name": "tls-extractor-disabled-by-default",
        "values": "ci/minimal-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "init_containers_absent": True,
        "volume_absent": "tls-certs",
    },
    # ------------------------------------------------------------------
    # tlsCertExtractor enabled — initContainers block present with correct image
    # ------------------------------------------------------------------
    {
        "name": "tls-extractor-enabled-renders-init-container",
        "values": "ci/with-tls-extractor-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "initContainers", 0, "name"],
                "tls-cert-extractor",
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "initContainers", 0, "image"],
                "us-central1-docker.pkg.dev/ma-infrastructure-474617/docker-registry/k8s-cert-helper:1.37.1",
            ),
        ],
    },
    # ------------------------------------------------------------------
    # tlsCertExtractor enabled — tls-certs emptyDir volume present
    # ------------------------------------------------------------------
    {
        "name": "tls-extractor-enabled-renders-emptydir-volume",
        "values": "ci/with-tls-extractor-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "volume_present": "tls-certs",
    },
    # ------------------------------------------------------------------
    # tlsCertExtractor enabled — init container mounts tls-certs volume
    # ------------------------------------------------------------------
    {
        "name": "tls-extractor-init-container-mounts-certs-volume",
        "values": "ci/with-tls-extractor-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "initContainers", 0, "volumeMounts", 0, "name"],
                "tls-certs",
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "initContainers", 0, "volumeMounts", 0, "mountPath"],
                "/certs",
            ),
        ],
    },
    # ------------------------------------------------------------------
    # tlsCertExtractor enabled — Logstash container mounts tls-certs volume read-only
    # ------------------------------------------------------------------
    {
        "name": "tls-extractor-logstash-container-mounts-certs-volume-readonly",
        "values": "ci/with-tls-extractor-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "logstash_certs_mount": {"name": "tls-certs", "mountPath": "/certs", "readOnly": True},
    },
    # ------------------------------------------------------------------
    # tlsCertExtractor enabled — init container script references host and port
    # ------------------------------------------------------------------
    {
        "name": "tls-extractor-script-contains-host-and-port",
        "values": "ci/with-tls-extractor-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "init_container_script_contains": ["kafka.example.com", "9095", "openssl s_client", "keytool -importcert", "pipefail", "chmod 644", "! -s ", "BEGIN CERTIFICATE", "TrustedCertificateEntry"],
    },
    # ------------------------------------------------------------------
    # kafka.ssl enabled — truststore settings rendered in inputs ConfigMap
    # ------------------------------------------------------------------
    {
        "name": "kafka-ssl-enabled-renders-truststore-in-inputs",
        "values": "ci/with-tls-extractor-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "bmp-001-inputs.conf", "ssl_truststore_location"),
            ("ConfigMap", "bmp-001-inputs.conf", "/certs/ca.p12"),
            ("ConfigMap", "bmp-001-inputs.conf", 'ssl_truststore_type => "PKCS12"'),
            ("ConfigMap", "bmp-001-inputs.conf", "ssl_endpoint_identification_algorithm"),
            ("ConfigMap", "bmp-001-inputs.conf", 'ssl_truststore_password => "public-nosecret"'),
        ],
        "content_absent": [],
    },
    # ------------------------------------------------------------------
    # kafka.ssl disabled — no truststore settings in inputs ConfigMap
    # ------------------------------------------------------------------
    {
        "name": "kafka-ssl-disabled-omits-truststore-from-inputs",
        "values": "ci/minimal-values.yaml",
        "present": [],
        "absent": [],
        "fields": [],
        "content_absent": [
            ("ConfigMap", "bmp-001-inputs.conf", "ssl_truststore_location"),
            ("ConfigMap", "bmp-001-inputs.conf", "ssl_truststore_type"),
            ("ConfigMap", "bmp-001-inputs.conf", "ssl_endpoint_identification_algorithm"),
        ],
    },
    # ------------------------------------------------------------------
    # liveness probe rendered when tlsCertExtractor and livenessProbe enabled
    # ------------------------------------------------------------------
    {
        "name": "tls-extractor-liveness-probe-rendered-when-enabled",
        "values": "ci/with-tls-extractor-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 0, "livenessProbe", "initialDelaySeconds"],
                120,
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 0, "livenessProbe", "periodSeconds"],
                3600,
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 0, "livenessProbe", "failureThreshold"],
                1,
            ),
        ],
        "liveness_probe_script_contains": [
            "openssl s_client",
            "openssl x509",
            "fingerprint",
            "kafka.example.com",
            "9095",
            "subject",
            "issuer",
            "/tmp/probe-cert-",
            "/tmp/disk-cert-",
            "LIVE_CA_FP",
            "DISK_CA_FP",
        ],
    },
    # ------------------------------------------------------------------
    # liveness probe absent when tlsCertExtractor disabled
    # ------------------------------------------------------------------
    {
        "name": "liveness-probe-absent-when-extractor-disabled",
        "values": "ci/minimal-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "liveness_probe_absent": True,
    },
    # ------------------------------------------------------------------
    # liveness probe absent when livenessProbe.enabled is false
    # ------------------------------------------------------------------
    {
        "name": "liveness-probe-absent-when-probe-disabled",
        "extra_args": [
            "-f", f"{CHART}/ci/with-tls-extractor-values.yaml",
            "--set", "tlsCertExtractor.livenessProbe.enabled=false",
        ],
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "liveness_probe_absent": True,
    },
    # ------------------------------------------------------------------
    # kafka.ssl.truststorePassword rendered only when non-empty
    # ------------------------------------------------------------------
    {
        "name": "kafka-ssl-truststore-password-rendered-when-set",
        "extra_args": [
            "-f", f"{CHART}/ci/with-tls-extractor-values.yaml",
            "--set", "kafka.ssl.truststorePassword=supersecret",
        ],
        "present": [],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "bmp-001-inputs.conf", 'ssl_truststore_password => "supersecret"'),
        ],
        "content_absent": [],
    },
    # ------------------------------------------------------------------
    # monitoring.metricbeat disabled by default — no metricbeat sidecar,
    # no metricbeat ConfigMap, no metricbeat volumes
    # ------------------------------------------------------------------
    {
        "name": "metricbeat-disabled-by-default",
        "values": "ci/minimal-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "metricbeat_sidecar_absent": True,
        "metricbeat_configmap_absent": True,
        "metricbeat_volumes_absent": True,
    },
    # ------------------------------------------------------------------
    # monitoring.metricbeat enabled — metricbeat ConfigMap rendered
    # ------------------------------------------------------------------
    {
        "name": "metricbeat-enabled-renders-configmap",
        "values": "ci/with-metricbeat-values.yaml",
        "present": ["ConfigMap"],
        "absent": [],
        "fields": [],
        "content_checks": [
            ("ConfigMap", "metricbeat.yml", "module: logstash"),
            ("ConfigMap", "metricbeat.yml", "xpack.enabled: true"),
            ("ConfigMap", "metricbeat.yml", "https://localhost:9600"),
            ("ConfigMap", "metricbeat.yml", "ssl.verification_mode: none"),
            ("ConfigMap", "metricbeat.yml", "${MONITOR_ES_USERNAME}"),
            ("ConfigMap", "metricbeat.yml", "${MONITOR_ES_PASSWORD}"),
            ("ConfigMap", "metricbeat.yml", "https://el.gc1.mgt.stardust.es.net:9200"),
            ("ConfigMap", "metricbeat.yml", "node_stats"),
        ],
        "content_absent": [],
    },
    # ------------------------------------------------------------------
    # monitoring.metricbeat enabled — sidecar container rendered in pod
    # ------------------------------------------------------------------
    {
        "name": "metricbeat-enabled-renders-sidecar",
        "values": "ci/with-metricbeat-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 1, "name"],
                "metricbeat",
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 1, "image"],
                "docker.elastic.co/beats/metricbeat:8.19.8",
            ),
        ],
    },
    # ------------------------------------------------------------------
    # monitoring.metricbeat enabled — credentials sourced from
    # credentials.secretName via secretKeyRef (not envFrom)
    # ------------------------------------------------------------------
    {
        "name": "metricbeat-credentials-from-secret",
        "values": "ci/with-metricbeat-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 1, "env", 0, "name"],
                "MONITOR_ES_USERNAME",
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 1, "env", 0, "valueFrom", "secretKeyRef", "name"],
                "bmp-pipeline-credentials",
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 1, "env", 0, "valueFrom", "secretKeyRef", "key"],
                "monitor_es_username",
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 1, "env", 1, "name"],
                "MONITOR_ES_PASSWORD",
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 1, "env", 1, "valueFrom", "secretKeyRef", "key"],
                "monitor_es_password",
            ),
        ],
    },
    # ------------------------------------------------------------------
    # monitoring.metricbeat enabled — emptyDir data volume and config
    # volume present; metricbeat-config mounted into sidecar
    # ------------------------------------------------------------------
    {
        "name": "metricbeat-enabled-renders-volumes",
        "values": "ci/with-metricbeat-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "volume_present": "metricbeat-data",
        "metricbeat_config_volume_present": True,
    },
    # ------------------------------------------------------------------
    # monitoring.metricbeat clusterName — add_fields processor rendered
    # with CLUSTER_NAME env var on sidecar and in ConfigMap
    # ------------------------------------------------------------------
    {
        "name": "metricbeat-cluster-name-rendered",
        "values": "ci/with-metricbeat-values.yaml",
        "present": ["Logstash"],
        "absent": [],
        "fields": [
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 1, "env", 2, "name"],
                "CLUSTER_NAME",
            ),
            (
                "Logstash",
                ["spec", "podTemplate", "spec", "containers", 1, "env", 2, "value"],
                "bmp-staging",
            ),
        ],
        "content_checks": [
            ("ConfigMap", "metricbeat.yml", "orchestrator.cluster.name"),
            ("ConfigMap", "metricbeat.yml", "${CLUSTER_NAME}"),
        ],
        "content_absent": [],
    },
    # ------------------------------------------------------------------
    # monitoring.metricbeat clusterName empty — add_fields processor
    # and CLUSTER_NAME env var omitted
    # ------------------------------------------------------------------
    {
        "name": "metricbeat-cluster-name-omitted-when-empty",
        "extra_args": [
            "-f", f"{CHART}/ci/with-metricbeat-values.yaml",
            "--set", "monitoring.metricbeat.clusterName=",
        ],
        "present": ["Logstash"],
        "absent": [],
        "fields": [],
        "content_absent": [
            ("ConfigMap", "metricbeat.yml", "orchestrator.cluster.name"),
            ("ConfigMap", "metricbeat.yml", "${CLUSTER_NAME}"),
        ],
    },
    # ------------------------------------------------------------------
    # Hard-fail: transform index 1 is reserved (inputs slot)
    # ------------------------------------------------------------------
    {
        "name": "hard-fail-index-1-reserved",
        "extra_args": [
            "-f", f"{CHART}/ci/minimal-values.yaml",
            "--set", "pipeline.transforms[0].index=1",
            "--set", "pipeline.transforms[0].configMap=bad-cm",
        ],
        "helm_fail": "transform index 1 is reserved (001 = inputs)",
    },
    # ------------------------------------------------------------------
    # Hard-fail: transform index 999 is reserved (outputs slot)
    # ------------------------------------------------------------------
    {
        "name": "hard-fail-index-999-reserved",
        "extra_args": [
            "-f", f"{CHART}/ci/minimal-values.yaml",
            "--set", "pipeline.transforms[0].index=999",
            "--set", "pipeline.transforms[0].configMap=bad-cm",
        ],
        "helm_fail": "transform index 999 is reserved (999 = outputs)",
    },
    # ------------------------------------------------------------------
    # Hard-fail: transform index exceeds 3-digit max
    # ------------------------------------------------------------------
    {
        "name": "hard-fail-index-exceeds-max",
        "extra_args": [
            "-f", f"{CHART}/ci/minimal-values.yaml",
            "--set", "pipeline.transforms[0].index=1000",
            "--set", "pipeline.transforms[0].configMap=bad-cm",
        ],
        "helm_fail": "reserved (999 = outputs)",
    },
]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def render(values_file: str | None, extra_args: list[str] | None = None) -> tuple[list[dict], str, int]:
    cmd = ["helm", "template", "test-release", CHART]
    if values_file:
        cmd += ["-f", f"{CHART}/{values_file}"]
    if extra_args:
        cmd += extra_args
    result = subprocess.run(cmd, capture_output=True, text=True)
    docs = [d for d in yaml.safe_load_all(result.stdout) if d is not None]
    return docs, result.stderr, result.returncode


def find_all(docs: list[dict], kind: str) -> list[dict]:
    return [d for d in docs if d.get("kind") == kind]


def deep_get(obj: Any, keys: list) -> Any:
    for key in keys:
        if isinstance(obj, list):
            obj = obj[key]
        elif isinstance(obj, dict):
            obj = obj[key]
        else:
            raise KeyError(f"expected dict or list at {key!r}, got {type(obj).__name__}")
    return obj


def find_configmap_with_key(docs: list[dict], data_key: str) -> dict | None:
    for doc in find_all(docs, "ConfigMap"):
        if data_key in (doc.get("data") or {}):
            return doc
    return None


def run_scenario(scenario: dict[str, Any], docs: list[dict]) -> None:
    for kind in scenario.get("present", []):
        if not find_all(docs, kind):
            raise AssertionError(f"{kind} must be present but was not rendered")

    for kind in scenario.get("absent", []):
        found = find_all(docs, kind)
        if found:
            raise AssertionError(
                f"{kind} must not be rendered but {len(found)} instance(s) found"
            )

    for kind, key_path, expected in scenario.get("fields", []):
        matches = find_all(docs, kind)
        if not matches:
            raise AssertionError(f"field check on {kind}: no resource of that kind found")
        try:
            actual = deep_get(matches[0], key_path)
        except (KeyError, IndexError) as exc:
            if expected is None:
                # sentinel: key just needs to exist — it not existing is the failure
                raise AssertionError(
                    f"{kind}: key path {key_path} not found — {exc}"
                ) from exc
            raise AssertionError(f"{kind}: key path {key_path} not found — {exc}") from exc
        if expected is not None and actual != expected:
            path_label = ".".join(str(k) for k in key_path)
            raise AssertionError(
                f"{kind}.{path_label}: expected {expected!r}, got {actual!r}"
            )

    for kind, data_key, needle in scenario.get("content_checks", []):
        cm = find_configmap_with_key(docs, data_key)
        if cm is None:
            raise AssertionError(
                f"content check: no ConfigMap with data key {data_key!r} found"
            )
        content = cm["data"][data_key]
        if needle not in content:
            raise AssertionError(
                f"ConfigMap[{data_key!r}]: expected to find {needle!r} in content"
            )

    for kind, data_key, needle in scenario.get("content_absent", []):
        cm = find_configmap_with_key(docs, data_key)
        if cm is None:
            continue  # key doesn't exist at all — absence confirmed
        content = cm["data"][data_key]
        if needle in content:
            raise AssertionError(
                f"ConfigMap[{data_key!r}]: {needle!r} must not appear in content"
            )

    expected_order = scenario.get("pipeline_volume_order")
    if expected_order:
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError("pipeline_volume_order check: no Logstash resource found")
        volumes = logstash_docs[0]["spec"]["podTemplate"]["spec"]["volumes"]
        actual_names = [v["configMap"]["name"] for v in volumes]
        if actual_names != expected_order:
            raise AssertionError(
                f"pipeline volume order mismatch:\n  expected: {expected_order}\n  actual:   {actual_names}"
            )

    if scenario.get("init_containers_absent"):
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError("init_containers_absent check: no Logstash resource found")
        pod_spec = logstash_docs[0]["spec"]["podTemplate"]["spec"]
        if "initContainers" in pod_spec and pod_spec["initContainers"]:
            raise AssertionError("initContainers must not be present but was rendered")

    volume_absent = scenario.get("volume_absent")
    if volume_absent:
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError(f"volume_absent check: no Logstash resource found")
        volumes = logstash_docs[0]["spec"]["podTemplate"]["spec"].get("volumes", [])
        names = [v.get("name") for v in volumes]
        if volume_absent in names:
            raise AssertionError(f"volume {volume_absent!r} must not be present but was rendered")

    volume_present = scenario.get("volume_present")
    if volume_present:
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError(f"volume_present check: no Logstash resource found")
        volumes = logstash_docs[0]["spec"]["podTemplate"]["spec"].get("volumes", [])
        names = [v.get("name") for v in volumes]
        if volume_present not in names:
            raise AssertionError(f"volume {volume_present!r} must be present but was not rendered")

    logstash_certs_mount = scenario.get("logstash_certs_mount")
    if logstash_certs_mount:
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError("logstash_certs_mount check: no Logstash resource found")
        containers = logstash_docs[0]["spec"]["podTemplate"]["spec"]["containers"]
        logstash_container = next((c for c in containers if c["name"] == "logstash"), None)
        if logstash_container is None:
            raise AssertionError("logstash_certs_mount check: no container named 'logstash' found")
        mounts = logstash_container.get("volumeMounts", [])
        for mount in mounts:
            if all(mount.get(k) == v for k, v in logstash_certs_mount.items()):
                break
        else:
            raise AssertionError(
                f"logstash container volumeMounts: expected mount {logstash_certs_mount!r} not found\n"
                f"  actual mounts: {mounts}"
            )

    init_script_needles = scenario.get("init_container_script_contains")
    if init_script_needles:
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError("init_container_script_contains check: no Logstash resource found")
        init_containers = logstash_docs[0]["spec"]["podTemplate"]["spec"].get("initContainers", [])
        if not init_containers:
            raise AssertionError("init_container_script_contains check: no initContainers found")
        script = " ".join(init_containers[0].get("command", []))
        for needle in init_script_needles:
            if needle not in script:
                raise AssertionError(
                    f"init container script: expected to find {needle!r} in command"
                )

    liveness_probe_script_needles = scenario.get("liveness_probe_script_contains")
    if liveness_probe_script_needles:
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError("liveness_probe_script_contains check: no Logstash resource found")
        containers = logstash_docs[0]["spec"]["podTemplate"]["spec"]["containers"]
        logstash_container = next((c for c in containers if c["name"] == "logstash"), None)
        if logstash_container is None:
            raise AssertionError("liveness_probe_script_contains check: no container named 'logstash' found")
        probe = logstash_container.get("livenessProbe")
        if not probe:
            raise AssertionError("liveness_probe_script_contains check: no livenessProbe found")
        script = " ".join(probe.get("exec", {}).get("command", []))
        for needle in liveness_probe_script_needles:
            if needle not in script:
                raise AssertionError(
                    f"liveness probe script: expected to find {needle!r} in command"
                )

    if scenario.get("liveness_probe_absent"):
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError("liveness_probe_absent check: no Logstash resource found")
        containers = logstash_docs[0]["spec"]["podTemplate"]["spec"]["containers"]
        logstash_container = next((c for c in containers if c["name"] == "logstash"), None)
        if logstash_container is None:
            raise AssertionError("liveness_probe_absent check: no container named 'logstash' found")
        if "livenessProbe" in logstash_container:
            raise AssertionError("livenessProbe must not be present but was rendered")

    if scenario.get("metricbeat_sidecar_absent"):
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError("metricbeat_sidecar_absent check: no Logstash resource found")
        containers = logstash_docs[0]["spec"]["podTemplate"]["spec"]["containers"]
        mb = next((c for c in containers if c.get("name") == "metricbeat"), None)
        if mb is not None:
            raise AssertionError("metricbeat sidecar must not be present but was rendered")

    if scenario.get("metricbeat_configmap_absent"):
        cms = find_all(docs, "ConfigMap")
        if any("metricbeat" in (cm.get("metadata", {}).get("name", "")) for cm in cms):
            raise AssertionError("metricbeat ConfigMap must not be present but was rendered")

    if scenario.get("metricbeat_volumes_absent"):
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError("metricbeat_volumes_absent check: no Logstash resource found")
        volumes = logstash_docs[0]["spec"]["podTemplate"]["spec"].get("volumes", [])
        names = [v.get("name", "") for v in volumes]
        for vname in ("metricbeat-data", "metricbeat-config"):
            if vname in names:
                raise AssertionError(f"volume {vname!r} must not be present but was rendered")

    if scenario.get("metricbeat_config_volume_present"):
        logstash_docs = find_all(docs, "Logstash")
        if not logstash_docs:
            raise AssertionError("metricbeat_config_volume_present check: no Logstash resource found")
        volumes = logstash_docs[0]["spec"]["podTemplate"]["spec"].get("volumes", [])
        names = [v.get("name", "") for v in volumes]
        if "metricbeat-config" not in names:
            raise AssertionError("volume 'metricbeat-config' must be present but was not rendered")


def main() -> None:
    passed, failed, xfailed = 0, 0, 0

    for scenario in SCENARIOS:
        name = scenario["name"]
        known_failure: str | None = scenario.get("known_failure")
        helm_fail: str | None = scenario.get("helm_fail")
        values = scenario.get("values")
        extra_args = scenario.get("extra_args")

        try:
            docs, stderr, returncode = render(values, extra_args)

            if helm_fail:
                if returncode != 0 and helm_fail in stderr:
                    print(f"  PASS   {name}  (helm hard-failed as expected)")
                    passed += 1
                elif returncode != 0:
                    print(
                        f"  FAIL   {name}: helm failed but stderr did not contain {helm_fail!r}\n"
                        f"         stderr: {stderr.strip()}"
                    )
                    failed += 1
                else:
                    print(f"  FAIL   {name}: expected helm failure but it succeeded")
                    failed += 1
                continue

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

        except Exception as e:
            print(f"  ERROR  {name}: unexpected exception: {e}")
            failed += 1

    total = passed + failed + xfailed
    print(
        f"\n{total} scenarios: {passed} passed, {failed} failed, {xfailed} xfailed (known)"
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
