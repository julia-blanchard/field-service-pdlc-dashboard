#!/usr/bin/env python3
"""Add data-project-health attributes to project-container elements in GitHub Pages"""
import re

# Read the file
with open('docs/index.html', 'r') as f:
    content = f.read()

# Pattern to find project-container followed by its badge
# This will match: <div class="project-container"> ... <span class="project-badge badge-XXXX">
pattern = r'(<div class="project-container">)(.*?)(<span class="project-badge badge-([^"]+)")'

def replace_func(match):
    opening_tag = match.group(1)
    middle_content = match.group(2)
    badge_span = match.group(3)
    health_status = match.group(4)

    # Create new opening tag with data attribute
    new_opening_tag = f'<div class="project-container" data-project-health="{health_status}">'

    return new_opening_tag + middle_content + badge_span

# Replace all occurrences
content = re.sub(pattern, replace_func, content, flags=re.DOTALL)

# Write back
with open('docs/index.html', 'w') as f:
    f.write(content)

print("Added data-project-health attributes to all project-container elements")
