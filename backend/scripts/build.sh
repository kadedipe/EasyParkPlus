#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🏗️  Building Parking Management System Backend${NC}"
echo "=========================================="

# Get version from git
VERSION=$(git describe --tags --always --dirty)
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

# Function to build image
build_image() {
    local target=$1
    local tag=$2
    
    echo -e "${YELLOW}Building ${target} image...${NC}"
    
    docker build \
        --target ${target} \
        --build-arg APP_VERSION=${VERSION} \
        --build-arg BUILD_DATE=${BUILD_DATE} \
        -t parking-backend:${tag} \
        -f Dockerfile \
        .
    
    echo -e "${GREEN}✅ ${target} image built successfully${NC}"
}

# Build development image
build_image "development" "dev"

# Build production image
build_image "production" "latest"

# Tag production image with version
docker tag parking-backend:latest parking-backend:${VERSION}

echo -e "${GREEN}✅ All images built successfully${NC}"
echo ""
echo "Images:"
echo "  - parking-backend:dev"
echo "  - parking-backend:latest"
echo "  - parking-backend:${VERSION}"