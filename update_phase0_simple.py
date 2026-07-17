#!/usr/bin/env python3
"""
Simple script to update phase_0_programs.json
Run this manually: python3 update_phase0_simple.py
"""
import json
from pathlib import Path

# For now, just touch the file to update timestamp
# The actual Google Sheet parsing would go here
data_file = Path('data/phase_0_programs.json')

if data_file.exists():
    data = json.loads(data_file.read_text())
    print(f"Current Phase 0 count: {len(data.get('programs', []))}")
    print("\nTo update Phase 0 data:")
    print("1. Ask Claude to fetch the Google Sheet data")
    print("2. Claude will parse and save it to phase_0_programs.json")
else:
    print("phase_0_programs.json not found!")
