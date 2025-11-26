# Changelog

All notable changes to this project will be documented in this file.


[Unreleased/0.0.5]

- added backups.monitoring.enabled that exposes a new service that can be hooked into otel/prom scraping
- Fixing CI to prevent duplicate tags or overriding tags.
- Added support for monitoring backup service

[0.0.4]
 - Enable a backups pattern, supporting GCS via service or workload identity.
 - Fixing retention policy 
 - Adding monitoring support for keeper and clickhouse

[0.0.3]
 - adding DB access list
 - Restructuring TLS config. (Breaking change)
 
[0.0.2]
 - Making TLS Configurable

[0.0.1] 
 - Adding inital clickhouse configuration chart
