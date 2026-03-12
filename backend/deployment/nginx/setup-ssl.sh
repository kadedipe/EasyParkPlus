#!/bin/bash

# SSL Certificate Setup Script
DOMAIN=${1:-"api.parking-management.com"}
EMAIL=${2:-"admin@parking-management.com"}

echo "Setting up SSL certificates for $DOMAIN"

# Check if certificates already exist
if [ -d "/etc/nginx/ssl/live/$DOMAIN" ]; then
    echo "Certificates already exist. Renewing if needed..."
    certbot renew --nginx
else
    echo "Obtaining new certificates..."
    certbot --nginx \
        --non-interactive \
        --agree-tos \
        --email $EMAIL \
        --domains $DOMAIN \
        --redirect \
        --keep-until-expiring
fi

# Reload nginx to apply changes
nginx -s reload

echo "SSL setup completed for $DOMAIN"