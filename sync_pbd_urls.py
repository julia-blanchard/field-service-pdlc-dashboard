#!/usr/bin/env python3
"""Sync PBD URLs from Google Sheet column J to phase_0_programs.json"""
import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "phase_0_programs.json"

# PBD URLs from Google Sheet column J "Related PBD Link" (rows with data)
# Format: pbd_url -> [(prototype_name_partial, parent_program_name), ...]
PBD_MAPPINGS = {
    "https://docs.google.com/document/d/1Mu7lyiv7Ux4uvSt1AoRjTCxBrf1HQep8vR3W3wJqcZQ/edit": [
        ("Phase 2 of WFM - native experience", "Frontline Workforce Management"),
    ],
    "https://docs.google.com/document/d/1aNThhwwRJAkvlyQ6pf7-cIFzu9etuVG61eu2w-qJPbk/edit": [
        ("Upload Queue: Validation Errors", "Perf Priming & Upload Queue Improvements"),
    ],
    "https://docs.google.com/document/d/1BC575RmPfzTA57M2ylA3YITuDNiufii1o-OnkEIxwW8/edit": [
        ("Headless 360 - End to end steelthread", "Field Service Headless Setup"),
    ],
    "https://docs.google.com/document/d/1y145WkBKt47HucqKk0IaM9hvxiSAxEcjiP-ROIr3_Ls": [
        ("Project Felix", "Agentforce Adoption: Mobile"),
    ],
}

with open(DATA_FILE, 'r') as f:
    data = json.load(f)

updated_count = 0
for pbd_url, prototype_info in PBD_MAPPINGS.items():
    for keyword, parent_program in prototype_info:
        for program in data['programs']:
            name = program.get('name', '')
            if keyword in name:
                # Update PBD URL and parent program
                program['pbd_url'] = pbd_url
                program['parent_program'] = parent_program
                # Set phase to 1 for programs with PBDs
                if program.get('phase') == '0':
                    program['phase'] = '1'
                # Set subcolumn to prototyping so they render
                if program.get('subcolumn') == 'backlog':
                    program['subcolumn'] = 'prototyping'
                updated_count += 1
                print(f"✓ Updated: {name[:60]}...")
                print(f"  → PBD: {pbd_url[:80]}...")
                print(f"  → Program: {parent_program}")
                break

with open(DATA_FILE, 'w') as f:
    json.dump(data, f, indent=2)

print(f"\n✅ Updated {updated_count} programs with PBD URLs and parent programs")
