#!/usr/bin/env python3
"""
Complete Phase 0/1 data refresh from Google Sheets
Processes all 180 rows, applies tier normalization, and saves to phase_0_programs.json
"""

import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).parent
JSON_FILE = SCRIPT_DIR / "data" / "phase_0_programs.json"

# Column mappings (0-indexed)
COLUMNS = {
    'portfolio': 0,      # Column A
    'theme': 1,          # Column B
    'tier': 2,           # Column C
    'stage': 3,          # Column D
    'owner': 4,          # Column E
    'initiative': 5,     # Column F
    'feature': 6,        # Column G
    'former_brief': 7,   # Column H
    'one_pager': 8,      # Column I
    'related_pbd': 9,    # Column J
    'prd': 10,           # Column K
    'tshirt_size': 11,   # Column L
    'what_answering': 12,# Column M
    'gtm_month': 13,     # Column N
    'july': 14,          # Column O
    'august': 15,        # Column P
    'september': 16,     # Column Q
    'october': 17,       # Column R
    'status': 18,        # Column S
    'pm_lead': 19,       # Column T
    'arch_lead': 20,     # Column U
    'tpm_lead': 21,      # Column V
    'ux_lead': 22,       # Column W
    'cx_lead': 23        # Column X
}

def get_cell_value(row_data, column_name):
    """Safely get cell value by column name"""
    col_index = COLUMNS.get(column_name)
    if col_index is None:
        return ""
    return row_data[col_index] if len(row_data) > col_index else ""

def normalize_tier(tier_value):
    """
    Normalize tier values to T1, T2, T3, or 'Tier N/A'
    """
    if not tier_value or not tier_value.strip():
        return "Tier N/A"

    tier_clean = tier_value.strip()

    # Extract number from tier strings like "Tier 1", "T1", "1", etc.
    if "1" in tier_clean:
        return "T1"
    elif "2" in tier_clean:
        return "T2"
    elif "3" in tier_clean:
        return "T3"
    else:
        return "Tier N/A"

def parse_sheet_data(all_rows):
    """
    Parse raw Google Sheets rows into structured program data
    """
    programs = []
    skipped_rows = 0
    total_rows = len(all_rows)

    for idx, row_data in enumerate(all_rows, start=4):  # Start at row 4 (after headers)
        try:
            # Get values using column mappings
            portfolio = get_cell_value(row_data, 'portfolio')
            theme = get_cell_value(row_data, 'theme')
            tier = get_cell_value(row_data, 'tier')
            stage = get_cell_value(row_data, 'stage')
            owner = get_cell_value(row_data, 'owner')
            initiative = get_cell_value(row_data, 'initiative')
            feature = get_cell_value(row_data, 'feature')
            status = get_cell_value(row_data, 'status')
            pm_lead = get_cell_value(row_data, 'pm_lead')
            arch_lead = get_cell_value(row_data, 'arch_lead')
            tpm_lead = get_cell_value(row_data, 'tpm_lead')
            ux_lead = get_cell_value(row_data, 'ux_lead')
            cx_lead = get_cell_value(row_data, 'cx_lead')
            related_pbd = get_cell_value(row_data, 'related_pbd')

            # Determine display name and feature link
            # If Feature is a URL, use Initiative as name and Feature as a link
            feature_link = None
            if feature and (feature.startswith('http://') or feature.startswith('https://')):
                display_name = initiative
                feature_link = feature
            else:
                display_name = feature if feature else initiative

            # Only include Phase 0 and Phase 1 items
            if not display_name:
                skipped_rows += 1
                continue

            # Truncate very long names to 100 characters
            if len(display_name) > 100:
                display_name = display_name[:97] + "..."

            # Check if row is in Phase 0 or Phase 1
            is_phase_0_or_1 = any(s in stage for s in ['PM Backlog', 'Prototyping', 'Ready for Review', 'Engineering Backlog'])
            if not is_phase_0_or_1:
                skipped_rows += 1
                continue

            # Normalize portfolio name to FY27 format
            if portfolio and "Field Service" not in portfolio:
                if portfolio == "Foundations":
                    portfolio = "FY27 Field Service Foundations"
                elif portfolio == "Mobile":
                    portfolio = "FY27 Field Service Mobile"
                elif portfolio == "Workforce Scheduling":
                    portfolio = "FY27 Field Service Workforce Scheduling"
                elif "Scheduling" in portfolio or portfolio == "S&O":
                    portfolio = "FY27 Field Service Scheduling & Optimization"
                elif portfolio:
                    portfolio = f"FY27 Field Service {portfolio}"

            # Determine phase and subcolumn based on stage
            if "PM Backlog" in stage or "Engineering Backlog" in stage:
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

            # Use PM Lead if populated, otherwise fall back to Owner
            effective_pm = pm_lead or owner or ""

            # Normalize tier to T1/T2/T3 or "Tier N/A"
            normalized_tier = normalize_tier(tier)

            # Create Google Sheets link to specific row
            # gid=1674131463 is the correct sheet tab ID for "Phase 0 & Phase 1 Priorites"
            sheet_url = f"https://docs.google.com/spreadsheets/d/1ERWXm6wVS5ItzxCqR6pX1tTf6_ec2_D-jPZeEF5V89c/edit#gid=1674131463&range={idx}:{idx}"

            program = {
                "name": display_name,
                "full_name": display_name,
                "id": f"sheet_{idx}",
                "phase": phase,
                "subcolumn": subcolumn,
                "portfolio": portfolio or "TBD",
                "theme": theme or "",
                "tier": normalized_tier,
                "stage": stage,
                "status": status or "",
                "program_manager": effective_pm,
                "arch_lead": arch_lead or "",
                "tpm_lead": tpm_lead or "",
                "ux_lead": ux_lead or "",
                "cx_lead": cx_lead or "",
                "related_pbd": related_pbd or "",
                "health": "Unknown",
                "target_release": "",
                "sheet_url": sheet_url,
                "feature_link": feature_link
            }
            programs.append(program)

        except Exception as e:
            print(f"Warning: Could not parse row {idx}: {e}")
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
        by_tier = {}

        for p in programs:
            phase = p.get("phase", "0")
            by_phase[phase] = by_phase.get(phase, 0) + 1

            portfolio = p.get("portfolio", "TBD")
            by_portfolio[portfolio] = by_portfolio.get(portfolio, 0) + 1

            tier = p.get("tier", "Tier N/A")
            by_tier[tier] = by_tier.get(tier, 0) + 1

        print(f"\nBy Phase:")
        print(f"   Phase 0 (PM Backlog): {by_phase.get('0', 0)}")
        print(f"   Phase 1 (Prototyping/Review): {by_phase.get('1', 0)}")

        print(f"\nBy Portfolio:")
        for portfolio in sorted(by_portfolio.keys()):
            print(f"   {portfolio}: {by_portfolio[portfolio]}")

        print(f"\nBy Tier:")
        for tier in sorted(by_tier.keys()):
            print(f"   {tier}: {by_tier[tier]}")

        return True
    except Exception as e:
        print(f"❌ Error writing JSON file: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("Phase 0 & Phase 1 Data Refresh - Tier Normalization")
    print("=" * 70)
    print()
    print("This script processes the raw sheet data with tier normalization.")
    print("It expects /tmp/all_phase0_rows.json to exist from the MCP agent.")
    print()

    # Load raw rows from agent output
    raw_rows_file = Path("/tmp/all_phase0_rows.json")
    if not raw_rows_file.exists():
        print(f"❌ ERROR: {raw_rows_file} not found")
        print("   Run the MCP agent first to fetch all 177 rows.")
        exit(1)

    with open(raw_rows_file) as f:
        all_rows = json.load(f)

    programs = parse_sheet_data(all_rows)

    if programs:
        save_programs(programs)
    else:
        print("❌ No Phase 0/1 programs found in sheet")
