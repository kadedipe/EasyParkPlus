# PostgreSQL Dockerfile for Parking Management System
# Multi-stage build for production-ready PostgreSQL with optimizations

# Stage 1: Builder for extensions and tools
FROM alpine:3.19 AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    make \
    postgresql15-dev \
    clang15 \
    llvm15 \
    musl-dev \
    openssl-dev \
    readline-dev \
    zlib-dev \
    linux-headers \
    perl \
    python3 \
    git \
    && rm -rf /var/cache/apk/*

# Clone and build pg_stat_statements extension
WORKDIR /build
RUN git clone --branch REL_15_5 https://github.com/postgres/postgres.git \
    && cd postgres/contrib/pg_stat_statements \
    && make \
    && make install

# Build pgcrypto extension
RUN cd /build/postgres/contrib/pgcrypto \
    && make \
    && make install

# Stage 2: Production PostgreSQL image
FROM postgres:15-alpine

LABEL maintainer="Parking Management Team <dev@parking-management.com>"
LABEL version="1.0.0"
LABEL description="Production PostgreSQL for Parking Management System"

# Environment variables for configuration
ENV POSTGRES_DB=parking_db \
    POSTGRES_USER=parking_user \
    POSTGRES_PASSWORD= \
    PGDATA=/var/lib/postgresql/data/pgdata \
    PGPORT=5432 \
    LANG=en_US.utf8 \
    TZ=UTC

# Install additional tools and extensions
RUN apk add --no-cache \
    tzdata \
    openssl \
    ca-certificates \
    postgresql15-contrib \
    postgresql15-plpython3 \
    pv \
    gnupg \
    && rm -rf /var/cache/apk/*

# Copy built extensions from builder stage
COPY --from=builder /usr/local/lib/postgresql/pg_stat_statements.so /usr/local/lib/postgresql/
COPY --from=builder /usr/local/lib/postgresql/pgcrypto.so /usr/local/lib/postgresql/

# Copy configuration files
COPY postgresql.conf /usr/local/share/postgresql/postgresql.conf.sample
COPY pg_hba.conf /usr/local/share/postgresql/pg_hba.conf.sample

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/
COPY init-extensions.sql /docker-entrypoint-initdb.d/
COPY backup.sh /usr/local/bin/
COPY healthcheck.sh /usr/local/bin/

# Copy custom scripts directory
RUN mkdir -p /opt/postgres/scripts
COPY scripts/ /opt/postgres/scripts/
RUN chmod +x /opt/postgres/scripts/*.sh

# Set up directories and permissions
RUN mkdir -p /var/lib/postgresql/backups \
    && mkdir -p /var/log/postgresql \
    && chown -R postgres:postgres /var/lib/postgresql \
    && chown -R postgres:postgres /var/log/postgresql \
    && chmod 755 /usr/local/bin/backup.sh \
    && chmod 755 /usr/local/bin/healthcheck.sh \
    && chmod 755 /opt/postgres/scripts/*.sh

# Create symlinks for easy configuration access
RUN ln -sf /usr/local/share/postgresql/postgresql.conf.sample /opt/postgresql.conf \
    && ln -sf /usr/local/share/postgresql/pg_hba.conf.sample /opt/pg_hba.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD ["healthcheck.sh"]

# Switch to postgres user
USER postgres

# Expose PostgreSQL port
EXPOSE 5432

# Volume for persistent data
VOLUME ["/var/lib/postgresql/data"]

# Entrypoint override to apply custom configurations
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["postgres"]