# helm-charts



## Getting started

Packaging:

helm package charts/clickhouse -d releases

Index generation:
helm repo index . --url https://github.com/esnet/ma-helm-charts/raw/main

Helm Dependency:

```sh
cd charts/<name>
helm dependency update
```
