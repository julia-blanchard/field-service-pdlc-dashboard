#!/usr/bin/env python3
"""
Sync Phase 0 data from Google Sheets
This script should be called by Claude Code with MCP access, not directly by cron
"""

import json
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
JSON_FILE = SCRIPT_DIR / "data" / "phase_0_programs.json"

# Column mapping (0-indexed)
COL_PORTFOLIO = 0      # A
COL_STAGE = 3          # D
COL_FEATURE = 8        # I
COL_STATUS = 16        # Q
COL_PM_LEAD = 17       # R
COL_ARCH_LEAD = 18     # S
COL_TPM_LEAD = 19      # T
COL_UX_LEAD = 20       # U
COL_CX_LEAD = 21       # V

def parse_mcp_output(mcp_output_text):
    """Parse the MCP tool output text into row arrays"""
    rows = []

    for line in mcp_output_text.strip().split('\n'):
        if not line.startswith('Row'):
            continue

        # Extract the row data from: Row  X: ['value1', 'value2', ...]
        try:
            _, data_part = line.split(': ', 1)
            row_data = eval(data_part)  # Safe here since we control the format
            rows.append(row_data)
        except:
            continue

    return rows

def parse_sheet_rows(rows):
    """Parse raw sheet rows into program data"""
    programs = []

    # Find header row
    header_idx = None
    for i, row in enumerate(rows):
        if row and len(row) > 0 and 'Portfolio' in str(row[0]):
            header_idx = i
            break

    if header_idx is None:
        print("❌ Could not find header row", file=sys.stderr)
        return []

    print(f"✓ Found header at row {header_idx + 1}", file=sys.stderr)

    # Parse data rows
    for i, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        if not row or len(row) < 9:
            continue

        portfolio = row[COL_PORTFOLIO] if len(row) > COL_PORTFOLIO else ''
        stage = row[COL_STAGE] if len(row) > COL_STAGE else ''
        feature = row[COL_FEATURE] if len(row) > COL_FEATURE else ''

        # Skip empty or engineering rows
        if not feature or not portfolio or 'Engineering Backlog' in str(stage):
            continue

        # Determine phase
        phase = '0'
        if 'PM Backlog' in str(stage) or 'Phase 0' in str(stage):
            phase = '0'
        elif any(keyword in str(stage) for keyword in ['Prototyping', 'Ready for Review', 'Approved', 'Discovery', 'Phase 1']):
            phase = '1'

        program = {
            'name': str(feature)[:80],
            'portfolio': str(portfolio),
            'stage': str(stage),
            'phase': phase,
            'status': str(row[COL_STATUS]) if len(row) > COL_STATUS else '',
            'pm_lead': str(row[COL_PM_LEAD]) if len(row) > COL_PM_LEAD else '',
            'arch_lead': str(row[COL_ARCH_LEAD]) if len(row) > COL_ARCH_LEAD else '',
            'tpm_lead': str(row[COL_TPM_LEAD]) if len(row) > COL_TPM_LEAD else '',
            'ux_lead': str(row[COL_UX_LEAD]) if len(row) > COL_UX_LEAD else '',
            'cx_lead': str(row[COL_CX_LEAD]) if len(row) > COL_CX_LEAD else '',
        }

        programs.append(program)

    return programs

def main():
    """Read MCP output from stdin and save to JSON"""
    print("🔄 Reading Google Sheet data from stdin...", file=sys.stderr)

    # Read all input
    input_text = sys.stdin.read()

    if not input_text:
        print("❌ No input received", file=sys.stderr)
        sys.exit(1)

    # Parse rows
    rows = parse_mcp_output(input_text)
    print(f"✓ Parsed {len(rows)} rows from MCP output", file=sys.stderr)

    # Parse programs
    programs = parse_sheet_rows(rows)
    print(f"✓ Extracted {len(programs)} programs", file=sys.stderr)

    # Save to JSON
    data = {
        'last_updated': datetime.now().isoformat(),
        'source': 'Google Sheets',
        'sheet_id': '1ERWXm6wVS5ItzxCqR6pX1tTf6_ec2_D-jPZeEF5V89c',
        'programs': programs
    }

    JSON_FILE.parent.mkdir(exist_ok=True)
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    # Stats
    phase_0 = sum(1 for p in programs if p['phase'] == '0')
    phase_1 = sum(1 for p in programs if p['phase'] == '1')

    print(f"✅ Saved {len(programs)} programs to {JSON_FILE}", file=sys.stderr)
    print(f"   Phase 0: {phase_0}, Phase 1: {phase_1}", file=sys.stderr)

    # Output summary as JSON to stdout
    print(json.dumps({
        'success': True,
        'total': len(programs),
        'phase_0': phase_0,
        'phase_1': phase_1,
        'file': str(JSON_FILE)
    }))

if __name__ == '__main__':
    main()
