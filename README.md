# ma-helm-charts

## Getting started

Helm Dependency:

```sh
cd charts/<name>
helm dependency update
```

Once you commit someting into main a Github Action will releas all artifacts and update the index page at: https://software.es.net/ma-helm-charts/index.yaml

## Adding Helm Repo

```sh
helm repo add ma-helm https://software.es.net/ma-helm-charts/
helm repo update ma-helm
```

You can then list the charts via:

```sh
helm search repo ma-helm
NAME                 	CHART VERSION	APP VERSION	DESCRIPTION
ma-helm/clickhouse   	0.1.3        	           	Clickhouse Cluster Configuration. This assumes ...
ma-helm/load-balancer	0.1.1        	           	Load Balancer and Configuration
```

## Testing
brew install chart-testing

ct install --all
```sh
helm plugin install https://github.com/helm-unittest/helm-unittest
```

### Linting

ct lint charts ## validates said charts, is also invoked by CICD


### Helm OCI push

This is mostly for testing purposes for now but we should really be moving to using OCI eventually.

1. Get a machine token

gcloud auth print-access-token | helm registry login -u oauth2accesstoken \
  --password-stdin https://us-central1-docker.pkg.dev

2. Build

```sh
helm package load-balancer
helm push load-balancer-0.1.1.tgz oci://us-central1-docker.pkg.dev/ma-infrastructure-474617/inf-helm
helm pull oci://us-central1-docker.pkg.dev/ma-infrastructure-474617/inf-helm/load-balancer --version 0.1.1
## Installing from oci
helm install my-release oci://us-central1-docker.pkg.dev/ma-infrastructure-474617/inf-helm/load-balancer --version 0.1.1
## Show chart
helm show chart oci://us-central1-docker.pkg.dev/ma-infrastructure-474617/inf-helm/load-balancer --version 0.1.1

```
