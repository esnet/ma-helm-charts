# Changelog

## [0.0.1]

### Added
- ECK-managed Logstash CR with configurable replicas, JVM heap, and pipeline worker settings
- Ordered pipeline system: 3-digit zero-padded slots with built-in Kafka input (slot 001) and Elasticsearch output (slot 999); both independently disableable
- `pipeline.transforms` for user-supplied transform ConfigMaps, with slot-range validation
- Metricbeat sidecar for Logstash Stack Monitoring via the xpack module; configurable metricsets (default: `node`, `node_stats`), period, and target Elasticsearch cluster
- Optional TLS cert extractor init container — pulls a cert chain from any `host:port` via `openssl s_client` and writes PEM + PKCS12 to a shared volume
- Kafka SSL/SASL_SSL support with PKCS12 truststore configuration
- Credentials injected via a pre-existing Secret (`credentials.secretName`); chart creates no secrets
- `extraResources` escape hatch for arbitrary additional manifests

### Removed
- `configmap-logstash.yaml` — redundant; ECK operator reads `spec.config` from the `Logstash` CR directly and the ConfigMap was never mounted
