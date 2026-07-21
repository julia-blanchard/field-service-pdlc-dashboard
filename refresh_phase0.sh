#!/bin/bash
# Refresh Phase 0/1 data from Google Sheets
# This requires an active Claude Code session with MCP access

SHEET_ID="1cie8l3W71Bkbncp5Yk3VIIiB3YHApKvRTENj1iwlpi4"
SHEET_RANGE="'FS PDLC'!A:Z"
SCRIPT_DIR="/Users/julia.blanchard/field-service-execution-dashboard"

cd "$SCRIPT_DIR" || exit 1

echo "🔄 Fetching Phase 0/1 data from Google Sheet..."
echo "   Sheet ID: $SHEET_ID"
echo "   Range: $SHEET_RANGE"
echo ""

# Fetch sheet data and pipe to sync script
# Note: This requires Claude Code to be running and accessible
/opt/homebrew/bin/claude -p "Please read the Google Sheet with ID $SHEET_ID range $SHEET_RANGE and output the raw row data" 2>/dev/null | python3 "$SCRIPT_DIR/sync_phase0_google_sheet.py"

if [ $? -eq 0 ]; then
    echo "✅ Phase 0/1 data refreshed successfully"
    exit 0
else
    echo "❌ Failed to refresh Phase 0/1 data"
    echo "   This script requires an active Claude Code session with MCP access"
    exit 1
fi
