#!/usr/bin/env python3
"""Temporary script to add PBD URLs to test programs"""
import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "phase_0_programs.json"

# PBD URLs from the Google Sheet (column J hyperlinks)
PBD_MAPPINGS = {
    "Project Felix": {
        "pbd_url": "https://docs.google.com/document/d/1y145WkBKt47HucqKk0IaM9hvxiSAxEcjiP-ROIr3_Ls",  # From row 28
        "phase": "1"
    },
    "Frontline Workforce Management: Field Service": {
        "pbd_url": "https://docs.google.com/document/d/1Mu7lyiv7Ux4uvSt1AoRjTCxBrf1HQep8vR3W3wJqcZQ/edit",  # From row 25
        "phase": "1"
    },
    "Headless 360 - End to end steelthread of Field Service Setup": {
        "pbd_url": "https://docs.google.com/document/d/1BC575RmPfzTA57M2ylA3YITuDNiufii1o-OnkEIxwW8/edit",  # From row 18
        "phase": "1"
    }
}

with open(DATA_FILE, 'r') as f:
    data = json.load(f)

updated_count = 0
for program in data['programs']:
    name = program.get('name', '')
    for key, updates in PBD_MAPPINGS.items():
        if key in name:
            program['pbd_url'] = updates['pbd_url']
            program['phase'] = updates['phase']
            updated_count += 1
            print(f"✓ Updated: {name[:60]}... → Phase {updates['phase']} with PBD URL")
            break

with open(DATA_FILE, 'w') as f:
    json.dump(data, f, indent=2)

print(f"\n✅ Updated {updated_count} programs with PBD URLs")
