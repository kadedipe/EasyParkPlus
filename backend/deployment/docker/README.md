# Parking Management System - Docker Deployment

This directory contains the Docker Compose configuration for deploying the complete Parking Management System.

## Prerequisites

1. **Docker** (version 20.10.0+)
2. **Docker Compose** (version 2.0.0+)
3. **At least 8GB RAM** available for Docker
4. **At least 20GB free disk space**

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd parking-management

# Make deployment script executable
chmod +x scripts/deploy.sh

# Copy environment template
cp deployment/docker/.env.example .env

# Edit environment variables (important!)
nano .env