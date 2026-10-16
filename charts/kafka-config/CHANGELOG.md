# Changelog

All notable changes to this project will be documented in this file.

[0.0.3]
 - Removed dual-stack (`RequireDualStack`) listener support. GKE always
   returns the v4 address regardless of IP family policy, making dual-stack
   non-functional. Use separate single-stack listeners for IPv4 and IPv6.
 - Restructured listener `configuration` block: `staticIpNames` (a joined
   list on the bootstrap annotation) is replaced by `configuration.bootstrap.
   annotations` (a free-form annotations map) and `configuration.brokers`
   (a list of `{id, annotations}` entries), matching the Strimzi API directly.
 - Added `cloud.google.com/l4-rbs: enabled` annotation support for IPv6
   listeners that require GKE L4 Regional Backend Services.
 - Broker IDs now start at 100. Added `config.keeper.broker.nodeIds`
   (default `"[100-199]"`), rendered as the `strimzi.io/next-node-ids`
   annotation on the broker `KafkaNodePool`.
 - Added `config.keeper.broker.nodeStartId` (default `100`). The listener
   template uses this alongside `broker.replicas` to auto-generate the
   per-broker configuration block via `untilStep`, matching the Jinja2
   `range(nodeStartId, nodeStartId + broker_replicas)` pattern. No explicit
   broker list is required in listener values — scale `replicas` and all
   broker entries follow automatically.
 - `configuration.brokers` (explicit list) replaced by two optional fields:
   `configuration.brokerAnnotations` (map applied to every broker) and
   `configuration.brokerIpAddresses` (positional list of GCP address resource
   names, where index 0 maps to the first broker at `nodeStartId`). Both
   fields are optional. Scaling replicas only requires appending to the list,
   no broker IDs to maintain.
 - Updated `values.yaml` listener examples to reflect the new structure
   for IPv4, IPv6, and external TLS single-stack loadbalancer listeners.
 - Fixed broker and controller pod anti-affinity rules using the wrong
   label key. `strimzi.io/name` is cluster-scoped — Strimzi applies it
   to all pods in the cluster (both controllers and brokers), causing
   controllers to block broker scheduling and leaving brokers permanently
   pending when controllers occupied all available nodes. Both pools now
   use `strimzi.io/pool-name` (pool-scoped) so each pool's anti-affinity
   only matches its own pods.
 - Added regression test `anti-affinity-uses-pool-name` to prevent this
   class of bug recurring.

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
