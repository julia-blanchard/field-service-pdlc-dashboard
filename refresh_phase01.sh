#!/bin/bash
# Daily Phase 0/1 refresh
# Run this: ./refresh_phase01.sh

echo "🔄 Refreshing Phase 0/1 data from Google Sheets..."
echo "⚠️  This requires Claude Code to be running"
echo ""
echo "In Claude Code, run:"
echo "  Please refresh the Phase 0 and Phase 1 data from Google Sheets"
echo ""
echo "Current data age:"
python3 << 'PYEOF'
import json
from datetime import datetime
from zoneinfo import ZoneInfo
with open("data/phase_0_programs.json") as f:
    data = json.load(f)
last_updated = datetime.fromisoformat(data['last_updated'])
now = datetime.now(ZoneInfo("America/Los_Angeles"))
days_old = (now - last_updated).days
print(f"  Last updated: {data['last_updated']}")
print(f"  Age: {days_old} days old")
print(f"  Programs: {len(data['programs'])} total")
PYEOF
