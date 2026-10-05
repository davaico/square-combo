# Monitoring

The application exposes Prometheus text metrics at `/metrics`. Scrape it over loopback with the configured public Host header, or through a restricted proxy route. `/health` is only process/database liveness.

Useful alerts:

- `sync_last_run_success == 0`: the latest business-date run failed, is still running, or no run exists.
- `time() - sync_last_success_timestamp_seconds > 90000`: no successful date reconciliation within 25 hours. A zero timestamp means no success has been recorded.
- `sync_failed_runs_last_24h > 0`: at least one business-date run failed. Historical failures remain in this rolling count even after a successful rerun; inspect the task's exit status/logs and rerun the affected dates.
- A failed `square-combo-sync.service` or missed systemd timer invocation.

A multi-date reconciliation returns failure if any date fails. One successful later date does not erase another date's failure; use both metrics and the service outcome. A successful run with no active merchants is valid but does not prove configured merchant coverage—verify activation and mappings during provisioning.

With Grafana Alloy, configure `prometheus.scrape` to use `/metrics`, include the configured Host header and forward to your private remote-write receiver. Follow Grafana's current installation instructions for credentials; do not commit them here.

Optional log collection should read the absolute protected `LOG_DIR/sync.log` path from your deployment, with access limited to operators. Logs contain aggregate operational data and sanitized error classes. Set retention appropriate to business confidentiality and remove raw provider responses from any old installation's logging pipeline. General logs rotate at 10 MB/five backups, sync logs at 10 MB/ten backups; journald and remote retention are separate operator settings.
