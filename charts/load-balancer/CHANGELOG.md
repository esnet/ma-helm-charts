# Changelog


[0.1.6]
 - Fix: `cert-bootstrap` Job (and its ServiceAccount/Role/RoleBinding) only carried
   ArgoCD's `argocd.argoproj.io/hook` annotations, which ArgoCD honors but plain
   `helm upgrade --install` does not. Installing this chart outside ArgoCD (e.g. via
   a bootstrap script) caused every subsequent upgrade to fail with
   `Job.batch "cert-bootstrap" is invalid: spec.template: ... field is immutable`,
   since Helm tried to patch the Job in place instead of recreating it. Added the
   equivalent `helm.sh/hook` / `helm.sh/hook-delete-policy` annotations alongside
   the existing ArgoCD ones so both plain Helm and ArgoCD-driven installs delete
   and recreate these resources on every install/upgrade.
 - Added `helm.sh/hook-weight` (`"1"` on the ServiceAccount/Role/RoleBinding, `"2"`
   on the Job) matching the existing ArgoCD `sync-wave` values, so plain Helm
   installs also guarantee the RBAC exists before the Job that needs it — without
   an explicit weight, same-hook-type resources have no defined relative order.
 - `README.md` corrected: the bootstrap hook has run for both `gke` and `envoy`
   gateway types since 0.1.4, not `gke`-only as previously documented; the
   `config.gateway.bootstrap.image` default in the values reference table was
   still listed as `alpine:3` after the 0.1.5 switch to `k8s-cert-helper`.

[0.1.5]
 - Fix gVisor clusters: the `cert-bootstrap` Job's default image (`alpine:3`) could
   not resolve external DNS via `apk` inside the gVisor sandbox, breaking the
   bootstrap cert flow on those clusters. Default image switched to
   `k8s-cert-helper` (an `alpine/k8s` fork with `openssl` pre-installed;
   see https://github.com/esnet-saas/supporting-containers), removing the
   `apk add` step entirely.
 - Simplify the bootstrap script: replaced raw Kubernetes API calls (`curl` +
   service account bearer token) for checking/creating the TLS Secret with
   plain `kubectl get secret` / `kubectl create secret tls` / `kubectl annotate
   secret`, now that the image ships `kubectl`.
 - `cert-bootstrap-role` gains the `patch` verb on `secrets` (needed for the
   `kubectl annotate secret` step above).

[0.1.4]
 - Renamed 00-gke-cert-bootstrap.yaml to 00-cert-bootstrap.yaml and is now used for both GKE and Envoy.
 - deprecated the config.gateway.enabled, it is now true by default.
 - Added unit tests for various use cases.

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
