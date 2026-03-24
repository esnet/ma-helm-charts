# Changelog

[0.1.3]
- Fix: `GatewayClass.spec.parametersRef.name` was hardcoded to `external-http-proxy`
  instead of using `config.gateway.proxy_name`. Previously, changing `proxy_name`
  would silently break the GatewayClass-to-EnvoyProxy binding.
- Fix Envoy Gateway IPv4-only mode: `ipFamily` is now always set explicitly
  (`IPv4`, `IPv6`, or `DualStack`) in the EnvoyProxy resource. Previously,
  when `ipv6.enabled: false`, no `ipFamily` was set, causing Envoy Gateway to
  inherit the cluster default (DualStack on dual-stack GKE clusters) and
  attempt to acquire an IPv6 address that was never provisioned.
- Add chart-level `README.md` documenting the regional IP constraint for the
  Envoy Gateway backend (regional IPs only; global IPs are not compatible).
- Fix GKE `gke-l7-global-external-managed` race condition: added an ArgoCD
  PreSync hook Job (`cert-bootstrap`) that generates a self-signed TLS Secret
  before the main sync so the Gateway can provision while cert-manager
  completes the ACME HTTP01 challenge in the background.
- Explicit ArgoCD sync-wave `"0"` annotation added to the Certificate resource
  to clarify ordering (after Gateway at `-10`).
- New `config.gateway.bootstrap.image` value (default `alpine:3`) to allow
  overriding the bootstrap Job image in air-gapped environments.
- Rename `config.gateway.gateway_namespace_override` to `config.gateway.envoy_system_namespace`
  for clarity; the old name implied it was general-purpose but it is exclusively
  used by the Envoy Gateway path.
- Fix Envoy Gateway namespace placement: `EnvoyProxy` and `GatewayClass.parametersRef`
  now unconditionally use `envoy_system_namespace`. Previously, if the value was
  unset they fell back to the release namespace, causing the Envoy Gateway
  controller to fail to find the `EnvoyProxy` and leaving the `GatewayClass`
  unreconciled (which broke HTTP-01 ACME challenge routing).
- `envoy_system_namespace` now defaults to `envoy-gateway-system` in `values.yaml`
  so no overlay needs to set it unless using a non-standard controller namespace.
- Fix `ClientTrafficPolicy` namespace: policy now always deploys into
  `config.namespace` (the application namespace, co-located with the `Gateway`
  it targets). Previously it incorrectly followed `envoy_system_namespace`,
  placing it in the controller namespace where the Gateway does not exist.
- Remove `00-envoynamespace.yml`: the load-balancer chart no longer creates the
  `envoy-gateway-system` namespace. Namespace ownership is now delegated to the
  dedicated `envoy-gateway` ArgoCD application.

[0.1.2]
- Fixing IPv6 support
- Switching to OCI publishing
