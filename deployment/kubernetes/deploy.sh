#!/bin/bash

# Parking Management System Kubernetes Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="parking-management-cluster"
REGION="us-central1"
PROJECT_ID="parking-management-prod"
NAMESPACES=("parking-system" "parking-monitoring")

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Parking Management System - Kubernetes Deployment${NC}"
echo -e "${BLUE}========================================${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}kubectl is required but not installed. Aborting.${NC}" >&2; exit 1; }
    command -v helm >/dev/null 2>&1 || { echo -e "${RED}helm is required but not installed. Aborting.${NC}" >&2; exit 1; }
    command -v kustomize >/dev/null 2>&1 || { echo -e "${RED}kustomize is required but not installed. Aborting.${NC}" >&2; exit 1; }
    command -v gcloud >/dev/null 2>&1 || { echo -e "${RED}gcloud is required but not installed. Aborting.${NC}" >&2; exit 1; }
    
    echo -e "${GREEN}✓ Prerequisites checked${NC}"
}

# Create cluster if not exists
create_cluster() {
    echo -e "${YELLOW}Checking if cluster exists...${NC}"
    
    if ! gcloud container clusters describe $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
        echo -e "${YELLOW}Creating GKE cluster...${NC}"
        gcloud container clusters create $CLUSTER_NAME \
            --region=$REGION \
            --project=$PROJECT_ID \
            --num-nodes=3 \
            --machine-type=e2-standard-4 \
            --enable-autoscaling \
            --min-nodes=3 \
            --max-nodes=10 \
            --enable-vertical-pod-autoscaling \
            --enable-autorepair \
            --enable-autoupgrade \
            --workload-pool=$PROJECT_ID.svc.id.goog
        
        echo -e "${GREEN}✓ Cluster created${NC}"
    else
        echo -e "${GREEN}✓ Cluster already exists${NC}"
    fi
    
    # Get credentials
    gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID
}

# Create namespaces
create_namespaces() {
    echo -e "${YELLOW}Creating namespaces...${NC}"
    
    for ns in "${NAMESPACES[@]}"; do
        if ! kubectl get namespace $ns >/dev/null 2>&1; then
            kubectl create namespace $ns
            echo -e "${GREEN}✓ Namespace $ns created${NC}"
        else
            echo -e "${GREEN}✓ Namespace $ns already exists${NC}"
        fi
    done
}

# Install NGINX Ingress Controller
install_ingress_controller() {
    echo -e "${YELLOW}Installing NGINX Ingress Controller...${NC}"
    
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    
    helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.type=LoadBalancer \
        --set controller.autoscaling.enabled=true \
        --set controller.autoscaling.minReplicas=2 \
        --set controller.autoscaling.maxReplicas=5 \
        --set controller.metrics.enabled=true \
        --set controller.metrics.serviceMonitor.enabled=true
    
    echo -e "${GREEN}✓ NGINX Ingress Controller installed${NC}"
}

# Install Cert Manager
install_cert_manager() {
    echo -e "${YELLOW}Installing Cert Manager...${NC}"
    
    helm repo add jetstack https://charts.jetstack.io
    helm repo update
    
    helm upgrade --install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --create-namespace \
        --set installCRDs=true \
        --set prometheus.enabled=true \
        --set webhook.timeoutSeconds=30
    
    # Wait for cert-manager to be ready
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=120s
    
    # Create cluster issuer
    cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@parking.example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
    
    echo -e "${GREEN}✓ Cert Manager installed${NC}"
}

# Install Prometheus Stack
install_prometheus_stack() {
    echo -e "${YELLOW}Installing Prometheus Stack...${NC}"
    
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace parking-monitoring \
        --set grafana.enabled=true \
        --set grafana.adminPassword=admin \
        --set prometheus.prometheusSpec.retention=30d \
        --set prometheus.prometheusSpec.resources.requests.memory=2Gi \
        --set prometheus.prometheusSpec.resources.limits.memory=4Gi \
        --set alertmanager.enabled=true
    
    echo -e "${GREEN}✓ Prometheus Stack installed${NC}"
}

# Install Loki for logging
install_loki() {
    echo -e "${YELLOW}Installing Loki...${NC}"
    
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    helm upgrade --install loki grafana/loki-stack \
        --namespace parking-monitoring \
        --set grafana.enabled=false \
        --set prometheus.enabled=false \
        --set promtail.enabled=true \
        --set loki.persistence.enabled=true \
        --set loki.persistence.size=50Gi
    
    echo -e "${GREEN}✓ Loki installed${NC}"
}

# Deploy application using Kustomize
deploy_application() {
    echo -e "${YELLOW}Deploying application with Kustomize...${NC}"
    
    # Generate deployment timestamp
    DEPLOYMENT_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    export DEPLOYMENT_TIME
    
    # Apply kustomize
    kustomize build . | kubectl apply -f -
    
    echo -e "${GREEN}✓ Application deployed${NC}"
}

# Wait for deployments to be ready
wait_for_deployments() {
    echo -e "${YELLOW}Waiting for deployments to be ready...${NC}"
    
    for ns in "${NAMESPACES[@]}"; do
        kubectl wait --for=condition=available deployment --all -n $ns --timeout=300s
        kubectl wait --for=condition=ready pod -l app -n $ns --timeout=300s
    done
    
    echo -e "${GREEN}✓ All deployments are ready${NC}"
}

# Setup horizontal pod autoscaling
setup_hpa() {
    echo -e "${YELLOW}Setting up HPA...${NC}"
    
    # Apply HPA configurations
    kubectl apply -f hpa/ -n parking-system
    
    echo -e "${GREEN}✓ HPA configured${NC}"
}

# Create database backups
setup_backups() {
    echo -e "${YELLOW}Setting up database backups...${NC}"
    
    # Create backup cron job
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: parking-system
spec:
  schedule: "0 */6 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:14-alpine
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_PASSWORD
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres-service -U parking_admin parking_db | gzip > /backups/backup-\$(date +%Y%m%d-%H%M%S).sql.gz
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: postgres-backup-pvc
EOF
    
    echo -e "${GREEN}✓ Backups configured${NC}"
}

# Display service endpoints
show_endpoints() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # Get Kong external IP
    KONG_IP=$(kubectl get svc kong-proxy -n parking-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    echo -e "${YELLOW}API Gateway:${NC} http://$KONG_IP"
    echo -e "${YELLOW}API Gateway (SSL):${NC} https://$KONG_IP"
    
    # Get Grafana external IP
    GRAFANA_IP=$(kubectl get svc grafana -n parking-monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    echo -e "${YELLOW}Grafana:${NC} http://$GRAFANA_IP"
    echo -e "${YELLOW}Grafana Credentials:${NC} admin / Gr@fana2024!Admin"
    
    # Get Prometheus external IP
    PROMETHEUS_IP=$(kubectl get svc prometheus -n parking-monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    echo -e "${YELLOW}Prometheus:${NC} http://$PROMETHEUS_IP:9090"
    
    echo -e "${BLUE}========================================${NC}"
}

# Health check
health_check() {
    echo -e "${YELLOW}Running health checks...${NC}"
    
    # Check all pods are running
    for ns in "${NAMESPACES[@]}"; do
        NOT_RUNNING=$(kubectl get pods -n $ns --field-selector=status.phase!=Running --no-headers | wc -l)
        if [ $NOT_RUNNING -gt 0 ]; then
            echo -e "${RED}⚠ Some pods in $ns are not running${NC}"
            kubectl get pods -n $ns --field-selector=status.phase!=Running
        else
            echo -e "${GREEN}✓ All pods in $ns are running${NC}"
        fi
    done
    
    # Check services
    kubectl get svc --all-namespaces
}

# Main deployment function
main() {
    echo -e "${BLUE}Starting deployment at $(date)${NC}"
    
    check_prerequisites
    create_cluster
    create_namespaces
    install_ingress_controller
    install_cert_manager
    install_prometheus_stack
    install_loki
    deploy_application
    wait_for_deployments
    setup_hpa
    setup_backups
    show_endpoints
    health_check
    
    echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
}

# Run main function
main "$@"