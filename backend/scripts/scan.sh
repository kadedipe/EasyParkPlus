#!/bin/bash
set -e

echo "🔒 Scanning Docker image for vulnerabilities..."

# Run Trivy scan
docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image \
    --severity CRITICAL,HIGH \
    --no-progress \
    parking-backend:latest

# Run Dockle for best practices check
docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    goodwithtech/dockle \
    parking-backend:latest

echo "✅ Scan complete"