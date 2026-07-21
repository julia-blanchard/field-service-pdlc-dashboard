#!/usr/bin/env python3
"""
Process Phase 0/1 sheet data - expects full sheet data as JSON argument
Usage: python3 process_phase0_data.py '<json_data>'
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).parent
JSON_FILE = SCRIPT_DIR / "data" / "phase_0_programs.json"
SHEET_ID = "1ERWXm6wVS5ItzxCqR6pX1tTf6_ec2_D-jPZeEF5V89c"

# Column mappings
COLUMNS = {'portfolio': 0, 'stage': 3, 'initiative': 4, 'feature': 8, 'status': 16,
           'pm_lead': 17, 'arch_lead': 18, 'tpm_lead': 19, 'ux_lead': 20, 'cx_lead': 21}

def parse_mcp_result_text(result_text):
    """Parse 'Row N: [...]' format from MCP tool"""
    rows = []
    for line in result_text.strip().split('\n'):
        if line.startswith('Row '):
            try:
                _, data = line.split(': ', 1)
                rows.append(eval(data))
            except:
                pass
    return rows

def process_rows(sheet_rows):
    """Convert sheet rows to programs"""
    programs = []
    for row_num, row_data in enumerate(sheet_rows, 1):
        if row_num < 4:  # Skip headers
            continue
        
        try:
            portfolio = row_data[COLUMNS['portfolio']] if len(row_data) > COLUMNS['portfolio'] else ""
            stage = row_data[COLUMNS['stage']] if len(row_data) > COLUMNS['stage'] else ""
            initiative = row_data[COLUMNS['initiative']] if len(row_data) > COLUMNS['initiative'] else ""
            feature = row_data[COLUMNS['feature']] if len(row_data) > COLUMNS['feature'] else ""
            
            display_name = feature if feature else initiative
            if not display_name or not any(s in stage for s in ['PM Backlog', 'Prototyping', 'Ready for Review']):
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
            
            phase, subcolumn = ("0", "backlog") if "PM Backlog" in stage else \
                              ("1", "prototyping") if "Prototyping" in stage else \
                              ("1", "ready_for_review") if "Ready for Review" in stage else ("0", "backlog")
            
            programs.append({
                "name": display_name,
                "full_name": display_name,
                "id": f"sheet_{row_num}",
                "phase": phase,
                "subcolumn": subcolumn,
                "portfolio": portfolio or "TBD",
                "stage": stage,
                "status": row_data[COLUMNS['status']] if len(row_data) > COLUMNS['status'] else "",
                "program_manager": row_data[COLUMNS['pm_lead']] if len(row_data) > COLUMNS['pm_lead'] else "",
                "arch_lead": row_data[COLUMNS['arch_lead']] if len(row_data) > COLUMNS['arch_lead'] else "",
                "tpm_lead": row_data[COLUMNS['tpm_lead']] if len(row_data) > COLUMNS['tpm_lead'] else "",
                "ux_lead": row_data[COLUMNS['ux_lead']] if len(row_data) > COLUMNS['ux_lead'] else "",
                "cx_lead": row_data[COLUMNS['cx_lead']] if len(row_data) > COLUMNS['cx_lead'] else "",
                "health": "Unknown",
                "target_release": ""
            })
        except Exception as e:
            print(f"Warning: Could not parse row {row_num}: {e}", file=sys.stderr)
    
    return programs

def save_programs(programs):
    """Save to JSON file"""
    data = {
        "last_updated": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "source": "Google Sheets",
        "sheet_id": SHEET_ID,
        "programs": programs
    }
    
    JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Summary
    by_phase = {"0": sum(1 for p in programs if p.get("phase") == "0"),
                "1": sum(1 for p in programs if p.get("phase") == "1")}
    by_portfolio = {}
    for p in programs:
        port = p.get("portfolio", "TBD")
        by_portfolio[port] = by_portfolio.get(port, 0) + 1
    
    print(f"✅ Saved {len(programs)} programs to {JSON_FILE}")
    print(f"\nBy Phase: Phase 0={by_phase['0']}, Phase 1={by_phase['1']}")
    print(f"\nBy Portfolio:")
    for port in sorted(by_portfolio.keys()):
        print(f"   {port}: {by_portfolio[port]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_phase0_data.py '<mcp_json_result>'")
        sys.exit(1)
    
    mcp_result = json.loads(sys.argv[1])
    result_text = mcp_result.get("result", "")
    
    if not result_text:
        print("Error: No result text in MCP response")
        sys.exit(1)
    
    print("=" * 70)
    print("Phase 0 & Phase 1 Data Refresh")
    print("=" * 70)
    
    rows = parse_mcp_result_text(result_text)
    print(f"📊 Parsed {len(rows)} total rows from sheet")
    
    programs = process_rows(rows)
    print(f"🎯 Found {len(programs)} Phase 0/1 programs")
    
    save_programs(programs)
