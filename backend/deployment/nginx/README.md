# Nginx Configuration for Parking Management API

## Overview
This directory contains Nginx configuration for the Parking Management backend API.

## Structure
- `nginx.conf` - Main Nginx configuration
- `sites-available/` - Available site configurations
- `sites-enabled/` - Enabled site configurations (symlinks)
- `conf.d/` - Additional configuration snippets
- `ssl/` - SSL certificates
- `logs/` - Nginx access and error logs
- `cache/` - Cache directory

## Setup

### Development
1. Use the development configuration:
   ```bash
   ln -sf ../sites-available/parking-management-dev.conf sites-enabled/