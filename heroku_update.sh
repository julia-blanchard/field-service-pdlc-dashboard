#!/bin/bash

# Heroku Scheduler script - runs data updates in cloud
# No local machine needed!

set -e  # Exit on error

echo "$(date): Starting Heroku scheduled update..."

# Authenticate with Salesforce using stored credentials
echo "$(date): Authenticating with Salesforce..."
echo "$SF_PASSWORD$SF_SECURITY_TOKEN" | sf org login password \
    --username "$SF_USERNAME" \
    --instance-url https://login.salesforce.com \
    --set-default-dev-hub \
    --set-default \
    --alias gus_heroku

# Set target org for scripts
export TARGET_ORG="gus_heroku"

# Fetch all data
echo "$(date): Fetching execution data..."
python3 fetch_execution_data.py

echo "$(date): Fetching teams data..."
python3 fetch_teams_data.py

echo "$(date): Fetching unmapped details..."
python3 fetch_unmapped_details.py

echo "$(date): Data update complete!"
echo "$(date): App will automatically reload with fresh data"
