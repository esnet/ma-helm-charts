# Changelog

All notable changes to this project will be documented in this file.

[0.0.10]
  - Fix `disable_play` HTTP handler: removed the `<headers><pragma>no-cache</pragma></headers>`
    restriction from the `dynamic_query_handler` rule. The restriction broke standard
    HTTP clients (Grafana plugin, clickhouse-go driver, etc.) that do not send the
    `pragma` header, causing `400 No query` errors on valid query requests.
  - Add `config.ch.disable_play_handlers` value: allows overriding the `<rule>` blocks
    rendered inside `config.d/disable_play.xml` when `disable_play: true`. Provide the
    inner rule blocks only — the `<clickhouse>` and `<http_handlers replace="1">` wrapper
    is always added by the template. Defaults to the standard set: `/ping`,
    `/replicas_status`, `/play` blocked with 403, and `dynamic_query_handler` for all
    other POST/GET requests.

[0.0.9]
  - Remove `allow_experimental_database_replicated` from server config. The setting
    graduated to stable in ClickHouse 26.x and was removed from `ServerSettings`;
    26.8+ rejects it with `UNKNOWN_ELEMENT_IN_CONFIG` and fails to start.
  - Add `config.ch.disable_play` boolean (default: false). When true, renders
    `config.d/disable_play.xml` with `replace="1"` on the `http_handlers` block,
    returning 403 for `/play` while preserving `/ping`, `/replicas_status`, and
    query execution handlers. Avoids YAML parser mangling of XML in `files.data`
    block scalars.

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
