#!/bin/bash

# Wazuh AI Companion Kubernetes Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="wazuh"
DOCKER_IMAGE="wazuh-ai-companion:2.0.0"

echo -e "${BLUE}🚀 Deploying Wazuh AI Companion to Kubernetes${NC}"

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl is not installed or not in PATH${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ kubectl is available${NC}"
}

# Function to check cluster connectivity
check_cluster() {
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Connected to Kubernetes cluster${NC}"
}

# Function to build and push Docker image
build_image() {
    echo -e "${YELLOW}🔨 Building Docker image...${NC}"
    docker build -t ${DOCKER_IMAGE} --target production .
    
    # If using a registry, push the image
    # docker tag ${DOCKER_IMAGE} your-registry.com/${DOCKER_IMAGE}
    # docker push your-registry.com/${DOCKER_IMAGE}
    
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
}

# Function to create namespace
create_namespace() {
    echo -e "${YELLOW}📁 Creating namespace...${NC}"
    kubectl apply -f namespace.yaml
    echo -e "${GREEN}✅ Namespace created${NC}"
}

# Function to deploy secrets
deploy_secrets() {
    echo -e "${YELLOW}🔐 Deploying secrets...${NC}"
    
    # Check if secrets need to be updated with real values
    echo -e "${YELLOW}⚠️  Please ensure secrets.yaml contains real base64-encoded values${NC}"
    echo -e "${YELLOW}⚠️  Current values are examples and should be changed for production${NC}"
    
    kubectl apply -f secrets.yaml
    echo -e "${GREEN}✅ Secrets deployed${NC}"
}

# Function to deploy ConfigMaps
deploy_configmaps() {
    echo -e "${YELLOW}⚙️  Deploying ConfigMaps...${NC}"
    kubectl apply -f configmap.yaml
    echo -e "${GREEN}✅ ConfigMaps deployed${NC}"
}

# Function to deploy persistent volumes
deploy_storage() {
    echo -e "${YELLOW}💾 Deploying persistent volumes...${NC}"
    kubectl apply -f persistent-volumes.yaml
    echo -e "${GREEN}✅ Persistent volumes deployed${NC}"
}

# Function to deploy database
deploy_database() {
    echo -e "${YELLOW}🗄️  Deploying PostgreSQL...${NC}"
    kubectl apply -f postgres-deployment.yaml
    
    # Wait for PostgreSQL to be ready
    echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=postgres -n ${NAMESPACE} --timeout=300s
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
}

# Function to deploy Redis
deploy_redis() {
    echo -e "${YELLOW}🔴 Deploying Redis...${NC}"
    kubectl apply -f redis-deployment.yaml
    
    # Wait for Redis to be ready
    echo -e "${YELLOW}⏳ Waiting for Redis to be ready...${NC}"
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=redis -n ${NAMESPACE} --timeout=300s
    echo -e "${GREEN}✅ Redis is ready${NC}"
}

# Function to deploy Ollama
deploy_ollama() {
    echo -e "${YELLOW}🤖 Deploying Ollama...${NC}"
    kubectl apply -f ollama-deployment.yaml
    
    # Wait for Ollama to be ready (this may take a while due to model download)
    echo -e "${YELLOW}⏳ Waiting for Ollama to be ready (this may take several minutes)...${NC}"
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=ollama -n ${NAMESPACE} --timeout=600s
    echo -e "${GREEN}✅ Ollama is ready${NC}"
}

# Function to deploy main application
deploy_app() {
    echo -e "${YELLOW}🚀 Deploying main application...${NC}"
    kubectl apply -f app-deployment.yaml
    
    # Wait for application to be ready
    echo -e "${YELLOW}⏳ Waiting for application to be ready...${NC}"
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=app -n ${NAMESPACE} --timeout=300s
    echo -e "${GREEN}✅ Application is ready${NC}"
}

# Function to deploy Nginx
deploy_nginx() {
    echo -e "${YELLOW}🌐 Deploying Nginx...${NC}"
    kubectl apply -f nginx-deployment.yaml
    echo -e "${GREEN}✅ Nginx deployed${NC}"
}

# Function to deploy HPA
deploy_hpa() {
    echo -e "${YELLOW}📈 Deploying Horizontal Pod Autoscaler...${NC}"
    kubectl apply -f hpa.yaml
    echo -e "${GREEN}✅ HPA deployed${NC}"
}

# Function to deploy monitoring
deploy_monitoring() {
    echo -e "${YELLOW}📊 Deploying monitoring stack...${NC}"
    kubectl apply -f monitoring-deployment.yaml
    echo -e "${GREEN}✅ Monitoring stack deployed${NC}"
}

# Function to run database migrations
run_migrations() {
    echo -e "${YELLOW}🔄 Running database migrations...${NC}"
    
    # Get the first app pod
    APP_POD=$(kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/component=app -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$APP_POD" ]; then
        echo -e "${RED}❌ No app pods found${NC}"
        return 1
    fi
    
    # Run migrations
    kubectl exec -n ${NAMESPACE} ${APP_POD} -- alembic upgrade head
    echo -e "${GREEN}✅ Database migrations completed${NC}"
}

# Function to show deployment status
show_status() {
    echo -e "${BLUE}📋 Deployment Status${NC}"
    echo -e "${YELLOW}Pods:${NC}"
    kubectl get pods -n ${NAMESPACE}
    
    echo -e "\n${YELLOW}Services:${NC}"
    kubectl get services -n ${NAMESPACE}
    
    echo -e "\n${YELLOW}Ingress:${NC}"
    kubectl get ingress -n ${NAMESPACE}
    
    echo -e "\n${YELLOW}HPA:${NC}"
    kubectl get hpa -n ${NAMESPACE}
}

# Function to get access information
show_access_info() {
    echo -e "${BLUE}🌐 Access Information${NC}"
    
    # Get LoadBalancer IP
    NGINX_IP=$(kubectl get service nginx-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$NGINX_IP" ]; then
        NGINX_IP=$(kubectl get service nginx-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    fi
    
    if [ -n "$NGINX_IP" ]; then
        echo -e "${GREEN}Application URL: http://${NGINX_IP}${NC}"
    else
        echo -e "${YELLOW}LoadBalancer IP not yet assigned. Use port-forward for testing:${NC}"
        echo -e "${YELLOW}kubectl port-forward -n ${NAMESPACE} service/nginx-service 8080:80${NC}"
        echo -e "${YELLOW}Then access: http://localhost:8080${NC}"
    fi
    
    # Grafana access
    echo -e "${GREEN}Grafana URL: http://${NGINX_IP:-localhost}:3000 (admin/admin)${NC}"
    echo -e "${YELLOW}For Grafana port-forward: kubectl port-forward -n ${NAMESPACE} service/grafana-service 3000:3000${NC}"
}

# Main deployment function
main() {
    echo -e "${BLUE}Starting Wazuh AI Companion Kubernetes Deployment${NC}"
    
    # Pre-flight checks
    check_kubectl
    check_cluster
    
    # Build image
    if [ "$1" = "--build" ]; then
        build_image
    fi
    
    # Deploy components in order
    create_namespace
    deploy_secrets
    deploy_configmaps
    deploy_storage
    deploy_database
    deploy_redis
    deploy_ollama
    deploy_app
    deploy_nginx
    deploy_hpa
    
    # Deploy monitoring if requested
    if [ "$1" = "--with-monitoring" ] || [ "$2" = "--with-monitoring" ]; then
        deploy_monitoring
    fi
    
    # Run migrations
    sleep 10  # Give pods time to start
    run_migrations
    
    # Show status
    show_status
    show_access_info
    
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
}

# Handle command line arguments
case "$1" in
    --help|-h)
        echo "Usage: $0 [--build] [--with-monitoring]"
        echo "  --build: Build Docker image before deployment"
        echo "  --with-monitoring: Deploy monitoring stack (Prometheus/Grafana)"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac