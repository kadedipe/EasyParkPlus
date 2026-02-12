markdown
# Parking Management System - Kubernetes Deployment

## Overview

This directory contains the Kubernetes deployment configuration for the Parking Management System. The deployment includes microservices, databases, API gateway, and monitoring stack.

## Architecture
┌─────────────────────────────────────────────────────────────┐
│ Ingress Controller │
│ (NGINX) │
└─────────────────┬─────────────────────────────────────────┘
│
┌─────────────────▼─────────────────────────────────────────┐
│ API Gateway │
│ (Kong) │
└─────────┬─────────┬─────────┬─────────┬──────────────────┘
│ │ │ │
┌─────────▼─┐ ┌─────▼─────┐ ┌▼─────────┐ ┌▼────────────────┐
│ Parking │ │ User │ │ Payment │ │ Notification │
│ API │ │ Service │ │ Service │ │ Service │
└─────────┬─┘ └─────┬─────┘ └┬────────┘ └┬────────────────┘
│ │ │ │
┌─────────▼─────────▼────────▼──────────▼─────────────────┐
│ PostgreSQL │
│ (Primary/Replica) │
└────────────────────────────────────────────────────────┘
│
┌─────────▼───────────────────────────────────────────────┐
│ Redis │
│ (Cache/Session) │
└────────────────────────────────────────────────────────┘

text

## Prerequisites

- Kubernetes 1.24+
- kubectl 1.24+
- Helm 3.8+
- Kustomize 4.5+
- Google Cloud SDK (for GKE deployment)
- Docker (for building images)

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/parking-management/deployment.git
cd deployment/kubernetes
2. Configure Environment
Copy the example environment file and update with your values:

bash
cp .env.example .env
source .env
3. Deploy to Kubernetes
Using Makefile:

bash
# Deploy everything
make deploy-all

# Or deploy step by step
make deploy-namespaces
make deploy-secrets
make deploy-configmaps
make deploy-storage
make deploy-databases
make deploy-backend
make deploy-gateway
make deploy-monitoring
make deploy-network-policies
make deploy-hpa
Using deployment script:

bash
chmod +x deploy.sh
./deploy.sh
4. Verify Deployment
bash
# Check status
make status

# Check logs
make logs

# Run tests
make test
Directory Structure
text
kubernetes/
├── configmaps/           # Configuration files
├── secrets/             # Kubernetes secrets (encrypted)
├── storage/             # Persistent volume claims
├── databases/           # PostgreSQL and Redis
├── backend/            # Microservices
├── gateway/            # Kong API Gateway
├── monitoring/         # Prometheus, Grafana, etc.
├── hpa/               # Horizontal Pod Autoscalers
├── network-policies/  # Network security policies
├── patches/           # Kustomize patches
├── kustomization.yaml # Kustomize configuration
├── deploy.sh         # Deployment script
├── Makefile          # Make commands
└── README.md         # This file
Services
Backend Services
Service	Port	Replicas	Description
parking-api	8080	3-10	Main parking management API
user-service	8080	2-8	User management and authentication
payment-service	8080	2-6	Payment processing
notification-service	8080	2	Email/SMS notifications
analytics-service	8080	1	Usage analytics
Databases
Service	Port	Type	Storage
PostgreSQL	5432	Primary/Replica	50GB + 20GB WAL
Redis	6379	Cluster with Sentinel	20GB
Monitoring
Service	Port	Description
Prometheus	9090	Metrics collection
Grafana	3000	Visualization
Loki	3100	Log aggregation
Node Exporter	9100	Host metrics
cAdvisor	8080	Container metrics
Configuration

Resource Limits
Default resource limits can be adjusted in the deployment files:

yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
Scaling
Horizontal Pod Autoscaling
HPA is configured for services with the following thresholds:

parking-api: CPU > 70%, Memory > 80%, or 100 req/s

user-service: CPU > 70% or 50 req/s

payment-service: CPU > 70%

Vertical Pod Autoscaling
VPA is enabled on the GKE cluster and automatically adjusts resource requests.

Monitoring
Grafana Dashboards
Access Grafana at http://grafana.parking-monitoring:3000 (default credentials: admin/Gr@fana2024!Admin)

Pre-configured dashboards:

PostgreSQL Performance

Redis Performance

Docker Containers

System Metrics

API Gateway Metrics

API Response Times

Kubernetes Cluster

Prometheus Alerts
Alert rules are defined for:

High CPU/Memory usage

Disk space low

Pod restarts

Slow API responses

High error rates

Database down

Replication lag

Backup and Recovery
Database Backups
Automated backups run every 6 hours:

bash
# Manual backup
kubectl create job --from=cronjob/postgres-backup manual-backup -n parking-system

# Restore from backup
kubectl exec -it postgres-0 -n parking-system -- psql -U parking_admin -d parking_db < backup.sql
Security
Network Policies
Default deny-all policy is enforced. Explicit allow rules are defined for:

API Gateway to services

Services to databases

Monitoring to services

TLS/SSL
Cert Manager automatically provisions and renews SSL certificates from Let's Encrypt.

Secrets Management
Sensitive data is stored in Kubernetes Secrets and optionally integrated with:

HashiCorp Vault

Google Cloud Secret Manager

AWS Secrets Manager

Troubleshooting
Common Issues
Pods not starting

bash
kubectl describe pod <pod-name> -n parking-system
kubectl logs <pod-name> -n parking-system
Database connection issues

bash
kubectl exec -it postgres-0 -n parking-system -- pg_isready
kubectl exec -it redis-0 -n parking-system -- redis-cli ping
Monitoring not working

bash
kubectl port-forward -n parking-monitoring service/prometheus 9090:9090
kubectl port-forward -n parking-monitoring service/grafana 3000:3000
Health Checks
bash
# Check all services
make status

# Check specific service
kubectl get endpoints <service-name> -n parking-system

# Check HPA status
kubectl get hpa -n parking-system
Maintenance
Rolling Updates
bash
# Update image
kubectl set image deployment/parking-api parking-api=parking-management/parking-api:v2.0.0 -n parking-system

# Check rollout status
kubectl rollout status deployment/parking-api -n parking-system

# Rollback if needed
kubectl rollout undo deployment/parking-api -n parking-system
Scaling
bash
# Manual scaling
kubectl scale deployment parking-api --replicas=5 -n parking-system

# Auto-scaling (HPA)
kubectl get hpa -n parking-system
Cleanup
bash
# Delete all resources
make clean

# Delete cluster
make delete-cluster
Support
For issues and questions:

GitHub Issues: https://github.com/parking-management/deployment/issues

Documentation: https://docs.parking.example.com

Slack: #parking-management-deployment