#!/bin/bash

# Heroku Scheduler script - runs data updates in cloud
# No local machine needed!

set -e  # Exit on error

echo "$(date): Starting Heroku scheduled update..."

# Authenticate with Salesforce using stored OAuth URL
# This is more secure than password+token and works with SSO
echo "$(date): Authenticating with Salesforce..."
if [ -n "$SFDX_AUTH_URL" ]; then
    echo "$SFDX_AUTH_URL" > /tmp/auth.txt
    sf org login sfdx-url --sfdx-url-file /tmp/auth.txt --alias gus_heroku --set-default
    rm /tmp/auth.txt
    export TARGET_ORG="gus_heroku"
else
    echo "ERROR: SFDX_AUTH_URL not set in Heroku config vars"
    exit 1
fi

# Fetch all data
echo "$(date): Fetching execution data..."
python3 fetch_execution_data.py

echo "$(date): Fetching teams data..."
python3 fetch_teams_data.py

echo "$(date): Fetching unmapped details..."
python3 fetch_unmapped_details.py

echo "$(date): Data update complete!"
echo "$(date): App will automatically reload with fresh data"
