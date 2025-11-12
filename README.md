# ma-helm-charts

## Getting started

Helm Dependency:

```sh
cd charts/<name>
helm dependency update
```

Once you commit someting into main a Github Action will releas all artifacts and update the index page at: https://software.es.net/ma-helm-charts/index.yaml


## Note

All chars here are public and being pushed to a public registry.

## Using the repo

All artifacts are currently published to our OCI registry:

gcloud artifacts packages list \
  --repository=inf-helm \
  --location=us-central1 \
  --project=ma-infrastructure-474617

### Show chart

helm show chart oci://us-central1-docker.pkg.dev/ma-infrastructure-474617/inf-helm/load-balancer

## Install chart

helm install my-release oci://us-central1-docker.pkg.dev/ma-infrastructure-474617/inf-helm/load-balancer --version 0.1.2


## Testing
brew install chart-testing

ct install --all
```sh
helm plugin install https://github.com/helm-unittest/helm-unittest
```

### Linting

ct lint charts ## validates said charts, is also invoked by CICD


### CICD

Every MR will push create a temporary tag you can use for testing:

example:

```sh
helm pull helm pull oci://us-central1-docker.pkg.dev/ma-infrastructure-474617/inf-helm/clickhouse --version 0.0.3-dev-f6b6158
```
