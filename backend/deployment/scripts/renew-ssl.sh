#!/bin/bash

# SSL Certificate Renewal Script

set -e

DOMAIN=${1:-"api.parking-management.com"}
EMAIL=${2:-"admin@parking-management.com"}

echo "Starting SSL certificate renewal for ${DOMAIN}"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "Certbot is not installed. Installing..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Renew certificates
certbot renew --nginx --non-interactive --quiet

# Reload nginx to apply new certificates
if command -v docker &> /dev/null; then
    docker exec parking-nginx nginx -s reload
else
    systemctl reload nginx
fi

# Check expiration dates
echo "Checking certificate expiration dates..."
if [ -f "/etc/letsencrypt/live/${DOMAIN}/cert.pem" ]; then
    openssl x509 -in "/etc/letsencrypt/live/${DOMAIN}/cert.pem" -noout -enddate
fi

echo "SSL certificate renewal completed"