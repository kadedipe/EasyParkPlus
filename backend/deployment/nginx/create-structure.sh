#!/bin/bash

# Create directory structure
mkdir -p sites-available
mkdir -p sites-enabled
mkdir -p conf.d
mkdir -p ssl/live
mkdir -p logs
mkdir -p cache
mkdir -p ../static

# Create symbolic link for site configuration (adjust as needed)
if [ ! -L sites-enabled/parking-management.conf ]; then
    ln -s ../sites-available/parking-management.conf sites-enabled/
fi

# Set permissions
chmod -R 755 logs
chmod -R 755 cache

echo "Nginx directory structure created successfully"