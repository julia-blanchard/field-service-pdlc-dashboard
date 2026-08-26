#!/usr/bin/env python3
"""
Fetch Field Service Execution Status data from GUS Report
Report ID: 00OEE000002tswH2AQ (264 Field Service Program Epic Admin)
Shows: Programs -> Projects -> Epics with health information
"""

import json
import re
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data" / "execution_data.json"
REPORT_ID = "00OEE000002tswH2AQ"  # Field Service report
TARGET_ORG = os.getenv("TARGET_ORG", "org62")  # Use env var or default to org62

# The GUS report above has a hardcoded portfolio scope, so it silently misses
# new portfolios (e.g. FY27/266 pillars) until someone edits the report's
# filter by hand. discover_forward_facing_portfolios() below fills that gap
# via SOQL instead -- no hardcoded portfolio names, so the next release's
# portfolios get picked up automatically as long as their name carries a
# release number.
FORWARD_RELEASE_CUTOFF = 264  # keep 264 and newer; drop 262 and earlier
JUNK_PORTFOLIO_NAME_RE = re.compile(r'dummy|holder|test|do not use|innovation|backlog', re.IGNORECASE)
RELEASE_NUMBER_RE = re.compile(r'\b(2[4-9]\d)\b')
FY27_NAME_RE = re.compile(r'FY27', re.IGNORECASE)
# Portfolios that match the Field Service name search but whose Parent_Cloud__c
# is confirmed to be something else (e.g. Government Cloud Field Service ->
# Parent_Cloud__c = GIA, not Field Service).
EXCLUDED_PARENT_CLOUD_PORTFOLIOS = {'Government Cloud Field Service'}

def fetch_execution_report():
    """Fetch execution report from GUS with extended metadata"""
    try:
        print(f"Fetching GUS report {REPORT_ID}...")
        result = subprocess.run(
            ['sf', 'api', 'request', 'rest', '--target-org', TARGET_ORG,
             f'/services/data/v64.0/analytics/reports/{REPORT_ID}?includeDetails=true',
             '--method', 'GET'],
            capture_output=True,
            text=True,
            check=True
        )

        report_data = json.loads(result.stdout)
        return report_data
    except Exception as e:
        print(f"Error fetching report: {e}")
        return None

def parse_health_from_status(status_str):
    """Extract health status from text"""
    if not status_str or status_str == '-':
        return 'Unknown'

    status_lower = status_str.lower()
    if 'on track' in status_lower:
        return 'On Track'
    if 'watch' in status_lower or 'at risk' in status_lower:
        return 'Watch'
    if 'blocked' in status_lower or 'off track' in status_lower:
        return 'Blocked'
    if 'not started' in status_lower:
        return 'Not Started'
    if 'completed' in status_lower or 'complete' in status_lower:
        return 'Completed'

    return 'Unknown'

def parse_report_data(report_data):
    """Parse GUS report into structured data with correct grouping hierarchy"""
    if not report_data:
        return {
            'last_updated': datetime.now().isoformat(),
            'programs': []
        }

    # The report structure is:
    # groupingsDown -> Portfolio -> Program -> Project -> factMap rows (epics)

    # Column mapping (from reportExtendedMetadata.detailColumnInfo):
    # Col 0: Epic Name
    # Col 1: LOC
    # Col 2: Priority
    # Col 3: Epic Health Comments
    # Col 4: Health
    # Col 5: Path to Green
    # Col 6: Team: Team Name
    # Col 7: Pillar
    # Col 8: Actual Story Points on Epic
    # Col 9: #Storypoints Closed
    # Col 10: Scheduled Build: Name (Target)
    # Col 11: Owner: Full Name (Epic Owner / Dev Lead)
    # Col 12: Product Owner: Full Name (Project-level)
    # Col 13: Last Modified Date
    # Col 14: Program Health
    # Col 15: Planned Release

    groupings_down = report_data.get('groupingsDown', {}).get('groupings', [])
    programs_map = {}

    # Level 1: Portfolio groupings
    for portfolio_group in groupings_down:
        portfolio_name = portfolio_group.get('label', 'Unknown')

        # Level 2: Program groupings
        for program_group in portfolio_group.get('groupings', []):
            program_name = program_group.get('label', 'Unknown')
            program_id = program_group.get('value', '')

            # Initialize program if not exists
            if program_id not in programs_map:
                programs_map[program_id] = {
                    'name': program_name,
                    'id': program_id,
                    'portfolio': portfolio_name,
                    'health': 'Unknown',
                    'health_status': 'Unknown',
                    'program_manager': '',
                    'target_release': '',
                    'projects': {}
                }

            # Level 3: Project groupings
            for project_group in program_group.get('groupings', []):
                project_name = project_group.get('label', 'Unknown')
                project_id = project_group.get('value', '')

                # Get fact map key for this project's epics
                fact_key = project_group.get('key', '') + '!T'
                fact_data = report_data.get('factMap', {}).get(fact_key, {})
                rows = fact_data.get('rows', [])

                # Initialize project if not exists
                if project_id not in programs_map[program_id]['projects']:
                    programs_map[program_id]['projects'][project_id] = {
                        'name': project_name,
                        'id': project_id,
                        'product_owner': '',
                        'dev_lead': '',
                        'target': '',
                        'last_modified': '',
                        'health_status': 'Unknown',
                        'epics': []
                    }

                project_ref = programs_map[program_id]['projects'][project_id]

                # Process epic rows
                for row in rows:
                    cells = row.get('dataCells', [])

                    if len(cells) < 4:
                        continue

                    epic_name = cells[0].get('label', '')
                    loc = cells[1].get('label', '') if len(cells) > 1 else ''
                    priority = cells[2].get('label', '') if len(cells) > 2 else ''
                    epic_health_comments = cells[3].get('label', '') if len(cells) > 3 else ''
                    health_status = cells[4].get('label', '') if len(cells) > 4 else ''
                    path_to_green = cells[5].get('label', '') if len(cells) > 5 else ''
                    team_name = cells[6].get('label', '') if len(cells) > 6 else ''
                    pillar = cells[7].get('label', '') if len(cells) > 7 else ''
                    actual_points = cells[8].get('label', '') if len(cells) > 8 else ''
                    closed_points = cells[9].get('label', '') if len(cells) > 9 else ''
                    scheduled_build = cells[10].get('label', '') if len(cells) > 10 else ''
                    owner_name = cells[11].get('label', '') if len(cells) > 11 else ''
                    product_owner = cells[12].get('label', '') if len(cells) > 12 else ''
                    last_modified = cells[13].get('value', '') if len(cells) > 13 else ''
                    program_health = cells[14].get('label', '') if len(cells) > 14 else ''
                    planned_release = cells[15].get('label', '') if len(cells) > 15 else ''

                    # Update project-level fields (from first epic)
                    if not project_ref['product_owner'] and product_owner and product_owner != '-':
                        project_ref['product_owner'] = product_owner

                    if not project_ref['dev_lead'] and owner_name and owner_name != '-':
                        project_ref['dev_lead'] = owner_name

                    # Note: target will be computed as MAX of epic scheduled builds after all epics are collected

                    if not project_ref['last_modified'] and last_modified:
                        project_ref['last_modified'] = last_modified

                    # Update program-level health from epic data
                    if program_health and program_health != '-':
                        parsed_health = parse_health_from_status(program_health)
                        if parsed_health != 'Unknown':
                            programs_map[program_id]['health'] = parsed_health
                            programs_map[program_id]['health_status'] = program_health

                    # Add epic
                    if epic_name and epic_name != '-':
                        epic_health = parse_health_from_status(health_status)

                        project_ref['epics'].append({
                            'name': epic_name,
                            'id': '',  # Not available in report
                            'priority': priority,
                            'health': epic_health,
                            'health_status': health_status,
                            'health_comments': epic_health_comments,
                            'owner': owner_name,
                            'team': team_name,
                            'scheduled_build': scheduled_build,
                            'planned_release': planned_release,
                            'last_modified': last_modified,
                            'loc': loc,
                            'path_to_green': path_to_green
                        })

    # Convert to list format
    programs = []
    for program_id, program_data in programs_map.items():
        program = {
            'name': program_data['name'],
            'id': program_data['id'],
            'portfolio': program_data['portfolio'],
            'health': program_data['health'],
            'health_status': program_data['health_status'],
            'program_manager': program_data['program_manager'],
            'target_release': program_data['target_release'],
            'projects': []
        }

        # Convert projects
        for project_id, project_data in program_data['projects'].items():
            # Calculate project health from epics
            epic_healths = [e['health'] for e in project_data['epics']]
            if 'Blocked' in epic_healths or 'Off Track' in epic_healths:
                project_health = 'Blocked'
            elif 'Watch' in epic_healths or 'At Risk' in epic_healths:
                project_health = 'Watch'
            elif 'On Track' in epic_healths:
                project_health = 'On Track'
            elif 'Completed' in epic_healths:
                project_health = 'Completed'
            else:
                project_health = 'Not Started'

            project_data['health_status'] = project_health

            # Calculate project target as MAX of epic scheduled builds
            epic_builds = [e['scheduled_build'] for e in project_data['epics']
                          if e.get('scheduled_build') and e['scheduled_build'] != '-']
            if epic_builds:
                # Get the maximum build number (handles both numeric like '264' and strings)
                try:
                    # Try numeric comparison first
                    max_build = str(max([int(b) for b in epic_builds if b.isdigit()]))
                except (ValueError, TypeError):
                    # Fall back to string comparison
                    max_build = max(epic_builds)
                project_data['target'] = max_build
            # If no epic builds, target remains whatever was set (possibly empty)

            # Only add projects that have epics
            if len(project_data['epics']) > 0:
                program['projects'].append(project_data)

        programs.append(program)

    # Filter out programs with no projects after empty project removal
    programs = [p for p in programs if len(p['projects']) > 0]

    return {
        'last_updated': datetime.now().isoformat(),
        'programs': programs
    }

def enrich_with_epic_ids(structured_data):
    """Query GUS to get epic IDs and planned releases by name"""
    print("🔍 Enriching epic data with IDs and planned releases from GUS...")

    # Collect all epic names
    epic_names = []
    for program in structured_data['programs']:
        for project in program['projects']:
            for epic in project['epics']:
                if epic['name'] and epic['name'] != '-':
                    epic_names.append(epic['name'])

    if not epic_names:
        print("   No epics to enrich")
        return structured_data

    print(f"   Found {len(epic_names)} epics to look up")

    # Query epic IDs and planned releases in smaller batches (SOQL has character limits)
    epic_data_map = {}
    batch_size = 50  # Reduced batch size to avoid SOQL length limits

    for i in range(0, len(epic_names), batch_size):
        batch = epic_names[i:i + batch_size]
        # Escape single quotes and backslashes in epic names for SOQL
        escaped_names = [name.replace("\\", "\\\\").replace("'", "\\'") for name in batch]
        names_list = "','".join(escaped_names)

        query = f"SELECT Id, Name, Planned_Release__r.Name, End_Date__c, T_Shirt_Size__c FROM ADM_Epic__c WHERE Name IN ('{names_list}')"

        try:
            result = subprocess.run(
                ['sf', 'data', 'query', '--query', query, '--target-org', TARGET_ORG, '--json'],
                capture_output=True,
                text=True,
                check=True
            )

            data = json.loads(result.stdout)
            records = data.get('result', {}).get('records', [])

            for record in records:
                epic_data_map[record['Name']] = {
                    'id': record['Id'],
                    'planned_release': record.get('Planned_Release__r', {}).get('Name', '-') if record.get('Planned_Release__r') else '-',
                    'end_date': record.get('End_Date__c', ''),
                    't_shirt_size': record.get('T_Shirt_Size__c', '')
                }

        except Exception as e:
            print(f"   Warning: Failed to query batch {i//batch_size + 1}: {e}")
            # Continue to next batch instead of failing entirely
            continue

    print(f"   ✓ Found data for {len(epic_data_map)} epics")

    # Update epic IDs and planned releases in structured data
    enriched_count = 0
    for program in structured_data['programs']:
        for project in program['projects']:
            for epic in project['epics']:
                epic_name = epic['name']
                if epic_name in epic_data_map:
                    epic['id'] = epic_data_map[epic_name]['id']
                    epic['planned_release'] = epic_data_map[epic_name]['planned_release']
                    epic['end_date'] = epic_data_map[epic_name]['end_date']
                    epic['t_shirt_size'] = epic_data_map[epic_name]['t_shirt_size']
                    enriched_count += 1

    print(f"   ✓ Enriched {enriched_count} epics with 266 fields")

    return structured_data

def enrich_with_project_fields(structured_data):
    """Query GUS to get project Target__c field for 266 planning"""
    print("🔍 Enriching project data with Target field from GUS...")

    # Collect all project names
    project_names = []
    for program in structured_data['programs']:
        for project in program['projects']:
            if project['name'] and project['name'] != '-':
                project_names.append(project['name'])

    if not project_names:
        print("   No projects to enrich")
        return structured_data

    print(f"   Found {len(project_names)} projects to look up")

    # Query project Target fields in batches
    project_data_map = {}
    batch_size = 50

    for i in range(0, len(project_names), batch_size):
        batch = project_names[i:i + batch_size]
        # Escape single quotes and backslashes in project names for SOQL
        escaped_names = [name.replace("\\", "\\\\").replace("'", "\\'") for name in batch]
        names_list = "','".join(escaped_names)

        query = f"SELECT Id, Name, Target__c FROM PPM_Project__c WHERE Name IN ('{names_list}')"

        try:
            result = subprocess.run(
                ['sf', 'data', 'query', '--query', query, '--target-org', TARGET_ORG, '--json'],
                capture_output=True,
                text=True,
                check=True
            )

            data = json.loads(result.stdout)
            records = data.get('result', {}).get('records', [])

            for record in records:
                project_data_map[record['Name']] = {
                    'target': record.get('Target__c', '')
                }

        except Exception as e:
            print(f"   Warning: Failed to query batch {i//batch_size + 1}: {e}")
            continue

    print(f"   ✓ Found data for {len(project_data_map)} projects")

    # Update project Target fields in structured data
    enriched_count = 0
    for program in structured_data['programs']:
        for project in program['projects']:
            project_name = project['name']
            if project_name in project_data_map:
                project['target'] = project_data_map[project_name]['target']
                enriched_count += 1

    print(f"   ✓ Enriched {enriched_count} projects with Target field")

    return structured_data

def normalize_portfolio_names(structured_data):
    """Normalize portfolio names: 266+ (FY27) uses short format, 264 keeps full name"""
    import re
    print("🔍 Normalizing portfolio names...")

    # Pattern: "{release number} Field Service {pillar}"
    release_pattern = re.compile(r'^(\d+) Field Service (.+)$')

    normalized_count = 0
    for program in structured_data['programs']:
        original = program['portfolio']

        # Release-prefixed pattern
        match = release_pattern.match(original)
        if match:
            release_num = int(match.group(1))
            pillar = match.group(2)

            # 266+ (FY27) → short format
            if release_num >= 266:
                if pillar == 'Mobile':
                    new_portfolio = 'FY27 FS Mobile'
                elif pillar == 'Foundations':
                    new_portfolio = 'FY27 FS Foundations'
                elif pillar == 'Scheduling & Optimization':
                    new_portfolio = 'FY27 FS S&O'
                elif pillar == 'Workforce Scheduling':
                    new_portfolio = 'FY27 FS Workforce Scheduling'
                else:
                    new_portfolio = f'FY27 FS {pillar}'

                program['portfolio'] = new_portfolio
                if original != new_portfolio:
                    normalized_count += 1
            # 264 and earlier → keep as-is (no normalization)

        # Already FY27 named → shorten if needed
        elif original.startswith('FY27 Field Service '):
            pillar = original.replace('FY27 Field Service ', '')
            if pillar == 'Mobile':
                new_portfolio = 'FY27 FS Mobile'
            elif pillar == 'Foundations':
                new_portfolio = 'FY27 FS Foundations'
            elif pillar == 'Scheduling & Optimization':
                new_portfolio = 'FY27 FS S&O'
            elif pillar == 'Workforce Scheduling':
                new_portfolio = 'FY27 FS Workforce Scheduling'
            else:
                new_portfolio = f'FY27 FS {pillar}'

            program['portfolio'] = new_portfolio
            if original != new_portfolio:
                normalized_count += 1

    print(f"   ✓ Normalized {normalized_count} portfolio names")
    return structured_data

def fetch_field_service_teams():
    """Fetch Field Service team IDs from teams_data.json"""
    teams_file = SCRIPT_DIR / "data" / "teams_data.json"
    if not teams_file.exists():
        print("   ⚠️  teams_data.json not found, skipping team filter")
        return []

    with open(teams_file, 'r') as f:
        teams_data = json.load(f)

    active_team_names = [team['name'] for team in teams_data['teams']]

    # Get scrum team IDs
    name_conditions = " OR ".join([f"Name = '{name}'" for name in active_team_names])
    teams_query = f"""
    SELECT Id, Name
    FROM ADM_Scrum_Team__c
    WHERE {name_conditions}
    """

    try:
        result = subprocess.run(
            ['sf', 'data', 'query', '--query', teams_query, '--target-org', TARGET_ORG, '--json'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        scrum_teams = data.get('result', {}).get('records', [])
        team_ids = [team['Id'] for team in scrum_teams]
        print(f"   ✓ Found {len(team_ids)} Field Service teams")
        return team_ids
    except Exception as e:
        print(f"   ⚠️  Failed to fetch teams: {e}")
        return []

def fetch_262_projects():
    """Fetch 262 projects with their program mappings via epics (Field Service teams only)"""
    print("🔍 Fetching 262 projects for Field Service teams...")

    # Get Field Service team IDs
    team_ids = fetch_field_service_teams()
    if not team_ids:
        print("   ⚠️  No teams found, skipping 262 project fetch")
        return []

    team_ids_str = "', '".join(team_ids)

    # Query work items to get their projects (filtered by Field Service teams)
    query = f"""
    SELECT Epic__r.Project__r.Id, Epic__r.Project__r.Name,
           Epic__r.Project__r.Program__r.Name, Epic__r.Project__r.Program__r.Id,
           Epic__r.Project__r.Program__r.Portfolio__r.Name,
           Epic__r.Scheduled_Build__r.Name
    FROM ADM_Work__c
    WHERE Epic__r.Scheduled_Build__r.Name LIKE '262%'
    AND Epic__r.Project__c != null
    AND Epic__r.Project__r.Program__c != null
    AND Scrum_Team__c IN ('{team_ids_str}')
    LIMIT 50000
    """

    try:
        result = subprocess.run(
            ['sf', 'data', 'query', '--query', query, '--target-org', TARGET_ORG, '--json'],
            capture_output=True,
            text=True,
            check=True
        )

        data = json.loads(result.stdout)
        records = data.get('result', {}).get('records', [])

        # Deduplicate projects in Python
        projects = []
        seen_projects = set()
        for record in records:
            if not record.get('Epic__r') or not record['Epic__r'].get('Project__r'):
                continue

            project_data = record['Epic__r']['Project__r']
            project_id = project_data.get('Id', '')

            if project_id and project_id not in seen_projects:
                seen_projects.add(project_id)
                projects.append({
                    'Id': project_id,
                    'Name': project_data.get('Name', ''),
                    'Program__r': project_data.get('Program__r', {}),
                    'Scheduled_Build__r': record['Epic__r'].get('Scheduled_Build__r', {})
                })

        print(f"   ✓ Found {len(projects)} unique 262 projects with program assignments")
        return projects

    except Exception as e:
        print(f"   ⚠️  Failed to fetch 262 projects: {e}")
        return []

def run_soql(query):
    """Run a SOQL query via sf CLI and return the records list"""
    result = subprocess.run(
        ['sf', 'data', 'query', '--query', query, '--target-org', TARGET_ORG, '--json'],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout).get('result', {}).get('records', [])

def is_forward_facing_portfolio_name(name):
    """
    Decide if a portfolio name represents current/upcoming work vs a
    retired release. Every Field Service portfolio name carries an explicit
    release number (e.g. "264 Field Service Mobile", "FY27 Field Service
    Trust") -- that's a more reliable signal than epic LastModifiedDate,
    since old-release backlogs get bulk-groomed/triaged periodically,
    which bumps LastModifiedDate without representing new work.

    Returns True/False, or None if no release number could be found (those
    get dropped -- empirically they're vague/legacy names like "Field
    Service Cloud FY25", not real current-release portfolios).
    """
    if JUNK_PORTFOLIO_NAME_RE.search(name):
        return False
    if name in EXCLUDED_PARENT_CLOUD_PORTFOLIOS:
        return False
    if FY27_NAME_RE.search(name):
        return True
    match = RELEASE_NUMBER_RE.search(name)
    if not match:
        return None
    return int(match.group(1)) >= FORWARD_RELEASE_CUTOFF

def discover_forward_facing_portfolios():
    """
    Find Field Service portfolios via SOQL (no hardcoded portfolio list),
    scoped to release >= FORWARD_RELEASE_CUTOFF. This is what lets new
    portfolios (like FY27/266 pillars) get picked up automatically instead
    of requiring someone to edit the GUS report's filter by hand.
    """
    print("🔍 Discovering forward-facing Field Service portfolios via SOQL...")
    try:
        portfolios = run_soql(
            "SELECT Id, Name FROM PPM_Portfolio__c "
            "WHERE Name LIKE '%Field Service%' OR Name LIKE '%FSL%' OR Name LIKE '%SFS%'"
        )
    except Exception as e:
        print(f"   ⚠️  Failed to discover portfolios: {e}")
        return []

    forward = [p for p in portfolios if is_forward_facing_portfolio_name(p['Name'])]
    print(f"   ✓ {len(forward)} of {len(portfolios)} discovered portfolios are forward-facing")
    return forward

def fetch_new_release_programs(structured_data):
    """
    Fill the gap left by the GUS report's hardcoded portfolio scope: walk
    Portfolio -> Program -> Project -> Epic via SOQL for any forward-facing
    portfolio the report didn't already surface, and return program dicts
    matching parse_report_data's shape.
    """
    print("🔍 Fetching new-release programs not covered by the GUS report...")

    existing_portfolios = {p['portfolio'] for p in structured_data['programs']}
    forward_portfolios = discover_forward_facing_portfolios()
    new_portfolios = [p for p in forward_portfolios if p['Name'] not in existing_portfolios]

    if not new_portfolios:
        print("   ✓ No new portfolios to add -- report coverage is up to date")
        return []

    print(f"   ✓ {len(new_portfolios)} new portfolios not yet in execution data: "
          f"{[p['Name'] for p in new_portfolios]}")

    portfolio_map = {p['Id']: p['Name'] for p in new_portfolios}
    portfolio_idlist = ','.join(f"'{i}'" for i in portfolio_map)

    try:
        programs = run_soql(
            f"SELECT Id, Name, Portfolio__c, Program_Health__c, Program_Manager__r.Name "
            f"FROM PPM_Program__c WHERE Portfolio__c IN ({portfolio_idlist})"
        )
    except Exception as e:
        print(f"   ⚠️  Failed to fetch new-release programs: {e}")
        return []

    if not programs:
        return []

    program_idlist = ','.join(f"'{p['Id']}'" for p in programs)
    try:
        projects = run_soql(
            f"SELECT Id, Name, Program__c, Project_Health__c, "
            f"Product_Owner_Project_Object__r.Name, LastModifiedDate "
            f"FROM PPM_Project__c WHERE Program__c IN ({program_idlist})"
        )
    except Exception as e:
        print(f"   ⚠️  Failed to fetch new-release projects: {e}")
        return []

    epics = []
    project_ids = [p['Id'] for p in projects]
    chunk_size = 200
    for i in range(0, len(project_ids), chunk_size):
        chunk = project_ids[i:i + chunk_size]
        chunk_idlist = ','.join(f"'{c}'" for c in chunk)
        try:
            epics.extend(run_soql(
                f"SELECT Id, Name, Project__c, Health__c, Team__r.Name, "
                f"Scheduled_Build__r.Name, Priority__c, LastModifiedDate, "
                f"Epic_Health_Comments__c, Owner.Name "
                f"FROM ADM_Epic__c WHERE Project__c IN ({chunk_idlist})"
            ))
        except Exception as e:
            print(f"   ⚠️  Failed to fetch epics for chunk {i // chunk_size + 1}: {e}")
            continue

    epics_by_project = defaultdict(list)
    for e in epics:
        epics_by_project[e['Project__c']].append(e)

    projects_by_program = defaultdict(list)
    for p in projects:
        projects_by_program[p['Program__c']].append(p)

    new_programs = []
    for prog in programs:
        prog_projects = []
        for proj in projects_by_program.get(prog['Id'], []):
            proj_epics = []
            for e in epics_by_project.get(proj['Id'], []):
                health_status = e.get('Health__c') or 'Unknown'
                proj_epics.append({
                    'name': e['Name'],
                    'id': e['Id'],
                    'priority': e.get('Priority__c') or '-',
                    'health': parse_health_from_status(health_status),
                    'health_status': health_status,
                    'health_comments': e.get('Epic_Health_Comments__c') or '',
                    'owner': (e.get('Owner') or {}).get('Name', ''),
                    'team': (e.get('Team__r') or {}).get('Name', '-') if e.get('Team__r') else '-',
                    'scheduled_build': (e.get('Scheduled_Build__r') or {}).get('Name', '-') if e.get('Scheduled_Build__r') else '-',
                    'planned_release': '',
                    'last_modified': (e.get('LastModifiedDate') or '')[:10],
                    'loc': '',
                    'path_to_green': ''
                })
            # Empty projects would normally be dropped as noise, but this
            # whole function only runs for portfolios the GUS report doesn't
            # cover yet (new FY27 pillars) -- their projects start empty on
            # purpose, before epics get mapped in via the recommendation
            # engine or normal planning. Dropping them here made entire
            # programs disappear until someone manually mapped in a first
            # epic, which is what happened to Guided Experience, Project
            # Felix, and AMA Field App under FY27 FS Mobile.
            epic_builds = [e['scheduled_build'] for e in proj_epics if e['scheduled_build'] and e['scheduled_build'] != '-']
            prog_projects.append({
                'name': proj['Name'],
                'id': proj['Id'],
                'product_owner': (proj.get('Product_Owner_Project_Object__r') or {}).get('Name', '') if proj.get('Product_Owner_Project_Object__r') else '',
                'dev_lead': '',
                'target': max(epic_builds) if epic_builds else '',
                'last_modified': (proj.get('LastModifiedDate') or '')[:10],
                'health_status': proj.get('Project_Health__c') or 'Unknown',
                'epics': proj_epics
            })
        # A program with projects but zero epics anywhere still shows up
        # (e.g. Agentforce Mobile Adoption, 0 projects) so it's visible as a
        # candidate for the recommendation engine, not silently dropped.
        program_health = prog.get('Program_Health__c') or 'Unknown'
        new_programs.append({
            'name': prog['Name'],
            'id': prog['Id'],
            'portfolio': portfolio_map.get(prog['Portfolio__c'], 'Unknown'),
            'health': parse_health_from_status(program_health),
            'health_status': program_health,
            'program_manager': (prog.get('Program_Manager__r') or {}).get('Name', '') if prog.get('Program_Manager__r') else '',
            'target_release': '',
            'projects': prog_projects
        })

    print(f"   ✓ Built {len(new_programs)} new-release programs "
          f"({sum(len(p['projects']) for p in new_programs)} projects, "
          f"{sum(len(proj['epics']) for p in new_programs for proj in p['projects'])} epics)")
    return new_programs

def merge_262_projects(structured_data, projects_262):
    """Merge 262 projects into structured data"""
    if not projects_262:
        return structured_data

    print("🔀 Merging 262 projects into execution data...")

    # Group 262 projects by program
    programs_map = {}
    for program in structured_data['programs']:
        programs_map[program['name']] = program

    added_projects = 0
    new_programs = 0

    for proj_record in projects_262:
        program_name = proj_record.get('Program__r', {}).get('Name', '')
        if not program_name:
            continue

        project_name = proj_record.get('Name', '')
        project_id = proj_record.get('Id', '')
        scheduled_build = proj_record.get('Scheduled_Build__r', {}).get('Name', '')
        portfolio_ref = proj_record.get('Program__r', {}).get('Portfolio__r')
        portfolio = portfolio_ref.get('Name', 'Unknown') if portfolio_ref else 'Unknown'

        # Check if program exists
        if program_name not in programs_map:
            # Create new program for 262
            program_id = proj_record.get('Program__r', {}).get('Id', '')
            programs_map[program_name] = {
                'name': program_name,
                'id': program_id,
                'portfolio': portfolio,
                'health': 'Unknown',
                'health_status': 'Unknown',
                'program_manager': '',
                'target_release': '262',
                'projects': []
            }
            structured_data['programs'].append(programs_map[program_name])
            new_programs += 1

        program = programs_map[program_name]

        # Check if project already exists
        existing_project = None
        for proj in program['projects']:
            if proj['name'] == project_name or proj['id'] == project_id:
                existing_project = proj
                break

        if not existing_project:
            # Add new 262 project
            program['projects'].append({
                'name': project_name,
                'id': project_id,
                'product_owner': '',
                'dev_lead': '',
                'target': scheduled_build,
                'last_modified': '',
                'health_status': 'Unknown',
                'epics': []  # 262 projects won't have epic details from this query
            })
            added_projects += 1

    print(f"   ✓ Added {added_projects} 262 projects across {new_programs} programs")
    return structured_data

def main():
    """Main function to fetch and save execution data"""
    print("🔄 Fetching execution data from GUS...")

    # Fetch report data (264 programs/projects/epics)
    report_data = fetch_execution_report()
    if not report_data:
        print("❌ Failed to fetch report data")
        sys.exit(1)

    # Parse into structured format
    structured_data = parse_report_data(report_data)

    # Enrich with epic IDs and 266 fields from GUS
    structured_data = enrich_with_epic_ids(structured_data)
    structured_data = enrich_with_project_fields(structured_data)

    # Fetch and merge 262 projects
    projects_262 = fetch_262_projects()
    structured_data = merge_262_projects(structured_data, projects_262)

    # Fill in any forward-facing portfolios the GUS report's hardcoded scope
    # missed (e.g. new FY27/266 pillars) -- must run before
    # normalize_portfolio_names so the newly-fetched programs' portfolio
    # names get normalized consistently with the report-sourced ones.
    new_programs = fetch_new_release_programs(structured_data)
    structured_data['programs'].extend(new_programs)

    # Normalize portfolio names (FY27 Field Service Mobile → FY27 FS Mobile)
    structured_data = normalize_portfolio_names(structured_data)

    # Save to JSON file
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(structured_data, f, indent=2)

    print(f"✅ Saved {len(structured_data['programs'])} programs to {DATA_FILE}")

    # Print summary
    total_projects = sum(len(p['projects']) for p in structured_data['programs'])
    total_epics = sum(len(proj['epics']) for p in structured_data['programs'] for proj in p['projects'])
    print(f"   📊 {total_projects} projects, {total_epics} epics")

if __name__ == '__main__':
    main()
