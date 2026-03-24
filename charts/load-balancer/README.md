# load-balancer Helm Chart

Deploys a Gateway API-based load balancer on GKE using either the native GKE
L7 controller (`gke-l7-global-external-managed`) or the Envoy Gateway
controller (`envoy`).  Includes cert-manager integration for automatic
Let's Encrypt TLS certificate provisioning.

---

## Gateway types

Set `config.gateway.type` to one of the following values.

### `gke` — GKE L7 Global External Managed

Uses Google's managed `gke-l7-global-external-managed` GatewayClass.  The
frontend is a **global** external Application Load Balancer.

**IP addresses:** Must be **global** static IP addresses reserved in your GCP
project (`gcloud compute addresses create --global`).

**ArgoCD race-condition note:** The GKE controller requires the TLS Secret to
exist before it will provision the load balancer, but cert-manager cannot
complete the ACME HTTP01 challenge until the load balancer is running.  This
chart breaks that cycle with an ArgoCD `PreSync` hook Job
(`cert-bootstrap`) that creates a short-lived self-signed Secret before the
main sync.  cert-manager then issues the real Let's Encrypt certificate through
the live Gateway and replaces the Secret automatically.  This hook only runs
when `config.gateway.type: gke`.

### `envoy` — Envoy Gateway

Uses the Envoy Gateway controller.  Under the hood, Envoy Gateway creates a
Kubernetes `Service` of type `LoadBalancer`, which GKE maps to a **regional**
external passthrough Network Load Balancer.

> **⚠️ Envoy Gateway only supports regional static IP addresses.**
>
> You must reserve a **regional** static IP in the same region as your GKE
> cluster:
>
> ```sh
> # IPv4
> gcloud compute addresses create my-lb-ipv4 \
> --region=<CLUSTER_REGION> 
>
> # IPv6 (if dual-stack)
> gcloud compute addresses create my-lb-ipv6 \
> --ip-version=IPV6 \
> --endpoint-type=NETLB \
> --region=us-central1 \
> --subnet=default-kube
> ```
>
> **Global** static IPs (`--global`) are **not** compatible with the Envoy
> Gateway backend.  Using a global IP will prevent the LoadBalancer Service
> from acquiring an external address.  Global IPs are only supported by the
> `gke-l7-global-external-managed` GatewayClass (see above).

The IP address(es) are bound via the
`networking.gke.io/load-balancer-ip-addresses` annotation on the generated
`EnvoyProxy` service.  Pass the address **value** (not the reservation name)
in the values:

```yaml
config:
  gateway:
    type: envoy
    ipv4:
      enabled: true
      address: "34.x.x.x"         # regional IPv4 address value
      address_type: NamedAddress
    ipv6:
      enabled: false
```

**`ipFamily` is always set explicitly** by the chart (`IPv4`, `IPv6`, or
`DualStack`) to avoid Envoy Gateway inheriting a cluster-level dual-stack
default when only IPv4 is requested.

---

## Values reference

| Key | Default | Description |
|-----|---------|-------------|
| `config.gateway.type` | `envoy` | Gateway implementation: `gke` or `envoy` |
| `config.gateway.class_name` | `envoy` | GatewayClass name |
| `config.gateway.name` | `external-http` | Gateway resource name |
| `config.gateway.namespace_policy` | `All` | `allowedRoutes.namespaces.from` |
| `config.gateway.ipv4.enabled` | `true` | Enable IPv4 listener |
| `config.gateway.ipv4.address` | — | Static IP address (regional for Envoy, global for GKE) |
| `config.gateway.ipv6.enabled` | `true` | Enable IPv6 listener / DualStack |
| `config.gateway.ipv6.address` | — | Static IPv6 address |
| `config.gateway.bootstrap.image` | `alpine:3` | Image used by the GKE PreSync bootstrap Job |
| `config.certificate.name` | `tls-cert` | Name of the TLS Secret cert-manager writes to |
| `config.certificate.issuer` | `letsencrypt-prod` | cert-manager ClusterIssuer name |
| `config.certificate.tlsPolicy.enabled` | `true` | Create a TLS cipher/version policy |
| `config.argocd_annotation` | `true` | Inject `argocd.argoproj.io/sync-wave` annotations |
| `config.domains` | — | List of domains for the certificate and ACME challenge |

---

## ArgoCD sync-wave ordering

When `config.argocd_annotation: true` the following sync-wave order is used:

| Resource | Wave |
|----------|------|
| GKE: bootstrap Job (PreSync hook) | PreSync |
| EnvoyProxy / GatewayClass | `-15` |
| ClusterIssuer | `-15` |
| Gateway | `-10` |
| Certificate (cert-manager) | `0` |

The Certificate is intentionally deployed **after** the Gateway so the ACME
HTTP01 solver can route the challenge through the live load balancer.
