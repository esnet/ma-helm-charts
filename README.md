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
