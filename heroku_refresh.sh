#!/bin/bash
# Heroku Scheduler job to refresh GUS data
# Runs Mon-Fri at 9 AM and 2 PM Pacific

set -e

echo "Starting Heroku data refresh at $(date)"

# Check if today is a weekday (Monday=1, Sunday=7)
DAY_OF_WEEK=$(date +%u)
if [ "$DAY_OF_WEEK" -gt 5 ]; then
    echo "Today is weekend (day $DAY_OF_WEEK), skipping refresh"
    exit 0
fi

echo "Today is weekday (day $DAY_OF_WEEK), proceeding with refresh"

# Authenticate with Salesforce using SFDX_AUTH_URL from config var
if [ -n "$SFDX_AUTH_URL" ]; then
    echo "Authenticating with Salesforce..."
    echo "$SFDX_AUTH_URL" > sfdx_auth.txt
    sf org login sfdx-url --sfdx-url-file sfdx_auth.txt --alias org62 --set-default
    rm sfdx_auth.txt
    echo "✓ Authenticated"
else
    echo "ERROR: SFDX_AUTH_URL not set in Heroku config vars"
    exit 1
fi

# Fetch execution data
echo "Fetching execution data..."
python3 fetch_execution_data.py
if [ $? -eq 0 ]; then
    echo "✓ Execution data fetched"
else
    echo "ERROR: Failed to fetch execution data"
    exit 1
fi

# Fetch teams data
echo "Fetching teams data..."
python3 fetch_teams_data.py
if [ $? -eq 0 ]; then
    echo "✓ Teams data fetched"
else
    echo "WARNING: Failed to fetch teams data, continuing with cached"
fi

# Fetch unmapped details (for Allocations tab)
echo "Fetching unmapped details..."
python3 fetch_unmapped_details.py
if [ $? -eq 0 ]; then
    echo "✓ Unmapped details fetched"
else
    echo "WARNING: Failed to fetch unmapped details, continuing with cached"
fi

# Analyze hygiene issues (for Needs Attention feature)
echo "Analyzing hygiene issues..."
python3 analyze_hygiene.py
if [ $? -eq 0 ]; then
    echo "✓ Hygiene analysis complete"
else
    echo "WARNING: Failed to analyze hygiene, continuing with cached"
fi

echo "Data refresh complete at $(date)"
echo "Latest data will be served by the Flask app on next request"
