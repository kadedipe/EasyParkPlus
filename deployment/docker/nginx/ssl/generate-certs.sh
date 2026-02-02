#!/bin/bash
# Generate self-signed SSL certificates for development

set -e

echo "🔐 Generating SSL certificates for local development..."

# Create SSL directory if it doesn't exist
mkdir -p /etc/nginx/ssl

# Generate private key
openssl genrsa -out /etc/nginx/ssl/key.pem 2048

# Generate certificate signing request
openssl req -new -key /etc/nginx/ssl/key.pem -out /etc/nginx/ssl/csr.pem \
  -subj "/C=US/ST=State/L=City/O=Parking Management/CN=localhost"

# Generate self-signed certificate
openssl x509 -req -days 365 -in /etc/nginx/ssl/csr.pem -signkey /etc/nginx/ssl/key.pem \
  -out /etc/nginx/ssl/cert.pem

# Set proper permissions
chmod 600 /etc/nginx/ssl/key.pem
chmod 644 /etc/nginx/ssl/cert.pem

# Clean up CSR
rm -f /etc/nginx/ssl/csr.pem

echo "✅ SSL certificates generated successfully!"
echo "   Key: /etc/nginx/ssl/key.pem"
echo "   Cert: /etc/nginx/ssl/cert.pem"