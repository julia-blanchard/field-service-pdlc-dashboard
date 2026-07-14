#!/usr/bin/env python3
"""Add scheduled build to all Phase 2 In Progress programs in GitHub Pages"""
import json
import re

# Load execution data
with open('data/execution_data.json', 'r') as f:
    execution_data = json.load(f)

# Build mapping of program name -> scheduled builds
program_builds = {}
for program in execution_data['programs']:
    builds = set()
    for project in program.get('projects', []):
        for epic in project.get('epics', []):
            build = epic.get('scheduled_build', '').strip()
            if build and build != '-':
                builds.add(build)
    if builds:
        program_builds[program['name']] = sorted(builds)

print(f"Found {len(program_builds)} programs with scheduled builds")

# Read GitHub Pages HTML
with open('docs/index.html', 'r') as f:
    html = f.read()

# Find all program cards in Phase 2 In Progress and update them
count = 0
for program_name, builds in program_builds.items():
    # Escape special regex characters in program name
    escaped_name = re.escape(program_name)

    # Pattern to match the program card structure
    # Looking for: program-card -> program-name -> div with margin-bottom (portfolio badge area)
    pattern = rf'(<div class="program-name"[^>]*>{escaped_name}</div>\s*<div style="margin-bottom: 12px;)([^"]*")'

    # Build the scheduled build HTML
    build_str = ', '.join(builds)
    build_html = f' display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">\n                                    <span style="display: inline-block; font-size: 13px; color: #475569; font-weight: 600; background: #dbeafe; padding: 4px 10px; border-radius: 6px;">'

    # Find and capture the portfolio name to insert it back
    portfolio_pattern = rf'({escaped_name}</div>\s*<div style="margin-bottom: 12px;[^>]*>\s*<span[^>]*>)([^<]+)(</span>)'
    portfolio_match = re.search(portfolio_pattern, html)

    if portfolio_match:
        portfolio_name = portfolio_match.group(2)

        # Build complete replacement
        replacement_pattern = rf'(<div class="program-name"[^>]*>{escaped_name}</div>\s*)<div style="margin-bottom: 12px;">(\s*<span[^>]*>{re.escape(portfolio_name)}</span>\s*)</div>'

        replacement = rf'\1<div style="margin-bottom: 12px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">\2<span style="display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: #64748b; font-weight: 600;">🎯 {build_str}</span>\n                                </div>'

        new_html = re.sub(replacement_pattern, replacement, html, count=1)
        if new_html != html:
            html = new_html
            count += 1
            print(f"✓ Added scheduled build to: {program_name[:50]}")

# Write back
with open('docs/index.html', 'w') as f:
    f.write(html)

print(f"\nUpdated {count} program cards with scheduled builds")
