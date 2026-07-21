#!/usr/bin/env python3
"""
Refresh Phase 0/1 data using MCP tool within Python
This can only run from Claude Code session with MCP access loaded
"""

import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# This would normally import the MCP client, but in Claude Code context
# we'll document the manual process instead
SCRIPT_DIR = Path(__file__).parent
JSON_FILE = SCRIPT_DIR / "data" / "phase_0_programs.json"
SHEET_ID = "1ERWXm6wVS5ItzxCqR6pX1tTf6_ec2_D-jPZeEF5V89c"
SHEET_RANGE = "Phase 0 & Phase 1 Priorites!A:Z"

# Column mappings (0-indexed)
COLUMNS = {
    'portfolio': 0,      # Column A
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

def process_sheet_data(sheet_data_rows):
    """Process raw sheet data rows into programs"""
    programs = []
    skipped = 0

    for row_num, row_data in enumerate(sheet_data_rows, start=1):
        # Skip header rows (1-3)
        if row_num < 4:
            skipped += 1
            continue

        try:
            # Get values
            portfolio = row_data[COLUMNS['portfolio']] if len(row_data) > COLUMNS['portfolio'] else ""
            stage = row_data[COLUMNS['stage']] if len(row_data) > COLUMNS['stage'] else ""
            initiative = row_data[COLUMNS['initiative']] if len(row_data) > COLUMNS['initiative'] else ""
            feature = row_data[COLUMNS['feature']] if len(row_data) > COLUMNS['feature'] else ""
            status = row_data[COLUMNS['status']] if len(row_data) > COLUMNS['status'] else ""
            pm_lead = row_data[COLUMNS['pm_lead']] if len(row_data) > COLUMNS['pm_lead'] else ""
            arch_lead = row_data[COLUMNS['arch_lead']] if len(row_data) > COLUMNS['arch_lead'] else ""
            tpm_lead = row_data[COLUMNS['tpm_lead']] if len(row_data) > COLUMNS['tpm_lead'] else ""
            ux_lead = row_data[COLUMNS['ux_lead']] if len(row_data) > COLUMNS['ux_lead'] else ""
            cx_lead = row_data[COLUMNS['cx_lead']] if len(row_data) > COLUMNS['cx_lead'] else ""

            # Use Feature if available, else Initiative
            display_name = feature if feature else initiative

            # Must have name
            if not display_name:
                skipped += 1
                continue

            # Only Phase 0 and Phase 1
            is_phase_0_or_1 = any(s in stage for s in ['PM Backlog', 'Prototyping', 'Ready for Review'])
            if not is_phase_0_or_1:
                skipped += 1
                continue

            # Normalize portfolio
            if portfolio and "Field Service" not in portfolio:
                if portfolio == "Foundations":
                    portfolio = "264 Field Service Foundations"
                elif portfolio == "Mobile":
                    portfolio = "264 Field Service Mobile"
                elif "Scheduling" in portfolio or "Optimization" in portfolio:
                    portfolio = "264 Field Service Scheduling & Optimization"
                elif portfolio:
                    portfolio = f"264 Field Service {portfolio}"

            # Determine phase
            if "PM Backlog" in stage:
                phase, subcolumn = "0", "backlog"
            elif "Prototyping" in stage:
                phase, subcolumn = "1", "prototyping"
            elif "Ready for Review" in stage:
                phase, subcolumn = "1", "ready_for_review"
            else:
                phase, subcolumn = "0", "backlog"

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
            print(f"Warning: Could not parse row {row_num}: {e}")
            skipped += 1

    print(f"   Processed {row_num} rows")
    print(f"   Skipped {skipped} rows")
    print(f"   Found {len(programs)} Phase 0/1 programs")

    return programs

def save_programs(programs):
    """Save to JSON"""
    pt_time = datetime.now(ZoneInfo("America/Los_Angeles"))
    data = {
        "last_updated": pt_time.isoformat(),
        "source": "Google Sheets",
        "sheet_id": SHEET_ID,
        "programs": programs
    }

    JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✅ Saved {len(programs)} programs to {JSON_FILE}")

    # Summary
    by_phase = {"0": 0, "1": 0}
    by_portfolio = {}

    for p in programs:
        by_phase[p.get("phase", "0")] = by_phase.get(p.get("phase", "0"), 0) + 1
        portfolio = p.get("portfolio", "TBD")
        by_portfolio[portfolio] = by_portfolio.get(portfolio, 0) + 1

    print(f"\nBy Phase:")
    print(f"   Phase 0: {by_phase['0']}")
    print(f"   Phase 1: {by_phase['1']}")

    print(f"\nBy Portfolio:")
    for portfolio in sorted(by_portfolio.keys()):
        print(f"   {portfolio}: {by_portfolio[portfolio]}")

if __name__ == "__main__":
    print("=" * 70)
    print("Phase 0 & Phase 1 Data Refresh")
    print("=" * 70)
    print(f"Sheet ID: {SHEET_ID}")
    print(f"Range: {SHEET_RANGE}")
    print()
    print("⚠️  This script requires manual MCP tool call from Claude Code")
    print("    Ask Claude: 'Please fetch Phase 0/1 data and update the JSON'")
