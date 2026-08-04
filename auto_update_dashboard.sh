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
# TODO: Switch to Slack when "PDLC Dashboard Bot" is approved (https://api.slack.com/apps/A0BHN9TM350)
send_notification() {
    local subject="$1"
    local message="$2"
    echo "$(date): Sending email notification: $subject"
    echo "$message" | mail -s "$subject" "$EMAIL" 2>&1 || echo "$(date): Failed to send email notification"
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

# Analyze hygiene issues (non-critical, can continue without)
echo "$(date): Analyzing hygiene issues..."
if ! /usr/bin/python3 analyze_hygiene.py; then
    echo "$(date): Hygiene analysis failed, continuing with cached data"
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
    echo "$(date): Pulling latest changes from GitHub..."
    if ! git pull github main --rebase --autostash; then
        OVERALL_SUCCESS=false
        send_notification "⚠️ PDLC Dashboard Update FAILED at $UPDATE_TIME - Git Pull Error" "Error: Could not pull latest changes from GitHub

This usually means:
- Network connectivity issue
- GitHub is down
- SSH authentication problem

Action needed:
  cd ~/field-service-execution-dashboard
  git status
  git pull github main --rebase

Logs: ~/field-service-execution-dashboard/logs/auto_update.log"
        exit 1
    fi

    echo "$(date): Pushing changes to GitHub..."
    if ! git push github main; then
        OVERALL_SUCCESS=false
        send_notification "🚨 PDLC Dashboard Update FAILED at $UPDATE_TIME - Push to GitHub Failed" "Error: Could not push changes to GitHub

This usually means:
- SSH key not configured (git@github.com authentication failed)
- Network connectivity issue
- GitHub repository permissions problem

CRITICAL: Heroku staging and production will NOT update until this is fixed!

Action needed:
  1. Test SSH connection: ssh -T git@github.com
  2. Check if SSH key is added to GitHub: https://github.com/settings/keys
  3. Manually push: cd ~/field-service-execution-dashboard && git push github main

Logs: ~/field-service-execution-dashboard/logs/auto_update.log
Last commit: $(git log -1 --oneline)"
        exit 1
    fi

    echo "$(date): Successfully pushed to GitHub"

    # Send success notification with stats
    NEXT_UPDATE=$([ "$UPDATE_TIME" == *"AM"* ] && echo "2:00 PM" || echo "9:00 AM tomorrow")

    # Check Phase 0/1 data age and add reminder if needed
    PHASE01_AGE_DAYS=$(python3 << 'PYEOF'
import json
from datetime import datetime
from zoneinfo import ZoneInfo
try:
    with open("data/phase_0_programs.json") as f:
        data = json.load(f)
    last_updated = datetime.fromisoformat(data['last_updated'])
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    print((now - last_updated).days)
except:
    print("999")
PYEOF
)

    PHASE01_REMINDER=""
    if [ "$PHASE01_AGE_DAYS" -ge 3 ]; then
        PHASE01_REMINDER="

⚠️ Phase 0/1 data is $PHASE01_AGE_DAYS days old - needs manual refresh via Claude Code
   (Waiting on Google Service Account approval for automation)"
    fi

    send_notification "✅ PDLC Dashboard Updated Successfully at $UPDATE_TIME" "Latest stats:
$STATS

✅ Pushed to GitHub - Heroku staging will auto-deploy shortly
View dashboard: https://julia-blanchard.github.io/field-service-pdlc-dashboard/
Heroku staging: https://fieldservice-adlc-staging-146cc68a9d19.rose-virginia.herokuapp.com/
$PHASE01_REMINDER
Next update: $NEXT_UPDATE"
fi

echo "$(date): Dashboard update complete"

if [ "$OVERALL_SUCCESS" = true ]; then
    exit 0
else
    exit 1
fi
