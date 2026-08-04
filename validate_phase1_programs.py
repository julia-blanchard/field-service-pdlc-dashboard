#!/usr/bin/env python3
"""
Validate all Phase 1 programs with PBD URLs
Reads from phase_0_programs.json, validates each Phase 1 program, updates with validation results
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).parent
JSON_FILE = SCRIPT_DIR / "data" / "phase_0_programs.json"
VALIDATOR_SCRIPT = SCRIPT_DIR / "validate_pbd_real.py"

def validate_pbd(pbd_url):
    """
    Run PBD validator via validate_pbd_real.py
    Returns validation status, completion percentage
    """
    print(f"      Validating: {pbd_url}")

    try:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), pbd_url],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            print(f"      ❌ Validation failed: {result.stderr}")
            return None

        # Parse JSON output from validator
        output = result.stdout.strip()
        validation_data = json.loads(output)

        return {
            "status": validation_data.get("status", "FAIL"),
            "completion": validation_data.get("completion", 0),
            "report_url": validation_data.get("report_url", "")
        }

    except subprocess.TimeoutExpired:
        print(f"      ❌ Validation timeout after 120s")
        return None
    except json.JSONDecodeError:
        print(f"      ❌ Invalid JSON from validator")
        return None
    except Exception as e:
        print(f"      ❌ Validation error: {e}")
        return None

def main():
    print("🔍 Validating Phase 1 programs with PBD URLs...")

    # Read existing phase_0_programs.json
    if not JSON_FILE.exists():
        print(f"❌ Error: {JSON_FILE} not found")
        print("   Run fetch_phase0_from_sheets.py first to sync Google Sheet data")
        return 1

    with open(JSON_FILE, 'r') as f:
        data = json.load(f)

    programs = data.get("programs", [])

    # Filter to Phase 1 programs with PBD URLs
    phase1_programs = [
        p for p in programs
        if p.get("phase") == "1" and p.get("pbd_url", "").strip()
    ]

    if not phase1_programs:
        print("⚠️  No Phase 1 programs with PBD URLs found")
        print("   Add PBD URLs to column W in the Google Sheet")
        return 0

    print(f"   Found {len(phase1_programs)} Phase 1 programs with PBD URLs")

    # Validate each program
    validated_count = 0
    for program in phase1_programs:
        print(f"\n   📄 {program['name']}")

        validation = validate_pbd(program['pbd_url'])

        if validation:
            # Determine status emoji
            status = validation['status']
            if "PASS" in status and "WARNING" not in status:
                status_emoji = "✅"
            elif "WARNING" in status:
                status_emoji = "⚠️"
            else:
                status_emoji = "❌"

            # Update program with validation results
            program['validation_status'] = status
            program['completion'] = validation['completion']
            program['report_url'] = validation['report_url']
            program['status'] = f"{status_emoji} {status}"

            print(f"      {status_emoji} {status} ({validation['completion']}% complete)")
            validated_count += 1
        else:
            print(f"      ⚠️  Validation failed, skipping update")

    # Save updated data
    data['last_updated'] = datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()
    data['programs'] = programs

    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Successfully validated {validated_count}/{len(phase1_programs)} Phase 1 programs")
    print(f"   Updated: {JSON_FILE}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
