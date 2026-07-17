#!/bin/bash
# Update Phase 0 data from Google Sheet
# Usage: ./update_phase0_from_gsheet.sh

cd "$(dirname "$0")"

echo "📊 Fetching Phase 0 data from Google Sheets..."
echo "   Spreadsheet: FS Phase 0 & Phase 1"
echo "   Tab: Phase 0 & Phase 1 Priorites"
echo ""

# Note: This requires Claude Code with Google Workspace MCP configured
# Run this command from Claude Code's terminal for MCP tool access

echo "✋ Manual step required:"
echo ""
echo "1. Ask Claude Code to read the Google Sheet with:"
echo "   read_sheet_values(spreadsheet_id='1ERWXm6wVS5ItzxCqR6pX1tTf6_ec2_D-jPZeEF5V89c', range_name=\"'Phase 0 & Phase 1 Priorites'!A1:Z1000\")"
echo ""
echo "2. Save the output to a file, then pipe it to refresh_phase0_data.py:"
echo "   cat sheet_output.txt | python3 refresh_phase0_data.py"
echo ""
echo "💡 Or just ask Claude Code: 'Update Phase 0 data from the Google Sheet'"
