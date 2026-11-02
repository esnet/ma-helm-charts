# Changelog

All notable changes to this project will be documented in this file.

[0.0.3]
 - **Breaking:** Removed dual-stack listener support; use separate single-stack listeners for IPv4 and IPv6.
 - **Breaking:** Listener `configuration` block restructured — `staticIpNames` replaced by `configuration.bootstrap.annotations` (free-form map) and `configuration.brokerAnnotations` / `configuration.brokerIpAddresses` (positional list); no explicit broker IDs required.
 - Broker IDs now start at 100; `config.keeper.broker.nodeStartId` (default `100`) and `nodeIds` (default `[100-199]`) drive per-broker config generation automatically from `replicas`.
 - Added `cloud.google.com/l4-rbs: enabled` annotation support for IPv6 listeners on GKE.
 - Fixed pod anti-affinity using `strimzi.io/name` (cluster-scoped) instead of `strimzi.io/pool-name` (pool-scoped), which caused brokers to block controller scheduling.

[0.0.2]
 - Fixed `jmxOptions` being rendered at the wrong nesting level (was a sibling
   of `spec.kafka` instead of nested under it, so enabling it never actually
   worked).
 - Renamed `config.kafka.jmx.enabled` to `config.kafka.jmxOptions.enabled`
   (raw JMX/RMI access only, e.g. jconsole/VisualVM).
 - Added `config.kafka.metrics` (`enabled` / `allowList`) to configure
   Strimzi Metrics Reporter via `spec.kafka.metricsConfig`, exposing
   Prometheus-format metrics on port 8080 with no JMX bridge or sidecar.
   Applies cluster-wide, covering both the broker and controller node pools.
 - Updated to depend on v1 of operator
 - Moved all resource/limits management under kraft
 - remove replica from base kraft config
 
[0.0.1] 
 - Adding inital kafka configuration chart
 - Listeners are now dynamic and configurable.
 - Per-listener gateway or Loadbalancer configuration.
 - Support for static IPs and dual stack on GKE.
