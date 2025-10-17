# helm-charts



## Getting started

Packaging:

helm package charts/clickhouse -d .

Index generation:
helm repo index . --url https://github.com/esnet/ma-helm-charts/raw/main
