# Grafana Monitoring Setup for Parking Management System

This directory contains Grafana configuration for monitoring the Parking Management System.

## Directory Structure

grafana/
├── provisioning/
│ ├── dashboards/
│ │ ├── dashboard.yml # Dashboard provisioning config
│ │ ├── parking-system-overview.json
│ │ ├── parking-api-performance.json
│ │ ├── payment-service-monitor.json
│ │ ├── notification-service.json
│ │ └── databases/
│ │ ├── postgres-overview.json
│ │ ├── postgres-performance.json
│ │ └── postgres-replication.json
│ │ └── caching/
│ │ ├── redis-overview.json
│ │ └── redis-performance.json
│ │ └── apis/
│ │ ├── api-gateway-metrics.json
│ │ └── api-response-times.json
│ │ └── infrastructure/
│ │ ├── docker-containers.json
│ │ └── system-metrics.json
│ ├── datasources/
│ │ └── datasource.yml # Datasource configuration
│ └── alert-rules.yml # Alert rules
├── setup-dashboards.sh # Dashboard setup script
├── dashboard-manager.sh # Dashboard management tool
└── README.md # This file


## Quick Start

### 1. Start Grafana with Docker Compose

```bash
cd parking-management/deployment/docker
docker-compose up -d grafana

2. Access Grafana
URL: http://localhost:3003

Username: admin

Password: admin123 (or as configured in .env)

3. Setup Dashboards (Automated)
The dashboards are automatically provisioned when Grafana starts. You can also run:

# Make scripts executable
chmod +x setup-dashboards.sh dashboard-manager.sh

# Run setup script
./setup-dashboards.sh

Available Dashboards
1. Parking System Overview
Real-time system metrics

Active users, reservations, revenue

API performance and error rates

Parking space availability

2. PostgreSQL Database
Connection statistics

Query performance

Cache hit ratio

Table sizes and dead tuples

3. Redis Cache
Memory usage

Cache hit rate

Connected clients

Command execution rates

4. API Performance
Response times by endpoint

Request rates

Error rates by service

95th percentile latency

5. Infrastructure
Docker container status

CPU/Memory/Disk usage

Network I/O

System load

Datasources
Configured datasources include:

Prometheus (default) - Metrics collection

PostgreSQL - Direct database queries

Elasticsearch - Log analysis

Loki - Log aggregation

Tempo - Distributed tracing

Alerting
Pre-configured alert rules monitor:

Critical Alerts
API error rate > 5% for 5 minutes

No available parking spaces

Service down (HTTP 5xx errors)

Redis unavailable

Warning Alerts
High response times (>2s 95th percentile)

Low parking space availability (<10)

High database connections (>100)

Low cache hit ratio (<90%)

High memory/CPU usage

Dashboard Management
Use the dashboard manager script for backup/restore:

bash
# Export all dashboards
./dashboard-manager.sh export

# Import dashboards from directory
./dashboard-manager.sh import /path/to/dashboards

# Backup datasources
./dashboard-manager.sh backup-datasources

# List all dashboards
./dashboard-manager.sh list

# Delete a dashboard
./dashboard-manager.sh delete <dashboard-uid>
Customizing Dashboards
1. Add New Panels
Edit the JSON files in provisioning/dashboards/:

json
{
  "title": "New Panel",
  "type": "timeseries",
  "targets": [
    {
      "expr": "your_prometheus_query",
      "legendFormat": "{{label}}"
    }
  ]
}
2. Modify Variables
Update the templating section in dashboard JSON:

json
"templating": {
  "list": [
    {
      "name": "service",
      "query": "label_values(job)",
      "multi": true,
      "includeAll": true
    }
  ]
}
3. Change Time Ranges
Modify the time section:

json
"time": {
  "from": "now-6h",
  "to": "now"
},
"timepicker": {
  "refresh_intervals": ["5s", "10s", "30s", "1m", "5m"]
}
Adding Custom Metrics
1. Define Prometheus Metrics in Application
javascript
// Example in Node.js
const prometheus = require('prom-client');

// Create custom metric
const parkingSpacesMetric = new prometheus.Gauge({
  name: 'parking_spaces_available',
  help: 'Number of available parking spaces',
  labelNames: ['lot_id', 'lot_name']
});

// Update metric
parkingSpacesMetric.set({ lot_id: '1', lot_name: 'Main Lot' }, 25);
2. Expose Metrics Endpoint
javascript
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', prometheus.register.contentType);
  res.end(await prometheus.register.metrics());
});
3. Add to Grafana Dashboard
Create a new panel with query:

text
parking_spaces_available
Performance Tips
1. Query Optimization
Use rate() with appropriate time windows

Aggregate data when possible

Limit time range for complex queries

Use recording rules for expensive queries

2. Dashboard Optimization
Limit number of panels per dashboard

Use shorter refresh intervals for critical metrics

Group related metrics together

Use stat panels for single values

3. Alert Tuning
Set appropriate for durations to prevent flapping

Use different severity levels

Include runbook URLs in annotations

Test alerts in staging first

Troubleshooting
Common Issues
"No Data" in Panels

Check Prometheus datasource connection

Verify metric names exist in Prometheus

Check time range and refresh interval

Slow Dashboard Loading

Reduce number of panels

Simplify complex queries

Increase Prometheus query timeout

Use caching where possible

Missing Dashboards

Check provisioning directory permissions

Restart Grafana to reload provisioning

Verify dashboard JSON syntax

Alert Not Firing

Check alert rule syntax

Verify Prometheus rule evaluation

Check notification channel configuration

Logs
bash
# View Grafana logs
docker-compose logs grafana

# Check provisioning logs
docker exec -it grafana cat /var/log/grafana/grafana.log

# Test datasource connection
curl -u admin:password http://localhost:3003/api/datasources
Backup and Recovery
Automated Backup
Add to cron:

bash
# Daily backup at 2 AM
0 2 * * * /path/to/dashboard-manager.sh export
0 2 * * * /path/to/dashboard-manager.sh backup-datasources
Manual Backup
bash
# Backup all configuration
tar -czf grafana-backup-$(date +%Y%m%d).tar.gz \
  provisioning/ \
  dashboards/ \
  datasources/
Restore
bash
# Extract backup
tar -xzf grafana-backup-20240101.tar.gz

# Import dashboards
./dashboard-manager.sh import ./provisioning/dashboards

# Restore datasources
./dashboard-manager.sh restore-datasources ./datasources/datasources.json
Security Considerations
Change Default Credentials

Update admin password in .env

Use strong passwords for datasources

Limit Access

Use reverse proxy with authentication

Configure firewall rules

Use read-only users for dashboards

Secure API Keys

Rotate API keys regularly

Store keys in environment variables

Limit key permissions

Audit Logs

Enable audit logging in Grafana

Monitor user activity

Regular security reviews

Scaling
High Availability
For production:

Run multiple Grafana instances behind load balancer

Use shared database (PostgreSQL) for session storage

Configure external object storage for dashboards

Set up auto-scaling based on load

Performance Tuning
ini
# grafana.ini optimizations
[server]
max_open_files = 10000

[database]
max_idle_conn = 10
max_open_conn = 100

[analytics]
reporting_enabled = false
Support
For issues:

Check Grafana logs: docker-compose logs grafana

Verify datasource connectivity

Test Prometheus queries directly

Review dashboard JSON syntax

Check file permissions

Additional Resources
Grafana Documentation

Prometheus Querying

Dashboard JSON Model

Alerting Best Practices

text

## Complete Setup Instructions

1. **Create the directory structure**:
```bash
mkdir -p parking-management/deployment/docker/monitoring/grafana/provisioning/{dashboards/{databases,caching,apis,infrastructure},datasources}
Create all the files with the code provided above

Make scripts executable:

bash
chmod +x parking-management/deployment/docker/monitoring/grafana/setup-dashboards.sh
chmod +x parking-management/deployment/docker/monitoring/grafana/dashboard-manager.sh
Start Grafana:

bash
cd parking-management/deployment/docker
docker-compose up -d grafana
Access the dashboards:

Open http://localhost:3003

Login with admin/admin123

Navigate to "Parking Management" folder to see all dashboards

This comprehensive Grafana setup provides complete monitoring for the Parking Management System with pre-configured dashboards, alerting rules, and management tools for production use.
