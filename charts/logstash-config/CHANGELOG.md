# Changelog

## [0.0.1]

### Changed
- Renamed `configmap-inputs.yaml` → `configmap-kafka-input.yaml` and `configmap-outputs.yaml` → `configmap-elasticsearch-output.yaml` to reflect the concrete datasources they configure. The rendered Kubernetes ConfigMap names change accordingly: `<release>-inputs` → `<release>-kafka-input` and `<release>-outputs` → `<release>-elasticsearch-output`.

### Added
- `kafka.enabled` (default: `true`) — set `false` to skip the built-in Kafka input ConfigMap entirely. When disabled, pipeline slot 001 is free for a user-supplied input via `pipeline.transforms` or `extraResources`.
- `elasticsearch.enabled` (default: `true`) — set `false` to skip the built-in Elasticsearch output ConfigMap entirely. When disabled, pipeline slot 999 is free for a user-supplied output.
- Kafka env vars (`kafka_input_*`) are no longer injected into the Logstash container when `kafka.enabled: false`.
- `NOTES.txt` secret-key table is now conditional — only lists keys actually required by the enabled built-in components.
- `NOTES.txt` includes a "Bring Your Own Input/Output" section (rendered when either built-in is disabled) documenting both the `extraResources` + `pipeline.transforms` pattern and credential injection options.
- `pipeline.transforms` index validation now allows index 1 when `kafka.enabled: false` and index 999 when `elasticsearch.enabled: false`.
- ECK-managed Logstash CR with generic input/output ConfigMaps
- Credentials injected via a pre-existing Secret, referenced by `credentials.secretName` (chart does not create the Secret)
- 3-digit zero-padded pipeline ordering with hard validation
- extraResources escape hatch for pipeline-specific transform ConfigMaps
- Add `tlsCertExtractor` — optional init container that extracts the full TLS cert chain from any `host:port` via `openssl s_client` and writes both PEM and PKCS12 formats to a shared `emptyDir` volume. Enabled via `tlsCertExtractor.enabled: true`. Requires `host` and `port`. Image defaults to `alpine/k8s:1.36.2`. No Kubernetes API access required.
- Add `kafka.ssl` — optional truststore configuration for `SASL_SSL` Kafka connections. Renders `ssl_truststore_location`, `ssl_truststore_type`, `ssl_truststore_password` (only when non-empty), and `ssl_endpoint_identification_algorithm` into the inputs ConfigMap. Enabled via `kafka.ssl.enabled: true`. Independent of `tlsCertExtractor` — a pre-provisioned cert (e.g. via ExternalSecret) can be used without the extractor.
- Replace invalid `spec.pipelines[].configRef` with `path.config` glob + per-ConfigMap volume mounts (inputs, transforms, outputs each mounted into numbered subdirectories)
- Decouple `spec.version` (ECK schema requirement) from `image.tag` via new `elasticVersion` value (default: `9.5.5`)
- Update test suite to assert pipeline volume order and ExternalSecret absence
