# Changelog

All notable changes to this project will be documented in this file.

[0.0.9] - Unreleased
  - New: Added per-user `grants` support. Each entry under `config.ch.users.<username>.grants`
    is a full GRANT statement rendered as a `<grants><query>...</query></grants>` block
    in users.xml, using ClickHouse's native grant configuration. Any valid ClickHouse
    GRANT syntax is accepted (privileges, ON CLUSTER, WITH GRANT OPTION, etc.).
    Note: `grants` and `allow_databases` are mutually exclusive per ClickHouse's user
    configuration rules — do not use both on the same user.
  - Fix: TLSRoutes now use .Values.namespace instead of hardcoded "clickhouse" namespace.
  - Fix: TLSRoute backend service name now derived from config.ch.installation_name instead of
    hardcoded "clickhouse-ch-cluster". Changing installation_name no longer silently breaks routes.
  - Fix: TLSRoutes are now gated on both config.tls.enabled AND config.tls.routes, preventing
    routes being rendered without TLS configured on the ClickHouse side.
  - New: Gateway parentRef name and sectionNames are now configurable via config.tls.gateway
    (name, tcp_section, https_section) with existing values as defaults.
  - Fix: config.ch.storage_policy is now correctly used for the CHI storageManagement reclaimPolicy.
    Previously config.chk.storage_policy was used for both keeper and ClickHouse PVCs.
  - Fix: Backup metrics Service (ch-backups-metrics) is now gated on both config.backups.enabled
    AND config.backups.monitoring.enabled. Previously it was always rendered, creating a headless
    service with no endpoints when backups were disabled.
  - Fix: Profile rendering is now fully generic — any key/value pair under a profile is rendered.
    Previously only readonly and max_memory_usage were handled, and readonly: 0 was silently
    dropped due to a falsy guard (if 0 is false in Go templates).
  - Fix: Default user secret names standardised to use hyphens (clickhouse-users). The previous
    default clickhouse_users (underscore) is an invalid Kubernetes resource name per RFC 1123.

[0.0.8]
  - TLSRoutes API version are now configurable. Defaults to v1.
  - Envoy pattern will require +1.8.0 if using v1.

[0.0.7] - Breaking change
 - **Breaking:** `config.ch.resources.shardCount` and `replicasCount` removed.
   Cluster topology is now defined in `config.ch.clusters`, a map where each
   key is the cluster name and the value has `shards`, `replicas`, and an
   optional `schema_policy`.  All clusters within a CHI share the same Keeper
   ensemble and pod/volume templates.
 - Multiple clusters can now be declared under `config.ch.clusters`; the
   Altinity operator provisions each as a separate logical cluster backed by
   the same ClickHouseKeeper nodes.
 - **Breaking:** `config.ch.name` renamed to `config.ch.installation_name` to
   clearly distinguish the ClickHouseInstallation resource name from the
   logical cluster names defined in `config.ch.clusters`.
 - Fix: monitoring services now select pods via the `clickhouse.altinity.com/chi`
   label (CHI name) instead of `clickhouse.altinity.com/cluster` (cluster name).
   The previous selector would silently miss pods when the cluster name differed
   from the CHI name, and would never cover multiple clusters.
 - **Breaking:** `config.ch.files` converted from a list to a map. The key is
   the bare filename (e.g. `distributed_ddl.xml`). Files are placed under
   `config.d/` by default; set `directory` on an entry to override (e.g.
   `directory: users.d`). The old `name` field with an embedded path (e.g.
   `config.d/distributed_ddl.xml`) is no longer used.
 - **Breaking:** `config.ch.users` converted from a list to a map. The `name`
   field is removed; the username is now the map key instead.
 - **Breaking:** `config.ch.profiles` converted from a list to a map. The
   `name` field is removed; the profile name is now the map key instead.
 - Maps eliminate duplicate-key ambiguity and make `--set` overrides
   substantially easier (no more fragile array index addressing).

[0.0.6]
 - Added support for setting storageclass. Breaking change for disk volume configuration.

[0.0.5]

- added backups.monitoring.enabled that exposes a new service that can be hooked into otel/prom scraping
- Fixing CI to prevent duplicate tags or overriding tags.
- Added support for monitoring backup service
- Added node affinity support enabling the user to pin deploment to a given node pool. Fixed podAntiAffinity for keeper nodes.

[0.0.4]
 - Enable a backups pattern, supporting GCS via service or workload identity.
 - Fixing retention policy 
 - Adding monitoring support for keeper and clickhouse

[0.0.3]
 - adding DB access list
 - Restructuring TLS config. (Breaking change)
 
[0.0.2]
 - Making TLS Configurable

[0.0.1] 
 - Adding inital clickhouse configuration chart
