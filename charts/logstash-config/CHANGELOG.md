# Changelog

## [0.0.1]

- Initial release
- ECK-managed Logstash CR with generic input/output ConfigMaps
- Credentials injected via a pre-existing Secret, referenced by `credentials.secretName` (chart does not create the Secret)
- 3-digit zero-padded pipeline ordering with hard validation
- extraResources escape hatch for pipeline-specific transform ConfigMaps
- Add `tlsCertExtractor` — optional init container that extracts the full TLS cert chain from any `host:port` via `openssl s_client` and writes both PEM and PKCS12 formats to a shared `emptyDir` volume. Enabled via `tlsCertExtractor.enabled: true`. Requires `host` and `port`. Image defaults to `alpine/k8s:1.36.2`. No Kubernetes API access required.
- Add `kafka.ssl` — optional truststore configuration for `SASL_SSL` Kafka connections. Renders `ssl_truststore_location`, `ssl_truststore_type`, `ssl_truststore_password` (only when non-empty), and `ssl_endpoint_identification_algorithm` into the inputs ConfigMap. Enabled via `kafka.ssl.enabled: true`. Independent of `tlsCertExtractor` — a pre-provisioned cert (e.g. via ExternalSecret) can be used without the extractor.

### Fixed
- Replace invalid `spec.pipelines[].configRef` with `path.config` glob + per-ConfigMap volume mounts (inputs, transforms, outputs each mounted into numbered subdirectories)
- Move `config.reload.automatic` / `config.reload.interval` from per-pipeline settings to process-level `spec.config` (eliminates deprecation warnings)
- Replace non-existent `spec.logstashConfig` with correct `spec.config` flat map
- Replace non-existent `spec.logstashJvmOptions` with `LS_JAVA_OPTS` env var
- Decouple `spec.version` (ECK schema requirement) from `image.tag` via new `elasticVersion` value (default: `9.5.5`)
- Remove chart-managed ExternalSecret; replace `secrets.*` values with `credentials.secretName` — caller now owns provisioning the Secret
- Update test suite to assert pipeline volume order and ExternalSecret absence
