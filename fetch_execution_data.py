#!/usr/bin/env python3
"""
Fetch Field Service Execution Status data from GUS Report
Report ID: 00OEE000002tswH2AQ (264 Field Service Program Epic Admin)
Shows: Programs -> Projects -> Epics with health information
"""

import json
import subprocess
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data" / "execution_data.json"
REPORT_ID = "00OEE000002tswH2AQ"  # Field Service report
TARGET_ORG = os.getenv("TARGET_ORG", "org62")  # Use env var or default to org62

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
    """Query GUS to get epic IDs by name"""
    print("🔍 Enriching epic data with IDs from GUS...")

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

    # Query epic IDs in smaller batches (SOQL has character limits)
    epic_id_map = {}
    batch_size = 50  # Reduced batch size to avoid SOQL length limits

    for i in range(0, len(epic_names), batch_size):
        batch = epic_names[i:i + batch_size]
        # Escape single quotes and backslashes in epic names for SOQL
        escaped_names = [name.replace("\\", "\\\\").replace("'", "\\'") for name in batch]
        names_list = "','".join(escaped_names)

        query = f"SELECT Id, Name FROM ADM_Epic__c WHERE Name IN ('{names_list}')"

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
                epic_id_map[record['Name']] = record['Id']

        except Exception as e:
            print(f"   Warning: Failed to query batch {i//batch_size + 1}: {e}")
            # Continue to next batch instead of failing entirely
            continue

    print(f"   ✓ Found IDs for {len(epic_id_map)} epics")

    # Update epic IDs in structured data
    for program in structured_data['programs']:
        for project in program['projects']:
            for epic in project['epics']:
                epic_name = epic['name']
                if epic_name in epic_id_map:
                    epic['id'] = epic_id_map[epic_name]

    return structured_data

def main():
    """Main function to fetch and save execution data"""
    print("🔄 Fetching execution data from GUS...")

    # Fetch report data
    report_data = fetch_execution_report()
    if not report_data:
        print("❌ Failed to fetch report data")
        return

    # Parse into structured format
    structured_data = parse_report_data(report_data)

    # Enrich with epic IDs from GUS
    structured_data = enrich_with_epic_ids(structured_data)

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
