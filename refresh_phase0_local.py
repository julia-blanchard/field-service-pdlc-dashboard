#!/usr/bin/env python3
"""
Refresh Phase 0/1 data - to be called only from Claude Code session with MCP access
This script is NOT meant to run standalone or from cron
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).parent
JSON_FILE = SCRIPT_DIR / "data" / "phase_0_programs.json"

# Column mappings from "Phase 0 & Phase 1 Priorites" sheet (0-indexed)
COLUMNS = {
    'portfolio': 0,      # Column A
    'theme': 1,          # Column B
    'tier': 2,           # Column C
    'stage': 3,          # Column D
    'initiative': 4,     # Column E
    'feature': 8,        # Column I
    'status': 16,        # Column Q
    'pm_lead': 17,       # Column R
    'arch_lead': 18,     # Column S
    'tpm_lead': 19,      # Column T
    'ux_lead': 20,       # Column U
    'cx_lead': 21        # Column V
}

def get_cell_value(row_data, column_name):
    """Safely get cell value by column name"""
    col_index = COLUMNS.get(column_name)
    if col_index is None:
        return ""
    return row_data[col_index] if len(row_data) > col_index else ""

def parse_mcp_output(mcp_output):
    """
    Parse MCP read_sheet_values output format:
    Row  1: ['col1', 'col2', ...]
    Row  2: ['col1', 'col2', ...]
    """
    programs = []
    skipped_rows = 0
    total_rows = 0

    lines = mcp_output.strip().split('\n')

    for line in lines:
        if not line.startswith('Row '):
            continue

        total_rows += 1

        try:
            # Parse "Row  N: ['val1', 'val2', ...]"
            row_part, data_part = line.split(': ', 1)
            row_num = int(row_part.replace('Row', '').strip())

            # Skip header rows (1-3)
            if row_num < 4:
                skipped_rows += 1
                continue

            # Parse the list
            row_data = eval(data_part)  # Safe since MCP output is controlled

            # Get values using column mappings
            portfolio = get_cell_value(row_data, 'portfolio')
            stage = get_cell_value(row_data, 'stage')
            initiative = get_cell_value(row_data, 'initiative')
            feature = get_cell_value(row_data, 'feature')
            status = get_cell_value(row_data, 'status')
            pm_lead = get_cell_value(row_data, 'pm_lead')
            arch_lead = get_cell_value(row_data, 'arch_lead')
            tpm_lead = get_cell_value(row_data, 'tpm_lead')
            ux_lead = get_cell_value(row_data, 'ux_lead')
            cx_lead = get_cell_value(row_data, 'cx_lead')

            # Use Feature if available, else Initiative
            display_name = feature if feature else initiative

            # Must have either Feature or Initiative
            if not display_name:
                skipped_rows += 1
                continue

            # Only include Phase 0 and Phase 1 items
            is_phase_0_or_1 = any(s in stage for s in ['PM Backlog', 'Prototyping', 'Ready for Review'])
            if not is_phase_0_or_1:
                skipped_rows += 1
                continue

            # Normalize portfolio name to match dashboard format
            if portfolio and "Field Service" not in portfolio:
                if portfolio == "Foundations":
                    portfolio = "264 Field Service Foundations"
                elif portfolio == "Mobile":
                    portfolio = "264 Field Service Mobile"
                elif "Scheduling" in portfolio or "Optimization" in portfolio:
                    portfolio = "264 Field Service Scheduling & Optimization"
                elif portfolio:
                    portfolio = f"264 Field Service {portfolio}"

            # Determine phase and subcolumn based on stage
            if "PM Backlog" in stage:
                phase = "0"
                subcolumn = "backlog"
            elif "Prototyping" in stage:
                phase = "1"
                subcolumn = "prototyping"
            elif "Ready for Review" in stage:
                phase = "1"
                subcolumn = "ready_for_review"
            else:
                phase = "0"
                subcolumn = "backlog"

            program = {
                "name": display_name,
                "full_name": display_name,
                "id": f"sheet_{row_num}",
                "phase": phase,
                "subcolumn": subcolumn,
                "portfolio": portfolio or "TBD",
                "stage": stage,
                "status": status or "",
                "program_manager": pm_lead or "",
                "arch_lead": arch_lead or "",
                "tpm_lead": tpm_lead or "",
                "ux_lead": ux_lead or "",
                "cx_lead": cx_lead or "",
                "health": "Unknown",
                "target_release": ""
            }
            programs.append(program)

        except Exception as e:
            print(f"Warning: Could not parse row {row_num}: {e}", file=sys.stderr)
            skipped_rows += 1
            continue

    print(f"   Processed {total_rows} rows")
    print(f"   Skipped {skipped_rows} rows (headers or not Phase 0/1)")
    print(f"   Found {len(programs)} Phase 0/1 programs")

    return programs

def save_programs(programs):
    """Save programs to JSON file with timestamp"""
    try:
        pt_time = datetime.now(ZoneInfo("America/Los_Angeles"))
        data = {
            "last_updated": pt_time.isoformat(),
            "source": "Google Sheets",
            "sheet_id": "1ERWXm6wVS5ItzxCqR6pX1tTf6_ec2_D-jPZeEF5V89c",
            "programs": programs
        }

        JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Saved {len(programs)} programs to {JSON_FILE}")

        # Group by phase and portfolio for summary
        by_phase = {"0": 0, "1": 0}
        by_portfolio = {}

        for p in programs:
            phase = p.get("phase", "0")
            by_phase[phase] = by_phase.get(phase, 0) + 1

            portfolio = p.get("portfolio", "TBD")
            by_portfolio[portfolio] = by_portfolio.get(portfolio, 0) + 1

        print(f"\nBy Phase:")
        print(f"   Phase 0 (PM Backlog): {by_phase.get('0', 0)}")
        print(f"   Phase 1 (Prototyping/Review): {by_phase.get('1', 0)}")

        print(f"\nBy Portfolio:")
        for portfolio in sorted(by_portfolio.keys()):
            print(f"   {portfolio}: {by_portfolio[portfolio]}")

        return True
    except Exception as e:
        print(f"❌ Error writing JSON file: {e}", file=sys.stderr)
        return False

def main():
    """Read MCP output from stdin and update phase_0_programs.json"""
    print("=" * 70)
    print("Phase 0 & Phase 1 Data Refresh (MCP mode)")
    print("=" * 70)
    print("📖 Reading MCP output from stdin...")

    mcp_output = sys.stdin.read()

    if not mcp_output.strip():
        print("❌ No input received from stdin", file=sys.stderr)
        return 1

    programs = parse_mcp_output(mcp_output)

    if programs:
        success = save_programs(programs)
        return 0 if success else 1
    else:
        print("❌ No Phase 0/1 programs found in sheet", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
