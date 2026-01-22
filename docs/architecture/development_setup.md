# Development Setup - Parking Management System

## Overview

This document provides comprehensive instructions for setting up a local development environment for the Parking Management System. It covers everything from prerequisites to running the complete system locally.

## Prerequisites

### Required Software
```yaml
prerequisites:
  operating-system:
    - macOS: 11+ (Big Sur or newer)
    - Windows: 10/11 with WSL2
    - Linux: Ubuntu 20.04+, Fedora 35+, or CentOS 8+
  
  core-tools:
    - git: 2.30+
    - curl: 7.68+
    - wget: 1.20+
    - jq: 1.6+
    - make: 4.3+
  
  java-development:
    - jdk: OpenJDK 17 (Amazon Corretto or Temurin recommended)
    - maven: 3.8.4+ (or Gradle 7.4+)
    - ide:
      - IntelliJ IDEA Ultimate (recommended)
      - Visual Studio Code with Java extensions
      - Eclipse IDE for Enterprise Java
  
  containerization:
    - docker: 20.10+
    - docker-compose: 2.6+
    - kubernetes:
      - minikube: 1.25+ (for local k8s)
      - kind: 0.14+ (for k8s in Docker)
      - k3d: 5.4+ (lightweight k8s)
  
  infrastructure:
    - terraform: 1.3+
    - aws-cli: 2.7+ (configured with credentials)
    - kubectl: 1.24+
    - helm: 3.9+
  
  database-tools:
    - psql: PostgreSQL client 14+
    - redis-cli: 7.0+
    - mongosh: MongoDB shell 6.0+
  
  messaging:
    - kafkacat: for Kafka debugging
    - rabbitmqadmin: for RabbitMQ management
  
  monitoring:
    - promtool: for Prometheus rule validation
    - amtool: for AlertManager configuration