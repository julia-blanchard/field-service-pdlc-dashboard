#!/usr/bin/env python3
"""
Fetch orphaned epics that have active work in June/July 2026.
Work-item driven approach: query work items first, then get epic details.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data" / "unallocated_data.json"
UNMAPPED_FILE = SCRIPT_DIR / "data" / "unmapped_details.json"
TARGET_ORG = "org62"

def sf_data_query(query):
    """Execute SOQL query using sf data query command"""
    try:
        result = subprocess.run(
            ['sf', 'data', 'query', '--target-org', 'org62',
             '--query', query, '--json'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        return data.get('result', {}).get('records', [])
    except subprocess.CalledProcessError as e:
        print(f"Error executing query: {e}")
        print(f"STDERR: {e.stderr}")
        print(f"STDOUT: {e.stdout}")
        return []
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

def load_active_teams():
    """Load list of active teams from teams_data.json"""
    teams_file = Path(__file__).parent / 'data' / 'teams_data.json'
    try:
        with open(teams_file, 'r') as f:
            teams_data = json.load(f)
        return set(team['name'] for team in teams_data.get('teams', []))
    except Exception as e:
        print(f"Warning: Could not load active teams: {e}")
        return set()

def get_unique_epic_ids_from_unmapped():
    """Extract unique epic IDs from unmapped_details.json"""
    print("Loading epic IDs from unmapped_details.json...")
    with open(UNMAPPED_FILE, 'r') as f:
        data = json.load(f)

    epic_ids = set()

    # June epics
    for team_name, epic_list in data.get('june_delivered_unmapped', {}).items():
        for epic_obj in epic_list:
            epic_id = epic_obj.get('epic_id')
            if epic_id and epic_id != 'no_epic':
                epic_ids.add(epic_id)

    # July epics
    for team_name, epic_list in data.get('july_committed_unmapped', {}).items():
        for epic_obj in epic_list:
            epic_id = epic_obj.get('epic_id')
            if epic_id and epic_id != 'no_epic':
                epic_ids.add(epic_id)

    print(f"Found {len(epic_ids)} unique epic IDs")
    return list(epic_ids)

def fetch_epic_details(epic_ids):
    """Fetch full details for the given epic IDs"""
    if not epic_ids:
        return []

    print(f"Fetching details for {len(epic_ids)} epics...")

    # Query in batches of 100
    all_epics = []
    batch_size = 100

    for i in range(0, len(epic_ids), batch_size):
        batch = epic_ids[i:i+batch_size]
        ids_str = "', '".join(batch)

        query = f"""
        SELECT Id, Name, Health__c, Epic_Health_Comments__c,
               Priority__c, Scheduled_Build__r.Name,
               Owner.Name, Owner.IsActive, Team__r.Name,
               Project__r.Name,
               LastModifiedDate,
               Actual_Story_Points_on_Epic__c
        FROM ADM_Epic__c
        WHERE Id IN ('{ids_str}')
        """

        records = sf_data_query(query)
        all_epics.extend(records)
        print(f"  Fetched batch {i//batch_size + 1}: {len(records)} epics")

    return all_epics

def parse_epic_records(records, active_teams):
    """Parse epic records into standard format"""
    epics = []

    for record in records:
        # Parse story points
        try:
            story_points = float(record.get('Actual_Story_Points_on_Epic__c', 0) or 0)
        except:
            story_points = 0

        # Extract nested relationship fields
        scheduled_build = record.get('Scheduled_Build__r', {}).get('Name', '-') if record.get('Scheduled_Build__r') else '-'
        owner_obj = record.get('Owner', {})
        owner = owner_obj.get('Name', '-') if owner_obj else '-'
        owner_is_active = owner_obj.get('IsActive', True) if owner_obj else True
        team = record.get('Team__r', {}).get('Name', '-') if record.get('Team__r') else '-'

        # Get project name
        project_obj = record.get('Project__r')
        project_name = project_obj.get('Name', '-') if project_obj else '-'

        # Only include active teams
        if team not in active_teams:
            continue

        # Only include active owners
        if not owner_is_active:
            continue

        epic = {
            'id': record.get('Id', ''),
            'name': record.get('Name', ''),
            'priority': record.get('Priority__c', '-'),
            'health': record.get('Health__c', 'Unknown'),
            'health_status': record.get('Health__c', 'Unknown'),
            'health_comments': record.get('Epic_Health_Comments__c', '-'),
            'owner': owner,
            'owner_is_active': owner_is_active,
            'team': team,
            'scheduled_build': scheduled_build,
            'status': record.get('Health__c', 'Unknown'),
            'last_modified': record.get('LastModifiedDate', '')[:10] if record.get('LastModifiedDate') else '',
            'story_points': story_points,
            'program_name': '-',
            'program_portfolio': '-',
            'project_name': project_name,
            'is_orphaned': True,
            'category': '⚠️ Orphaned (No Program/Project)'
        }

        epics.append(epic)

    return epics

def group_by_team(epics):
    """Group epics by team with capacity calculations"""
    teams = defaultdict(list)
    for epic in epics:
        team = epic['team']
        if team and team != '-':
            teams[team].append(epic)

    # Convert to sorted list
    team_list = []
    for team_name, team_epics in sorted(teams.items()):
        total_capacity = sum(e.get('story_points', 0) for e in team_epics)
        orphaned_capacity = sum(e.get('story_points', 0) for e in team_epics if e.get('is_orphaned'))

        team_list.append({
            'name': team_name,
            'epic_count': len(team_epics),
            'orphaned_count': sum(1 for e in team_epics if e.get('is_orphaned')),
            'total_capacity': round(total_capacity, 1),
            'orphaned_capacity': round(orphaned_capacity, 1),
            'epics': team_epics
        })

    return team_list

def group_by_release(epics):
    """Group epics by scheduled build/release with capacity calculations"""
    releases = defaultdict(list)

    for epic in epics:
        release = epic['scheduled_build']
        if not release or release == '-':
            release = 'Release Month Not Assigned'
        releases[release].append(epic)

    # Sort releases
    def sort_key(item):
        release = item[0]
        if release == 'Release Month Not Assigned':
            return (999, release)
        try:
            parts = release.split('.')
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            return (major, minor, release)
        except:
            return (500, release)

    sorted_releases = sorted(releases.items(), key=sort_key)

    # Convert to list format
    release_list = []
    for release_name, release_epics in sorted_releases:
        total_capacity = sum(e.get('story_points', 0) for e in release_epics)
        orphaned_capacity = sum(e.get('story_points', 0) for e in release_epics if e.get('is_orphaned'))

        release_list.append({
            'name': release_name,
            'epic_count': len(release_epics),
            'orphaned_count': sum(1 for e in release_epics if e.get('is_orphaned')),
            'teams': len(set(e['team'] for e in release_epics if e['team'] != '-')),
            'total_capacity': round(total_capacity, 1),
            'orphaned_capacity': round(orphaned_capacity, 1),
            'epics': release_epics
        })

    return release_list

def generate_summary_stats(epics):
    """Generate summary statistics with capacity"""
    total = len(epics)
    orphaned = sum(1 for e in epics if e.get('is_orphaned'))

    total_capacity = sum(e.get('story_points', 0) for e in epics)
    orphaned_capacity = sum(e.get('story_points', 0) for e in epics if e.get('is_orphaned'))

    # Health breakdown
    health_counts = defaultdict(int)
    for epic in epics:
        health_counts[epic['health']] += 1

    # Team count
    unique_teams = len(set(e['team'] for e in epics if e['team'] != '-'))

    return {
        'total_epics': total,
        'orphaned_epics': orphaned,
        'future_release_epics': 0,
        'no_release_epics': sum(1 for e in epics if e['scheduled_build'] in ['-', 'Release Month Not Assigned']),
        'unique_teams': unique_teams,
        'total_capacity': round(total_capacity, 1),
        'orphaned_capacity': round(orphaned_capacity, 1),
        'future_capacity': 0,
        'no_release_capacity': 0,
        'health_breakdown': dict(health_counts)
    }

def main():
    """Main execution flow"""
    print("=" * 60)
    print("Fetching Orphaned Epics with June/July 2026 Work")
    print("=" * 60)

    # Load active teams
    active_teams = load_active_teams()
    print(f"Loaded {len(active_teams)} active teams")

    # Get unique epic IDs from unmapped_details.json
    epic_ids = get_unique_epic_ids_from_unmapped()

    if not epic_ids:
        print("No epic IDs found")
        return

    # Fetch full epic details
    records = fetch_epic_details(epic_ids)

    if not records:
        print("No epic records found")
        return

    # Parse into structured format
    epics = parse_epic_records(records, active_teams)

    print(f"Parsed {len(epics)} epics (filtered to active teams/owners)")

    # Group by team and release
    teams = group_by_team(epics)
    releases = group_by_release(epics)

    # Generate summary
    summary = generate_summary_stats(epics)

    # Build output structure
    output = {
        'last_updated': datetime.now().isoformat(),
        'summary': summary,
        'epics': epics,
        'by_team': teams,
        'by_release': releases
    }

    # Save to file
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Saved {len(epics)} epics to {DATA_FILE}")
    print(f"\nSummary:")
    print(f"  Total Epics: {summary['total_epics']}")
    print(f"  Orphaned (no program/project): {summary['orphaned_epics']}")
    print(f"  No release assigned: {summary['no_release_epics']}")
    print(f"  Unique teams: {summary['unique_teams']}")
    print(f"\n  Total Capacity: {summary['total_capacity']} PD")
    print(f"  Orphaned Capacity: {summary['orphaned_capacity']} PD")
    print(f"\nBy Team: {len(teams)} teams")
    print(f"By Release: {len(releases)} release groups")

if __name__ == '__main__':
    main()
