#!/bin/bash
# Custom Docker entrypoint for PostgreSQL with enhanced configuration

set -e

# Function to generate SSL certificates if not present
generate_ssl_certificates() {
    local ssl_dir="/var/lib/postgresql"
    local cert_file="$ssl_dir/server.crt"
    local key_file="$ssl_dir/server.key"
    
    if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
        echo "Generating SSL certificates..."
        
        # Create directory if it doesn't exist
        mkdir -p "$ssl_dir"
        
        # Generate private key
        openssl genrsa -out "$key_file" 2048 2>/dev/null
        
        # Generate certificate
        openssl req -new -x509 -days 365 -key "$key_file" -out "$cert_file" \
            -subj "/C=US/ST=State/L=City/O=Parking Management/CN=postgres" 2>/dev/null
        
        # Set proper permissions
        chmod 600 "$key_file"
        chmod 644 "$cert_file"
        chown postgres:postgres "$key_file" "$cert_file"
        
        echo "SSL certificates generated successfully"
    else
        echo "SSL certificates already exist"
    fi
}

# Function to apply custom configurations
apply_custom_config() {
    local config_dir="/usr/local/share/postgresql"
    local data_dir="$PGDATA"
    
    echo "Applying custom PostgreSQL configuration..."
    
    # Copy custom configuration files if they exist
    if [ -f "$config_dir/postgresql.conf.sample" ]; then
        cp "$config_dir/postgresql.conf.sample" "$data_dir/postgresql.conf"
        echo "Applied custom postgresql.conf"
    fi
    
    if [ -f "$config_dir/pg_hba.conf.sample" ]; then
        cp "$config_dir/pg_hba.conf.sample" "$data_dir/pg_hba.conf"
        echo "Applied custom pg_hba.conf"
    fi
    
    # Set permissions
    chown postgres:postgres "$data_dir"/*.conf
}

# Function to initialize database if not exists
initialize_database() {
    if [ -z "$(ls -A "$PGDATA")" ]; then
        echo "Initializing database..."
        
        # Run original entrypoint initdb
        initdb --username="$POSTGRES_USER" --pwfile=<(echo "$POSTGRES_PASSWORD")
        
        # Apply custom configuration
        apply_custom_config
        
        # Generate SSL certificates
        generate_ssl_certificates
        
        # Start PostgreSQL temporarily to run init scripts
        pg_ctl -D "$PGDATA" -o "-c listen_addresses='localhost'" -w start
        
        # Create additional databases if specified
        if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
            for db in $(echo "$POSTGRES_MULTIPLE_DATABASES" | tr ',' ' '); do
                echo "Creating database: $db"
                createdb --username="$POSTGRES_USER" "$db"
            done
        fi
        
        # Stop temporary instance
        pg_ctl -D "$PGDATA" -m fast -w stop
        
        echo "Database initialization complete"
    else
        echo "Database already exists, skipping initialization"
    fi
}

# Function to set up replication if configured
setup_replication() {
    if [ -n "$REPLICATION_ROLE" ]; then
        echo "Setting up replication as: $REPLICATION_ROLE"
        
        if [ "$REPLICATION_ROLE" = "primary" ]; then
            # Configure primary for replication
            echo "wal_level = replica" >> "$PGDATA/postgresql.conf"
            echo "max_wal_senders = 10" >> "$PGDATA/postgresql.conf"
            echo "wal_keep_size = 1GB" >> "$PGDATA/postgresql.conf"
            echo "max_replication_slots = 10" >> "$PGDATA/postgresql.conf"
            
            # Create replication user
            if [ -n "$REPLICATION_USER" ] && [ -n "$REPLICATION_PASSWORD" ]; then
                psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
                    CREATE ROLE $REPLICATION_USER WITH REPLICATION LOGIN PASSWORD '$REPLICATION_PASSWORD';
                EOSQL
            fi
            
        elif [ "$REPLICATION_ROLE" = "standby" ] && [ -n "$PRIMARY_HOST" ]; then
            # Configure standby
            rm -rf "$PGDATA"/*
            
            # Take base backup from primary
            PGPASSWORD=$REPLICATION_PASSWORD pg_basebackup \
                -h "$PRIMARY_HOST" \
                -p "$PRIMARY_PORT" \
                -U "$REPLICATION_USER" \
                -D "$PGDATA" \
                -P \
                -R
            
            # Update recovery configuration
            echo "primary_conninfo = 'host=$PRIMARY_HOST port=$PRIMARY_PORT user=$REPLICATION_USER password=$REPLICATION_PASSWORD'" >> "$PGDATA/postgresql.conf"
            echo "promote_trigger_file = '/tmp/promote_to_primary'" >> "$PGDATA/postgresql.conf"
        fi
    fi
}

# Function to run maintenance tasks
run_maintenance_tasks() {
    echo "Running maintenance tasks..."
    
    # Create backup directory
    mkdir -p /var/lib/postgresql/backups
    
    # Set up cron for automatic backups if enabled
    if [ "$AUTO_BACKUP" = "true" ]; then
        echo "Setting up automatic backups..."
        echo "0 2 * * * /usr/local/bin/backup.sh >> /var/log/postgresql/backup.log 2>&1" > /etc/crontabs/postgres
        crond -b -l 8
    fi
}

# Function to log environment for debugging
log_environment() {
    echo "=== PostgreSQL Environment ==="
    echo "POSTGRES_USER: $POSTGRES_USER"
    echo "POSTGRES_DB: $POSTGRES_DB"
    echo "PGDATA: $PGDATA"
    echo "PGPORT: $PGPORT"
    echo "REPLICATION_ROLE: $REPLICATION_ROLE"
    echo "============================="
}

# Main execution
main() {
    # Log environment for debugging
    log_environment
    
    # Initialize database if needed
    initialize_database
    
    # Set up replication if configured
    setup_replication
    
    # Run maintenance tasks
    run_maintenance_tasks
    
    # Generate SSL certificates if not present
    generate_ssl_certificates
    
    # Pass control to original PostgreSQL entrypoint
    echo "Starting PostgreSQL..."
    exec "$@"
}

# Run main function
main "$@"