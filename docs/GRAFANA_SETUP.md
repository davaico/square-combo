## Grafana Setup

### Prerequisites
- Register Grafana Cloud account at https://grafana.com/signup/cloud
- Go to portal -> Add new connection -> Choose which to integrate (etc. Linux server)
  -> Follow instructions to install Alloy service

### Setup VM metrics (CPU, Memory...)
- After installing Alloy by following the instructions, start the Alloy service
  and test your connection in Grafana Cloud portal.
- Click install dashboard at the last step of instructions to import VM
  monitoring dashboard.

### Setup application health metric
- Open config.alloy file as administrator, create prometheus scrape component 
  to get application health metric.
- Example config.alloy file:

```
prometheus.relabel "app_health" {
  forward_to = [prometheus.remote_write.metrics_service.receiver]

  rule {
    target_label = "job"
    replacement  = "app_health"
  }

  rule {
    target_label = "instance"
    replacement  = constants.hostname
  }
}

prometheus.scrape "app_health" {
  targets = [
    {
      __address__ = "<your application host>",
    },
  ]

  metrics_path = "/health"

  forward_to = [prometheus.relabel.app_health.receiver]
}
```
- Restart Alloy service
- Check health metric in Grafana Explore section and import to new dashboard

### Setup cronjob sync logs
- Open config.alloy file as administrator, create loki process to get logs from sync.log file.
- Example config.alloy file:

```
loki.source.file "square_combo_sync" {
  targets = [
    {
      __path__ = "/home/davaiadmin/apps/square-combo/logs/sync.log",
      job      = "square_combo_sync",
    },
  ]

  forward_to = [loki.process.square_combo_sync.receiver]
}

loki.process "square_combo_sync" {
  forward_to = [loki.write.grafana_cloud_loki.receiver]

  stage.labels {
    values = {
      service_name = "square_combo_sync",
    }
  }
}
```
- Restart Alloy service
- Check sync logs in Grafana Explore section and import to new dashboard
