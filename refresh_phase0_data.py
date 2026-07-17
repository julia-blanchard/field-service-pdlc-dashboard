#!/usr/bin/env python3
"""
Refresh Phase 0 data from Field Service Google Sheet
Parses the sheet data and updates phase_0_programs.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).parent
JSON_FILE = SCRIPT_DIR / "data" / "phase_0_programs.json"

def parse_sheet_data(sheet_data_text):
    """
    Parse Google Sheets data from MCP read_sheet_values output

    Expected format from mcp__plugin_google-workspace_vmcp-google-workspace__read_sheet_values:
    "Row 1: ['col1', 'col2', ...]"
    """
    programs = []

    lines = sheet_data_text.strip().split('\n')

    for line in lines:
        if not line.startswith('Row '):
            continue

        # Parse "Row N: ['val1', 'val2', ...]"
        try:
            row_num_part, data_part = line.split(': ', 1)
            row_num = int(row_num_part.replace('Row', '').strip())

            # Skip header rows (1-3)
            if row_num < 4:
                continue

            # Parse the list
            row_data = eval(data_part)  # Safe here since we control the input

            if len(row_data) < 9:  # Need at least feature column (I = index 8)
                continue

            portfolio = row_data[0] if len(row_data) > 0 else ""
            stage = row_data[3] if len(row_data) > 3 else ""
            initiative = row_data[4] if len(row_data) > 4 else ""
            feature = row_data[8] if len(row_data) > 8 else ""
            status = row_data[16] if len(row_data) > 16 else ""
            pm_lead = row_data[17] if len(row_data) > 17 else ""
            arch_lead = row_data[18] if len(row_data) > 18 else ""
            tpm_lead = row_data[19] if len(row_data) > 19 else ""
            ux_lead = row_data[20] if len(row_data) > 20 else ""
            cx_lead = row_data[21] if len(row_data) > 21 else ""

            # Use Initiative as fallback if Feature is empty
            display_name = feature if feature else initiative

            # Only include Phase 0 and Phase 1 items (PM Backlog, Prototyping, Ready for Review)
            # Must have either a Feature or Initiative
            if not display_name or ("PM Backlog" not in stage and "Prototyping" not in stage and "Ready for Review" not in stage):
                continue

            # Normalize portfolio name to match dashboard format
            if portfolio and "Field Service" not in portfolio:
                if portfolio == "Foundations":
                    portfolio = "264 Field Service Foundations"
                elif portfolio == "Mobile":
                    portfolio = "264 Field Service Mobile"
                elif portfolio == "Workforce Scheduling":
                    portfolio = "264 Field Service Workforce Scheduling"
                elif "Scheduling" in portfolio:
                    portfolio = "264 Field Service Scheduling & Optimization"
                elif portfolio:
                    portfolio = f"264 Field Service {portfolio}"

            # Determine phase and subcolumn based on stage
            # PM Backlog (Phase 0) → Phase 0 Backlog
            # Prototyping → Phase 1 Column 1
            # Ready for Review → Phase 1 Column 2
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
            print(f"Warning: Could not parse line: {line[:50]}... Error: {e}")
            continue

    return programs

def save_programs(programs):
    """Save programs to JSON file with timestamp"""
    try:
        pt_time = datetime.now(ZoneInfo("America/Los_Angeles"))
        data = {
            "last_updated": pt_time.isoformat(),
            "programs": programs
        }

        JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Saved {len(programs)} Phase 0 programs to {JSON_FILE}")

        # Group by portfolio for summary
        by_portfolio = {}
        for p in programs:
            portfolio = p.get("portfolio", "TBD")
            by_portfolio[portfolio] = by_portfolio.get(portfolio, 0) + 1

        print("\nPrograms by portfolio:")
        for portfolio in sorted(by_portfolio.keys()):
            print(f"   {portfolio}: {by_portfolio[portfolio]}")

        return True
    except Exception as e:
        print(f"❌ Error writing JSON file: {e}")
        return False

def main():
    """Main function - expects Google Sheets data from stdin"""
    print("🔄 Processing Phase 0 data from Google Sheet...")

    # Read sheet data from stdin (piped from MCP tool)
    sheet_data = sys.stdin.read()

    if not sheet_data:
        print("❌ No data received from stdin")
        print("Usage: cat sheet_data.txt | python3 refresh_phase0_data.py")
        return 1

    programs = parse_sheet_data(sheet_data)

    if programs:
        success = save_programs(programs)
        return 0 if success else 1
    else:
        print("❌ No Phase 0 programs found in sheet")
        return 1

if __name__ == "__main__":
    sys.exit(main())
