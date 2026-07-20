#!/usr/bin/env python3
"""
Sync localhost:5002 (field_service_dynamic.html) to GitHub Pages (docs/index.html)
Converts Flask template to static HTML with embedded JSON data
"""
import json
import os
import sys
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# Load data files with error handling
try:
    with open('data/execution_data.json', 'r') as f:
        exec_data = json.load(f)
except Exception as e:
    print(f"Warning: Could not load execution_data.json: {e}")
    exec_data = {'programs': [], 'last_updated': None}

try:
    with open('data/phase_0_programs.json', 'r') as f:
        phase_0_data = json.load(f)
except Exception as e:
    print(f"Warning: Could not load phase_0_programs.json: {e}")
    phase_0_data = {'programs': []}

try:
    with open('data/phase_1_programs.json', 'r') as f:
        phase_1_data = json.load(f)
except Exception as e:
    print(f"Warning: Could not load phase_1_programs.json: {e}")
    phase_1_data = {'programs': []}

try:
    with open('data/teams_data.json', 'r') as f:
        teams_data = json.load(f)
except Exception as e:
    print(f"Warning: Could not load teams_data.json: {e}")
    teams_data = {'teams': []}

# Define custom Jinja2 filter (same as app.py)
def format_month_header(month_str):
    """Convert YYYY-MM to 'Month YYYY' format"""
    if not month_str or month_str == 'no-date':
        return 'Release Month Not Assigned'

    try:
        date_obj = datetime.strptime(month_str, '%Y-%m')
        return date_obj.strftime('%B %Y')  # "June 2026"
    except:
        return month_str

# Create Jinja2 environment with custom filter
env = Environment(loader=FileSystemLoader('templates'))
env.filters['format_month'] = format_month_header
template = env.get_template('field_service_dynamic.html')

# Prepare data for template
execution_programs = exec_data.get('programs', [])
phase_0_programs = phase_0_data.get('programs', []) if isinstance(phase_0_data, dict) else phase_0_data
phase_1_programs = phase_1_data.get('programs', []) if isinstance(phase_1_data, dict) else phase_1_data
teams = teams_data.get('teams', [])

# Transform teams data field names for template compatibility (same as app.py)
for team in teams:
    # Rename capacity fields to match template expectations
    team['june_delivered'] = team.get('capacity_delivered_june', 0)
    team['july_committed'] = team.get('capacity_committed_july', 0)
    team['august_committed'] = team.get('capacity_committed_august', 0)
    team['september_committed'] = team.get('capacity_committed_september', 0)

    # Calculate capacity limits (assume 24 PD per person per month as default)
    team['june_capacity_limit'] = team.get('total', 0) * 24
    team['july_capacity_limit'] = team.get('total', 0) * 24
    team['august_capacity_limit'] = team.get('total', 0) * 24
    team['september_capacity_limit'] = team.get('total', 0) * 24

# Build programs list combining all phases
all_programs = []

# Add Phase 0 and Phase 1 from phase_0_programs.json (which includes both)
# Respect the phase field already set in the JSON
for prog in phase_0_programs:
    # Only set phase if not already present
    if 'phase' not in prog:
        prog['phase'] = '0'
    all_programs.append(prog)

# Add old Phase 1 programs from phase_1_programs.json (if any)
# Skip these for now since we're using Google Sheet data
# for prog in phase_1_programs:
#     prog['phase'] = '1'
#     all_programs.append(prog)

# Add Phase 2 (execution programs)
for prog in execution_programs:
    prog['phase'] = '2'
    prog['subcolumn'] = 'inprogress'
    all_programs.append(prog)

# Get portfolios
portfolios = sorted(set(
    p.get('portfolio', '')
    for p in execution_programs
    if p.get('portfolio') and ('Field Service' in p.get('portfolio', '') or 'UWM' in p.get('portfolio', ''))
))

# Calculate stats
total_execution_programs = len(execution_programs)
total_projects = sum(len(p.get('projects', [])) for p in execution_programs)

# Health counts
health_counts = {
    'not_assigned': 0,
    'on_track': 0,
    'watch': 0,
    'blocked': 0,
    'not_started': 0,
    'completed': 0
}

for prog in execution_programs:
    health = prog.get('health', '').lower()
    if 'on track' in health:
        health_counts['on_track'] += 1
    elif 'watch' in health:
        health_counts['watch'] += 1
    elif 'blocked' in health:
        health_counts['blocked'] += 1
    elif 'not started' in health:
        health_counts['not_started'] += 1
    elif 'completed' in health or 'complete' in health:
        health_counts['completed'] += 1
    else:
        health_counts['not_assigned'] += 1

# Project stats
project_stats = {'not_assigned': 0, 'on_track': 0, 'watch': 0, 'blocked': 0, 'not_started': 0, 'completed': 0}
epic_stats = {'not_assigned': 0, 'on_track': 0, 'watch': 0, 'blocked': 0, 'not_started': 0, 'completed': 0}

total_project_epics = 0
for prog in execution_programs:
    for proj in prog.get('projects', []):
        health = proj.get('health_status', '').lower()
        if 'on track' in health:
            project_stats['on_track'] += 1
        elif 'watch' in health:
            project_stats['watch'] += 1
        elif 'blocked' in health:
            project_stats['blocked'] += 1
        elif 'not started' in health:
            project_stats['not_started'] += 1
        elif 'completed' in health or 'complete' in health:
            project_stats['completed'] += 1
        else:
            project_stats['not_assigned'] += 1

        for epic in proj.get('epics', []):
            total_project_epics += 1
            health = epic.get('health_status', epic.get('health', '')).lower()
            if 'on track' in health:
                epic_stats['on_track'] += 1
            elif 'watch' in health:
                epic_stats['watch'] += 1
            elif 'blocked' in health:
                epic_stats['blocked'] += 1
            elif 'not started' in health:
                epic_stats['not_started'] += 1
            elif 'completed' in health or 'complete' in health:
                epic_stats['completed'] += 1
            else:
                epic_stats['not_assigned'] += 1

# Total epics = sum of all health statuses including not assigned
total_epics = sum(epic_stats.values())

# Team stats
total_teams = len(teams)
total_filled = sum(t.get('filled', 0) for t in teams)
total_non_filled = sum(t.get('non_filled', 0) for t in teams)

# Build program name → {id, portfolio} lookup for Allocations tab
program_lookup = {}
for prog in execution_programs:
    program_lookup[prog.get('name', '')] = {
        'id': prog.get('id', ''),
        'portfolio': prog.get('portfolio', '')
    }

# Calculate actual phase counts from all_programs
actual_phase_0_count = sum(1 for p in all_programs if p.get('phase') == '0')
actual_phase_1_count = sum(1 for p in all_programs if p.get('phase') == '1')
actual_phase_2_count = sum(1 for p in all_programs if p.get('phase') == '2')

# Render template
html = template.render(
    static_site=True,
    programs=all_programs,
    portfolios=portfolios,
    phase_0_count=actual_phase_0_count,
    phase_1_count=actual_phase_1_count,
    phase_2_count=actual_phase_2_count,
    phase_3_count=0,
    execution_programs=execution_programs,
    total_execution_programs=total_execution_programs,
    total_projects=total_projects,
    total_epics=total_epics,
    health_counts=health_counts,
    project_stats=project_stats,
    epic_stats=epic_stats,
    teams=teams,
    total_teams=total_teams,
    total_filled=total_filled,
    total_non_filled=total_non_filled,
    programs_by_capacity=[],
    program_lookup=program_lookup,
    last_updated=exec_data.get('last_updated')
)

# Write to docs/index.html
try:
    # Ensure docs directory exists
    os.makedirs('docs', exist_ok=True)

    with open('docs/index.html', 'w') as f:
        f.write(html)

    print("✅ Successfully synced field_service_dynamic.html to docs/index.html")
    print(f"   - {len(all_programs)} total programs")
    print(f"   - {total_execution_programs} execution programs")
    print(f"   - {total_projects} projects")
    print(f"   - {total_epics} epics")
    print(f"   - {total_teams} teams")
    sys.exit(0)
except Exception as e:
    print(f"❌ Error writing to docs/index.html: {e}")
    sys.exit(1)
