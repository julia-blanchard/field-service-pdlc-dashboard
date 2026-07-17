#!/usr/bin/env python3
"""
PDLC Phase Dashboard - Heroku App
Track programs across Phase 0, 1, 2, 3
"""

from flask import Flask, render_template, jsonify
import os
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

app = Flask(__name__, static_folder='static')

# Cache busting
@app.context_processor
def inject_cache_buster():
    return dict(cache_bust=int(time.time()))

@app.after_request
def add_header(response):
    """Add headers to prevent caching"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

def extract_latest_comment(comments_text):
    """Extract only the latest dated comment from health comments"""
    if not comments_text or comments_text == '-':
        return '-'

    import re
    # Pattern to match date prefixes like "27-May:", "05/19/2026:", "6/2:"
    date_pattern = r'(\d{1,2}[-/]\w+[-/]\d{0,4}:|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}:|\d{1,2}[-/]\d{1,2}:)'

    # Split by date patterns
    parts = re.split(date_pattern, comments_text)

    # Find the first date-prefixed entry (most recent, assuming reverse chronological)
    for i in range(len(parts)):
        if parts[i] and ':' in parts[i] and i + 1 < len(parts):
            # Return date prefix + its content
            latest = parts[i] + parts[i+1]
            return latest.strip()

    # If no date pattern found, return first 200 chars
    return comments_text[:200] + ('...' if len(comments_text) > 200 else '')

# Register as Jinja2 filter
app.jinja_env.filters['latest_comment'] = extract_latest_comment

def map_release_to_freeze_month(release_number):
    """
    Map Salesforce release numbers to their freeze months
    Based on Core App Major Release Schedule

    Release pattern:
    - 262: Freeze in April 2026
    - 264: Freeze in August 2026
    - 266: Freeze in December 2026
    - 268: Freeze in April 2027
    """
    if not release_number or not release_number.isdigit():
        return None

    release_num = int(release_number)

    base_release = 262
    base_year = 2026
    base_month = 4  # April freeze for 262

    releases_diff = (release_num - base_release) // 2

    # Each release is 4 months apart (April, August, December pattern)
    months_offset = releases_diff * 4

    freeze_date = datetime(base_year, base_month, 1) + relativedelta(months=months_offset)

    return freeze_date.strftime('%Y-%m')

def fetch_phase_0_from_file():
    """Fetch Phase 0 programs from local JSON file"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'data', 'phase_0_programs.json')
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Handle both old format (array) and new format (object with timestamp)
        if isinstance(data, list):
            programs = data
            last_updated = None
        else:
            programs = data.get('programs', [])
            last_updated = data.get('last_updated')

        print(f"Successfully loaded {len(programs)} programs from local file", flush=True)
        return programs, last_updated
    except Exception as e:
        print(f"Error loading Phase 0 data: {e}", flush=True)
        return get_fallback_phase_0(), None

def get_fallback_phase_0():
    """Fallback data if file load fails"""
    return [
        {
            "name": "Email",
            "pm": "Swati Deo",
            "arch": "Matthew Nielsen",
            "status": "Planning",
            "completion": 0,
            "next_milestone": "Prototype Review - June"
        },
        {
            "name": "Chat Blockers/VOCs",
            "pm": "Abhisek Dash",
            "arch": "TBD",
            "status": "Planning",
            "completion": 0,
            "next_milestone": "Prototype Review - July"
        }
    ]

def fetch_phase_1_from_file():
    """Fetch Phase 1 data from local JSON file (validated PBDs)"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'data', 'phase_1_programs.json')
        with open(file_path, 'r') as f:
            data = json.load(f)
        programs = data.get('programs', [])
        last_updated = data.get('last_updated')
        print(f"✅ Loaded {len(programs)} Phase 1 programs from file", flush=True)
        return programs, last_updated
    except Exception as e:
        print(f"Error loading Phase 1 data: {e}", flush=True)
        return get_fallback_phase_1(), None

def get_fallback_phase_1():
    """Fallback data if file load fails"""
    return [
        {
            "name": "Multi-modal RAG",
            "pm": "Oana Lungu Polanco",
            "arch": "Michael Macasek",
            "status": "⚠️ PASS WITH WARNINGS",
            "completion": 65
        },
        {
            "name": "Voice",
            "pm": "Abhisek Dash",
            "arch": "Sai Sudarsan Pogaru",
            "status": "✅ PASS",
            "completion": 85
        }
    ]

# Sample data - based on ADLC process
PROGRAMS_DATA = {
    "Phase 0": {
        "title": "Phase 0",
        "subtitle": "Preliminary Discovery & Planning",
        "cycle": "Continuous",
        "programs": [
            {
                "name": "AI-Powered Customer Insights",
                "pm": "Sarah Chen",
                "status": "Priority List",
                "completion": 25,
                "next_milestone": "Feature Grooming - Jun 5"
            },
            {
                "name": "Multi-Cloud Integration Hub",
                "pm": "James Park",
                "status": "Planning",
                "completion": 40,
                "next_milestone": "Priority Review - Jun 12"
            }
        ]
    },
    "Phase 1": {
        "title": "Phase 1",
        "subtitle": "Discovery & Prototype",
        "cycle": "2 weeks cycle",
        "programs": [
            {
                "name": "Service Agent Copilot",
                "pm": "Sarah Chen",
                "pod": "AI Pod",
                "status": "Alignment & Inspection",
                "completion": 90,
                "next_milestone": "Shovel Ready - May 30"
            },
            {
                "name": "Loyalty Insights Dashboard",
                "pm": "Kira Bauer",
                "pod": "AI Pod",
                "status": "Prototype Approved",
                "completion": 75,
                "next_milestone": "Eng Ownership - Jun 13"
            }
        ]
    },
    "Phase 2": {
        "title": "Phase 2",
        "subtitle": "Productization & GTM Initiation",
        "cycle": "Multiple 2 week cycles",
        "programs": [
            {
                "name": "Commerce Personalization Engine",
                "pm": "Alex Rodriguez",
                "pod": "Multiple AI Pods",
                "status": "Dev Ownership",
                "completion": 60,
                "next_milestone": "Q3 Complete - Jun 8"
            },
            {
                "name": "Industry Compliance Tracker",
                "pm": "Maria Santos",
                "pod": "Multiple AI Pods",
                "status": "Tech Readiness",
                "completion": 45,
                "next_milestone": "Final Inspection - Jun 15"
            }
        ]
    },
    "Phase 3": {
        "title": "Phase 3",
        "subtitle": "GTM Readiness & Adoption",
        "cycle": "Continuous",
        "programs": [
            {
                "name": "Case Classification AI",
                "pm": "David Kim",
                "team": "PM, PMM, UX, CX",
                "status": "GTM/Enablement",
                "completion": 80,
                "release_type": "Major Release (Tier 1)",
                "next_milestone": "Release Readiness - Jun 20"
            },
            {
                "name": "Real-Time Analytics Platform",
                "pm": "Lisa Wang",
                "team": "RM, Enablement",
                "status": "Ready to Release",
                "completion": 95,
                "release_type": "Monthly Release (Tier 2)",
                "next_milestone": "GTM Sign-off - Jun 25"
            }
        ]
    }
}

def normalize_portfolio_name(program_name, portfolio_field):
    """
    Extract normalized portfolio name - use program name as portfolio for Field Service programs
    Examples:
    - Program: "264 Field Service Mobile" -> Portfolio: "264 Field Service Mobile"
    - Program: "264 Field Service Scheduling & Optimization" -> Portfolio: "264 Field Service Scheduling & Optimization"
    - Program: "FY27 SC M4 UWM", Portfolio field: "264 UMW Worker Engagement..." -> Portfolio: "264 UMW Worker Engagement..."

    This allows Field Service programs to be organized by their program names,
    while other programs (like UWM) use their actual portfolio field.
    """
    # For Field Service programs, the program name IS the portfolio grouping
    if program_name and 'Field Service' in program_name:
        return program_name

    # For non-Field Service programs (like UWM), use the actual portfolio field from GUS
    return portfolio_field

@app.route('/')
def index():
    """Main dashboard - Field Service PDLC with Heroku layout"""
    # Load Phase 0 data from Google Sheet sync
    phase_0_programs, phase_0_updated = fetch_phase_0_from_file()

    # Load Phase 2 execution data from GUS
    exec_file = os.path.join(os.path.dirname(__file__), 'data', 'execution_data.json')
    try:
        with open(exec_file, 'r') as f:
            exec_data = json.load(f)
    except:
        exec_data = {'programs': [], 'last_updated': None}

    # Load teams data from GUS
    teams_file = os.path.join(os.path.dirname(__file__), 'data', 'teams_data.json')
    try:
        with open(teams_file, 'r') as f:
            teams_data = json.load(f)
            teams = teams_data.get('teams', [])
    except:
        teams = []

    # Transform teams data field names for template compatibility
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

    # Keep execution_programs separate (unmodified) for stats and execution tab
    execution_programs = exec_data.get('programs', [])
    # Make a copy for phase_2 that we can normalize without affecting execution_programs
    import copy
    phase_2_programs = copy.deepcopy(exec_data.get('programs', []))

    # Mark Phase 2 programs and normalize portfolio names
    for prog in phase_2_programs:
        prog['phase'] = '2'
        prog['subcolumn'] = 'inprogress'  # Default to "In Progress"
        # Normalize portfolio name from program name
        prog['portfolio'] = normalize_portfolio_name(prog.get('name', ''), prog.get('portfolio', ''))

    # Don't normalize execution_programs - they already have correct portfolio values from GUS

    # Get unique portfolios from execution programs - Field Service portfolios + UWM exception
    portfolios = sorted(set(
        p.get('portfolio', '')
        for p in execution_programs
        if p.get('portfolio') and ('Field Service' in p.get('portfolio', '') or 'UWM' in p.get('portfolio', ''))
    ))

    # Filter phase_0_programs to only include Field Service portfolios
    phase_0_programs = [
        p for p in phase_0_programs
        if p.get('portfolio') in portfolios
    ]

    # Filter phase_2_programs to only include Field Service portfolios
    phase_2_programs = [
        p for p in phase_2_programs
        if p.get('portfolio') in portfolios
    ]

    # Filter execution_programs to only include Field Service portfolios
    execution_programs = [
        p for p in execution_programs
        if p.get('portfolio') in portfolios
    ]

    # Combine all programs for Overview tab
    all_programs = phase_0_programs + phase_2_programs

    # Count programs by phase
    phase_0_count = sum(1 for p in all_programs if p.get('phase') == '0')
    phase_1_count = sum(1 for p in all_programs if p.get('phase') == '1')
    phase_2_count = sum(1 for p in all_programs if p.get('phase') == '2')
    phase_3_count = sum(1 for p in all_programs if p.get('phase') == '3')

    # Calculate execution stats for Execution tab
    total_execution_programs = len(execution_programs)
    total_projects = sum(len(prog.get('projects', [])) for prog in execution_programs)

    # Calculate program health counts
    health_counts = {'on_track': 0, 'watch': 0, 'blocked': 0, 'not_started': 0, 'completed': 0}
    for prog in execution_programs:
        health = prog.get('health', 'Unknown').lower()
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

    # Calculate project and epic stats
    project_stats = {'on_track': 0, 'watch': 0, 'blocked': 0, 'not_started': 0, 'completed': 0}
    all_epics = []
    for prog in execution_programs:
        for proj in prog.get('projects', []):
            epics = proj.get('epics', [])
            if epics:
                all_epics.extend(epics)
                # Infer project health from epic health
                epic_healths = [e.get('health', 'Unknown').lower() for e in epics]
                if any('blocked' in h for h in epic_healths):
                    project_stats['blocked'] += 1
                elif any('watch' in h for h in epic_healths):
                    project_stats['watch'] += 1
                elif any('on track' in h for h in epic_healths):
                    project_stats['on_track'] += 1
                else:
                    project_stats['not_started'] += 1

    # Calculate epic stats
    total_epics = len(all_epics)
    epic_stats = {'on_track': 0, 'watch': 0, 'blocked': 0, 'not_started': 0, 'completed': 0}
    for epic in all_epics:
        health = epic.get('health', 'Unknown').lower()
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

    # Sort execution programs by portfolio
    execution_programs_sorted = sorted(execution_programs, key=lambda p: (p.get('portfolio', '') or 'zzz', p.get('name', '')))

    # Calculate teams stats
    total_teams = len(teams)
    total_filled = sum(t['filled'] for t in teams)
    total_non_filled = sum(t['non_filled'] for t in teams)

    # Aggregate capacity by program for "By Program" view
    from collections import defaultdict
    program_capacity = defaultdict(lambda: {
        'june_delivered': 0,
        'july_committed': 0,
        'august_planned': 0,
        'september_planned': 0,
        'teams': []
    })

    for team in teams:
        team_name = team['name']

        # June delivered by program
        for program, points in team.get('june_delivered_by_program', {}).items():
            program_capacity[program]['june_delivered'] += points
            if team_name not in [t['name'] for t in program_capacity[program]['teams']]:
                program_capacity[program]['teams'].append({
                    'name': team_name,
                    'june_delivered': points,
                    'july_committed': 0,
                    'august_planned': 0,
                    'september_planned': 0
                })
            else:
                for t in program_capacity[program]['teams']:
                    if t['name'] == team_name:
                        t['june_delivered'] += points

        # July committed by program
        for program, points in team.get('july_committed_by_program', {}).items():
            program_capacity[program]['july_committed'] += points
            existing_team = next((t for t in program_capacity[program]['teams'] if t['name'] == team_name), None)
            if not existing_team:
                program_capacity[program]['teams'].append({
                    'name': team_name,
                    'june_delivered': 0,
                    'july_committed': points,
                    'august_planned': 0,
                    'september_planned': 0
                })
            else:
                existing_team['july_committed'] += points

        # August committed by program
        for program, points in team.get('august_committed_by_program', {}).items():
            program_capacity[program]['august_planned'] += points
            existing_team = next((t for t in program_capacity[program]['teams'] if t['name'] == team_name), None)
            if not existing_team:
                program_capacity[program]['teams'].append({
                    'name': team_name,
                    'june_delivered': 0,
                    'july_committed': 0,
                    'august_planned': points,
                    'september_planned': 0
                })
            else:
                existing_team['august_planned'] += points

        # September committed by program
        for program, points in team.get('september_committed_by_program', {}).items():
            program_capacity[program]['september_planned'] += points
            existing_team = next((t for t in program_capacity[program]['teams'] if t['name'] == team_name), None)
            if not existing_team:
                program_capacity[program]['teams'].append({
                    'name': team_name,
                    'june_delivered': 0,
                    'july_committed': 0,
                    'august_planned': 0,
                    'september_planned': points
                })
            else:
                existing_team['september_planned'] += points

    # Convert to list and sort by total capacity
    programs_by_capacity = [
        {
            'name': program,
            'june_delivered': data['june_delivered'],
            'july_committed': data['july_committed'],
            'august_planned': data['august_planned'],
            'september_planned': data['september_planned'],
            'teams': sorted(data['teams'], key=lambda t: t['june_delivered'] + t['july_committed'], reverse=True)
        }
        for program, data in program_capacity.items()
    ]
    programs_by_capacity = sorted(programs_by_capacity, key=lambda p: p['june_delivered'] + p['july_committed'], reverse=True)

    # Build program name → {id, portfolio} lookup for Allocations tab
    program_lookup = {}
    for prog in execution_programs:
        program_lookup[prog.get('name', '')] = {
            'id': prog.get('id', ''),
            'portfolio': prog.get('portfolio', '')
        }

    return render_template('field_service_dynamic.html',
                           static_site=False,
                           programs=all_programs,
                           portfolios=portfolios,
                           phase_0_count=phase_0_count,
                           phase_1_count=phase_1_count,
                           phase_2_count=phase_2_count,
                           phase_3_count=phase_3_count,
                           execution_programs=execution_programs_sorted,
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
                           programs_by_capacity=programs_by_capacity,
                           program_lookup=program_lookup)

@app.route('/api/programs')
def api_programs():
    """API endpoint for program data"""
    return jsonify(PROGRAMS_DATA)

@app.route('/api/programs/<phase>')
def api_programs_by_phase(phase):
    """API endpoint for programs by phase"""
    phase_key = f"Phase {phase}"
    if phase_key in PROGRAMS_DATA:
        return jsonify({phase_key: PROGRAMS_DATA[phase_key]['programs']})
    return jsonify({"error": "Phase not found"}), 404

@app.route('/execution-exact')
def execution_exact():
    """Execution tracker - exact pixel match to screenshot"""
    return execution_final()

@app.route('/execution')
def execution():
    """Execution tracker view with GUS data"""
    return execution_final()

@app.route('/execution-styled')
def execution_styled():
    """Execution tracker - styled with Poppins font matching AFCC design"""
    return execution_final()

@app.route('/execution-final')
def execution_final():
    """Execution tracker - exact match to screenshot"""
    # Load execution data
    exec_file = os.path.join(os.path.dirname(__file__), 'data', 'execution_data.json')
    try:
        with open(exec_file, 'r') as f:
            exec_data = json.load(f)
    except:
        exec_data = {'programs': [], 'last_updated': None}

    programs = exec_data.get('programs', [])
    last_updated = exec_data.get('last_updated') or teams_data.get('last_updated')

    # Calculate program stats
    total_programs = len(programs)
    health_counts = {
        'on_track': 0,
        'watch': 0,
        'blocked': 0,
        'not_started': 0
    }

    for prog in programs:
        health = prog.get('health', 'Unknown').lower()
        if 'on track' in health:
            health_counts['on_track'] += 1
        elif 'watch' in health:
            health_counts['watch'] += 1
        elif 'blocked' in health:
            health_counts['blocked'] += 1
        elif 'not started' in health:
            health_counts['not_started'] += 1

    # Calculate project stats
    total_projects = 0
    project_stats = {
        'on_track': 0,
        'watch': 0,
        'blocked': 0,
        'not_started': 0
    }

    all_epics = []
    for prog in programs:
        for proj in prog.get('projects', []):
            total_projects += 1
            epics = proj.get('epics', [])
            if epics:
                all_epics.extend(epics)
                epic_healths = [e.get('health', 'Unknown').lower() for e in epics]
                if any('blocked' in h for h in epic_healths):
                    project_stats['blocked'] += 1
                elif any('watch' in h for h in epic_healths):
                    project_stats['watch'] += 1
                elif any('not started' in h for h in epic_healths):
                    project_stats['not_started'] += 1
                elif any('on track' in h for h in epic_healths):
                    project_stats['on_track'] += 1
                else:
                    project_stats['not_started'] += 1
            else:
                project_stats['not_started'] += 1

    # Calculate epic stats
    total_epics = len(all_epics)
    epic_stats = {
        'on_track': 0,
        'watch': 0,
        'blocked': 0,
        'not_started': 0
    }

    for epic in all_epics:
        health = epic.get('health', 'Unknown').lower()
        if 'on track' in health:
            epic_stats['on_track'] += 1
        elif 'watch' in health:
            epic_stats['watch'] += 1
        elif 'blocked' in health:
            epic_stats['blocked'] += 1
        elif 'not started' in health:
            epic_stats['not_started'] += 1

    # Monthly releases grouping - three views
    from collections import defaultdict

    # Program view - based on program target release (freeze month)
    monthly_program_data = defaultdict(lambda: {'programs': set(), 'epics': 0})
    for prog in programs:
        target_release = prog.get('target_release', '')
        freeze_month = map_release_to_freeze_month(target_release)
        if freeze_month:
            monthly_program_data[freeze_month]['programs'].add(prog['name'])
            epic_count = sum(len(proj.get('epics', [])) for proj in prog.get('projects', []))
            monthly_program_data[freeze_month]['epics'] += epic_count

    # Project view - based on project completion estimates (could use epic dates)
    monthly_project_data = defaultdict(lambda: {'programs': set(), 'projects': set(), 'epics': 0})
    for prog in programs:
        for proj in prog.get('projects', []):
            epics = proj.get('epics', [])
            if epics:
                # Use latest epic end date for project
                end_dates = [e.get('end_date', '') for e in epics if e.get('end_date')]
                if end_dates:
                    latest_date = max(end_dates)
                    month = latest_date[:7]
                    monthly_project_data[month]['programs'].add(prog['name'])
                    monthly_project_data[month]['projects'].add(proj['name'])
                    monthly_project_data[month]['epics'] += len(epics)

    # Epic view - based on epic end dates
    monthly_epic_data = defaultdict(lambda: {'programs': set(), 'epics': 0})
    for prog in programs:
        for proj in prog.get('projects', []):
            for epic in proj.get('epics', []):
                end_date = epic.get('end_date', '')
                if end_date:
                    month = end_date[:7]
                    monthly_epic_data[month]['programs'].add(prog['name'])
                    monthly_epic_data[month]['epics'] += 1

    # Format for template
    def format_monthly_data(monthly_dict, include_projects=False):
        result = []
        for month, data in sorted(monthly_dict.items()):
            try:
                dt = datetime.strptime(month, '%Y-%m')
                label = dt.strftime('%b').upper()
                item = {
                    'month': month,
                    'label': label,
                    'prog_count': len(data['programs']),
                    'epic_count': data['epics']
                }
                if include_projects:
                    item['proj_count'] = len(data.get('projects', set()))
                result.append(item)
            except:
                pass
        return result

    monthly_releases_program = format_monthly_data(monthly_program_data)
    monthly_releases_project = format_monthly_data(monthly_project_data, include_projects=True)
    monthly_releases_epic = format_monthly_data(monthly_epic_data)

    # Get unique portfolios from programs
    portfolios = sorted(set(p.get('portfolio', '') for p in programs if p.get('portfolio')))

    # Sort programs alphabetically by portfolio name
    programs_sorted = sorted(programs, key=lambda p: (p.get('portfolio', '') or 'zzz', p.get('name', '')))

    return render_template('execution_final.html',
                           programs=programs_sorted,
                           total_programs=total_programs,
                           total_projects=total_projects,
                           total_epics=total_epics,
                           health_counts=health_counts,
                           project_stats=project_stats,
                           epic_stats=epic_stats,
                           monthly_releases_program=monthly_releases_program,
                           monthly_releases_project=monthly_releases_project,
                           monthly_releases_epic=monthly_releases_epic,
                           portfolios=portfolios,
                           last_updated=last_updated)

@app.route('/execution-v3')
def execution_v3():
    """Execution tracker v3 - matching exact screenshot design"""
    return execution_v2()

@app.route('/execution-v2')
def execution_v2():
    """Execution tracker v2 - matching screenshot design"""
    # Load execution data
    exec_file = os.path.join(os.path.dirname(__file__), 'data', 'execution_data.json')
    try:
        with open(exec_file, 'r') as f:
            exec_data = json.load(f)
    except:
        exec_data = {'programs': [], 'last_updated': None}

    programs = exec_data.get('programs', [])
    last_updated = exec_data.get('last_updated') or teams_data.get('last_updated')

    # Calculate program stats
    total_programs = len(programs)
    health_counts = {
        'on_track': 0,
        'watch': 0,
        'blocked': 0,
        'not_started': 0
    }

    for prog in programs:
        health = prog.get('health', 'Unknown').lower()
        if 'on track' in health:
            health_counts['on_track'] += 1
        elif 'watch' in health:
            health_counts['watch'] += 1
        elif 'blocked' in health:
            health_counts['blocked'] += 1
        elif 'not started' in health:
            health_counts['not_started'] += 1

    # Calculate project stats
    total_projects = 0
    project_stats = {
        'on_track': 0,
        'watch': 0,
        'blocked': 0,
        'not_started': 0
    }

    all_epics = []
    for prog in programs:
        for proj in prog.get('projects', []):
            total_projects += 1
            # Derive project health from epics
            epics = proj.get('epics', [])
            if epics:
                all_epics.extend(epics)
                epic_healths = [e.get('health', 'Unknown').lower() for e in epics]
                if any('blocked' in h for h in epic_healths):
                    project_stats['blocked'] += 1
                elif any('watch' in h for h in epic_healths):
                    project_stats['watch'] += 1
                elif any('not started' in h for h in epic_healths):
                    project_stats['not_started'] += 1
                elif any('on track' in h for h in epic_healths):
                    project_stats['on_track'] += 1
                else:
                    project_stats['not_started'] += 1
            else:
                project_stats['not_started'] += 1

    # Calculate epic stats
    total_epics = len(all_epics)
    epic_stats = {
        'on_track': 0,
        'watch': 0,
        'blocked': 0,
        'not_started': 0
    }

    for epic in all_epics:
        health = epic.get('health', 'Unknown').lower()
        if 'on track' in health:
            epic_stats['on_track'] += 1
        elif 'watch' in health:
            epic_stats['watch'] += 1
        elif 'blocked' in health:
            epic_stats['blocked'] += 1
        elif 'not started' in health:
            epic_stats['not_started'] += 1

    # Monthly releases grouping
    from collections import defaultdict
    monthly_data = defaultdict(lambda: {'programs': set(), 'epics': 0})

    for prog in programs:
        for proj in prog.get('projects', []):
            for epic in proj.get('epics', []):
                end_date = epic.get('end_date', '')
                if end_date:
                    try:
                        # Extract YYYY-MM from date
                        month = end_date[:7]  # "2026-06"
                        monthly_data[month]['programs'].add(prog['name'])
                        monthly_data[month]['epics'] += 1
                    except:
                        pass

    # Format monthly releases
    monthly_releases = []
    from datetime import datetime
    for month, data in sorted(monthly_data.items()):
        try:
            dt = datetime.strptime(month, '%Y-%m')
            label = dt.strftime('%b').upper()
            monthly_releases.append({
                'month': month,
                'label': label,
                'prog_count': len(data['programs']),
                'epic_count': data['epics']
            })
        except:
            pass

    # Extract unique portfolios (subclouds)
    portfolios = sorted(set(p.get('subcloud', '-') for p in programs if p.get('subcloud') and p.get('subcloud') != '-'))

    return render_template('execution_v2.html',
                           programs=programs,
                           total_programs=total_programs,
                           total_projects=total_projects,
                           total_epics=total_epics,
                           health_counts=health_counts,
                           project_stats=project_stats,
                           epic_stats=epic_stats,
                           monthly_releases=monthly_releases,
                           portfolios=portfolios,
                           last_updated=last_updated)

@app.route('/teams')
def teams():
    """Teams capacity view"""
    return render_template('teams.html')

@app.route('/milestones')
def milestones():
    """Milestones calendar view"""
    return render_template('milestones.html')

@app.route('/api/refresh', methods=['GET', 'POST'])
def refresh_all_data():
    """Refresh all dashboard data (execution + teams)"""
    try:
        import subprocess
        base_dir = os.path.dirname(__file__)
        results = []

        # Fetch execution data
        exec_script = os.path.join(base_dir, 'fetch_execution_data.py')
        exec_result = subprocess.run(['python3', exec_script], capture_output=True, text=True, timeout=120)
        results.append({
            'script': 'execution',
            'success': exec_result.returncode == 0,
            'output': exec_result.stdout if exec_result.returncode == 0 else exec_result.stderr
        })

        # Fetch teams data
        teams_script = os.path.join(base_dir, 'fetch_teams_data.py')
        teams_result = subprocess.run(['python3', teams_script], capture_output=True, text=True, timeout=120)
        results.append({
            'script': 'teams',
            'success': teams_result.returncode == 0,
            'output': teams_result.stdout if teams_result.returncode == 0 else teams_result.stderr
        })

        # Check if all succeeded
        all_success = all(r['success'] for r in results)

        if all_success:
            return jsonify({"success": True, "message": "All data refreshed successfully", "details": results})
        else:
            return jsonify({"success": False, "message": "Some refreshes failed", "details": results}), 207

    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Refresh timeout - try again later"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/refresh-execution-data', methods=['POST'])
def refresh_execution_data():
    """Refresh execution data from GUS (legacy endpoint)"""
    try:
        import subprocess
        script_path = os.path.join(os.path.dirname(__file__), 'fetch_execution_data.py')
        result = subprocess.run(['python3', script_path], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            return jsonify({"success": True, "message": "Data refreshed successfully"})
        else:
            return jsonify({"success": False, "error": result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Refresh timeout - try again later"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/validate-pbd', methods=['POST'])
def validate_pbd():
    """
    Validate a PBD document using the /validate-pbd skill
    Requires Claude Code with Google Workspace MCP

    Request body:
    {
        "program_id": "sheet_123",
        "pbd_url": "https://docs.google.com/document/d/.../edit"
    }

    Response:
    {
        "success": true,
        "validation_status": "PASS" | "PASS WITH WARNINGS" | "FAIL",
        "completion": 85,
        "report_url": "validation_reports/Program_Name.html"
    }
    """
    try:
        import subprocess
        data = request.get_json()

        if not data or 'pbd_url' not in data:
            return jsonify({"success": False, "error": "Missing pbd_url parameter"}), 400

        pbd_url = data['pbd_url']
        program_id = data.get('program_id', 'unknown')

        # Run PBD validation script (requires Claude Code + MCP)
        script_path = os.path.join(os.path.dirname(__file__), 'validate_pbd_real.py')
        result = subprocess.run(
            ['python3', script_path, pbd_url],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            # Parse validation results from stdout
            import json as json_lib
            try:
                validation_result = json_lib.loads(result.stdout)

                # Update phase_1_programs.json with new validation results
                # (Implementation would merge results into existing JSON)

                return jsonify({
                    "success": True,
                    "validation_status": validation_result.get('status', 'UNKNOWN'),
                    "completion": validation_result.get('completion', 0),
                    "report_url": validation_result.get('report_url', '')
                })
            except json_lib.JSONDecodeError:
                return jsonify({"success": False, "error": "Could not parse validation results"}), 500
        else:
            return jsonify({"success": False, "error": result.stderr}), 500

    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Validation timeout - PBD may be too large"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
