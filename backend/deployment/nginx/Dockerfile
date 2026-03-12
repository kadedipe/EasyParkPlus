FROM nginx:alpine

# Install certbot for SSL certificates
RUN apk add --no-cache certbot certbot-nginx

# Remove default nginx config
RUN rm -rf /etc/nginx/conf.d/default.conf

# Create necessary directories
RUN mkdir -p /etc/nginx/sites-available \
    && mkdir -p /etc/nginx/sites-enabled \
    && mkdir -p /var/www/certbot \
    && mkdir -p /etc/nginx/ssl

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY sites-available/ /etc/nginx/sites-available/

# Create symbolic link for site configuration
RUN ln -s /etc/nginx/sites-available/parking-management.conf /etc/nginx/sites-enabled/

# Copy SSL setup script
COPY setup-ssl.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/setup-ssl.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD nginx -t || exit 1

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]