#!/bin/bash

# Auto-update PDLC Dashboard and push to GitHub Pages
# This script runs on your local machine via cron
# Logs are saved to logs/auto_update.log
# Sends Slack DM notifications on success/failure

# Set PATH for cron environment (includes Homebrew for sf CLI)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

LOGFILE="/Users/julia.blanchard/field-service-execution-dashboard/logs/auto_update.log"
EMAIL="julia.blanchard@salesforce.com"
MAX_RETRIES=3
RETRY_DELAY=300  # 5 minutes in seconds

# Redirect all output to log file
exec >> "$LOGFILE" 2>&1

cd /Users/julia.blanchard/field-service-execution-dashboard || exit 1

# Function to send email notification
send_notification() {
    local subject="$1"
    local message="$2"
    echo "$message" | mail -s "$subject" "$EMAIL" 2>&1 || echo "Failed to send email notification"
}

# Function to retry a command
retry_command() {
    local command="$1"
    local description="$2"
    local attempt=1

    while [ $attempt -le $MAX_RETRIES ]; do
        echo "$(date): Attempt $attempt/$MAX_RETRIES - $description"

        if eval "$command"; then
            echo "$(date): $description succeeded"
            return 0
        else
            echo "$(date): $description failed (attempt $attempt/$MAX_RETRIES)"

            if [ $attempt -lt $MAX_RETRIES ]; then
                echo "$(date): Waiting $RETRY_DELAY seconds before retry..."
                sleep $RETRY_DELAY
            fi

            attempt=$((attempt + 1))
        fi
    done

    echo "$(date): $description failed after $MAX_RETRIES attempts"
    return 1
}

# Track overall success
OVERALL_SUCCESS=true
UPDATE_TIME=$(date +'%I:%M %p')
UPDATE_DATE=$(date +'%B %d, %Y')

# Fetch execution data with retry
echo "$(date): Starting execution data fetch..."
if ! retry_command "/usr/bin/python3 fetch_execution_data.py" "Fetching execution data"; then
    OVERALL_SUCCESS=false
    send_notification "PDLC Dashboard Update FAILED at $UPDATE_TIME" "Error: Could not fetch execution data from GUS after $MAX_RETRIES attempts

Action needed: Check logs at:
~/field-service-execution-dashboard/logs/auto_update.log

Possible causes:
- GUS authentication expired
- Network connectivity issue
- Mac was sleeping during scheduled run"
    exit 1
fi

# Fetch teams data with retry (non-critical, can continue with cached)
echo "$(date): Starting teams data fetch..."
if ! retry_command "/usr/bin/python3 fetch_teams_data.py" "Fetching teams data"; then
    echo "$(date): Teams fetch failed, continuing with cached data"
fi

# Note: Phase 0/1 data from Google Sheets requires manual refresh via Claude Code MCP tools
# To refresh: Ask Claude "Please fetch Phase 0 and Phase 1 data from the Google Sheet"
# The script fetch_phase0_from_sheets.py requires interactive Claude session with MCP access
echo "$(date): Using cached Phase 0/1 data (requires manual refresh via Claude Code)"

# Rebuild GitHub Pages static site
echo "$(date): Rebuilding static site..."
if ! /usr/bin/python3 sync_to_github_pages.py; then
    OVERALL_SUCCESS=false
    send_notification "PDLC Dashboard Update FAILED at $UPDATE_TIME" "Error: Could not rebuild static GitHub Pages site

Action needed: Check logs at:
~/field-service-execution-dashboard/logs/auto_update.log"
    exit 1
fi

# Extract stats from sync output for notification
STATS=$(tail -5 "$LOGFILE" | grep -E "programs|projects|epics|teams" | tail -4)

# Commit and push to GitHub
echo "$(date): Committing changes..."
git add docs/ data/

if git diff --staged --quiet; then
    echo "$(date): No changes to commit"
    send_notification "PDLC Dashboard Check at $UPDATE_TIME" "No new data changes detected. Dashboard is up to date.

View dashboard: https://julia-blanchard.github.io/field-service-pdlc-dashboard/"
else
    git commit -m "Automated dashboard update - $(date +'%Y-%m-%d %H:%M')"

    # Pull any remote changes first, then push
    if git pull github main --rebase --autostash && git push github main; then
        echo "$(date): Pushed to GitHub Pages"

        # Send success notification with stats
        NEXT_UPDATE=$([ "$UPDATE_TIME" == *"AM"* ] && echo "2:00 PM" || echo "9:00 AM tomorrow")
        send_notification "PDLC Dashboard Updated Successfully at $UPDATE_TIME" "Latest stats:
$STATS

View dashboard: https://julia-blanchard.github.io/field-service-pdlc-dashboard/

Next update: $NEXT_UPDATE"
    else
        OVERALL_SUCCESS=false
        send_notification "PDLC Dashboard Update FAILED at $UPDATE_TIME" "Error: Could not push changes to GitHub

Action needed: Check for git conflicts:
  cd ~/field-service-execution-dashboard
  git status

Logs: ~/field-service-execution-dashboard/logs/auto_update.log"
        exit 1
    fi
fi

echo "$(date): Dashboard update complete"

if [ "$OVERALL_SUCCESS" = true ]; then
    exit 0
else
    exit 1
fi
