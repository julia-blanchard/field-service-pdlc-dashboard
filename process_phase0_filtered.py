#!/usr/bin/env python3
"""Process Phase 0 Google Sheet data filtered by PM Backlog (Phase 0)"""
import json
import sys
from datetime import datetime

# Read all data from stdin
raw_data = sys.stdin.read()

programs = []

# Parse line by line
for line in raw_data.strip().split('\n'):
    if not line.startswith('Row'):
        continue
    
    # Extract row data
    parts = line.split(': ', 1)
    if len(parts) != 2:
        continue
    
    row_num_str = parts[0].replace('Row', '').strip()
    try:
        row_num = int(row_num_str)
    except:
        continue
    
    # Skip header rows
    if row_num <= 3:
        continue
    
    # Parse the list
    try:
        row_data = eval(parts[1])
    except:
        continue
    
    if not isinstance(row_data, list) or len(row_data) < 5:
        continue
    
    # Check if Stage column (index 3) contains "PM Backlog (Phase 0)"
    stage = row_data[3] if len(row_data) > 3 else ''
    if stage != 'PM Backlog (Phase 0)':
        continue
    
    portfolio = row_data[0] if len(row_data) > 0 else ''
    theme = row_data[1] if len(row_data) > 1 else ''
    tier = row_data[2] if len(row_data) > 2 else ''
    initiative = row_data[4] if len(row_data) > 4 else ''
    
    # Skip if no initiative
    if not initiative or initiative.strip() == '':
        continue
    
    programs.append({
        'portfolio': portfolio,
        'theme': theme,
        'tier': tier,
        'stage': stage,
        'initiative': initiative,
        'row_number': row_num
    })

print(f"Found {len(programs)} Phase 0 programs")
for prog in programs[:5]:
    print(f"  - {prog['initiative']} (Row {prog['row_number']})")
if len(programs) > 5:
    print(f"  ... and {len(programs) - 5} more")

# Save to file
output = {
    'last_updated': datetime.now().isoformat(),
    'programs': programs
}

with open('data/phase_0_programs.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Saved {len(programs)} programs to data/phase_0_programs.json")
