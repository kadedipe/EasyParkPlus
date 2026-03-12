#!/bin/bash

# Make all scripts executable

chmod +x deploy.sh
chmod +x backup-db.sh
chmod +x restore-db.sh
chmod +x setup-env.sh
chmod +x renew-ssl.sh
chmod +x monitor.sh
chmod +x rotate-logs.sh
chmod +x health-check.sh

echo "All scripts are now executable"