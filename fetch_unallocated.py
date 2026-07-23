#!/usr/bin/env python3
"""
Fetch Unallocated Field Service Work from GUS
Shows epics that are either:
1. Not mapped to a program/project
2. Scheduled for future releases (266+)
3. In early stages without clear release assignment
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data" / "unallocated_data.json"
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

def fetch_epics_with_recent_activity(epic_ids):
    """
    Batch query to find which epics have work items with Closed_On__c since 2026-01-01.
    Returns a set of epic IDs that have recent activity.
    Much faster than querying each epic individually.
    """
    if not epic_ids:
        return set()

    # Query in batches of 200
    all_active_epic_ids = set()
    batch_size = 200

    print(f"Checking work activity for {len(epic_ids)} epics...")

    for i in range(0, len(epic_ids), batch_size):
        batch = epic_ids[i:i+batch_size]
        ids_str = "', '".join(batch)

        query = f"""
        SELECT Epic__c
        FROM ADM_Work__c
        WHERE Epic__c IN ('{ids_str}')
          AND Closed_On__c >= 2026-01-01T00:00:00Z
        GROUP BY Epic__c
        """

        try:
            records = sf_data_query(query)
            batch_active = {r['Epic__c'] for r in records if r.get('Epic__c')}
            all_active_epic_ids.update(batch_active)
            print(f"  Batch {i//batch_size + 1}/{(len(epic_ids)-1)//batch_size + 1}: {len(batch_active)} epics with activity")
        except Exception as e:
            print(f"Warning: Could not check work activity for batch: {e}")
            # On error, assume all epics in batch are active
            all_active_epic_ids.update(batch)

    print(f"Found {len(all_active_epic_ids)} epics with work activity since 2026-01-01")
    return all_active_epic_ids

def load_project_to_program_mapping():
    """Load project->program mapping from execution_data.json"""
    execution_file = Path(__file__).parent / 'data' / 'execution_data.json'
    try:
        with open(execution_file, 'r') as f:
            execution_data = json.load(f)

        project_to_program = {}
        for program in execution_data.get('programs', []):
            portfolio = program.get('portfolio', '')
            # Include 264 portfolios and FY27 portfolios (e.g., FY27 SC M4 UWM)
            if not (portfolio.startswith('264') or portfolio.startswith('FY27')):
                continue
            program_name = program.get('name', '')
            for project in program.get('projects', []):
                project_name = project.get('name', '')
                project_to_program[project_name] = program_name

        return project_to_program
    except Exception as e:
        print(f"Warning: Could not load project->program mapping: {e}")
        return {}

def fetch_all_field_service_epics_direct():
    """
    Query ALL Field Service epics directly via SOQL.
    This matches the approach used in map_capacity_to_programs.py
    so we can find truly orphaned epics (those with no project/program).

    Note: ADM_Epic__c does not have Status__c field. Using Health__c instead.
    Health__c values: Not Started, On Track, Watch, On Hold, Completed, Canceled
    """
    query = """
    SELECT Id, Name, Health__c, Epic_Health_Comments__c,
           Priority__c, Scheduled_Build__r.Name,
           Owner.Name, Owner.IsActive, Team__r.Name,
           Project__r.Name,
           CreatedDate, LastModifiedDate,
           Actual_Story_Points_on_Epic__c
    FROM ADM_Epic__c
    WHERE (Team__r.Name LIKE '%Field Service%'
           OR Team__r.Name LIKE '%SFS%'
           OR Team__r.Name LIKE '%FSL%')
      AND Health__c NOT IN ('Completed', 'Canceled')
    ORDER BY Team__r.Name, LastModifiedDate DESC
    """

    print("Querying ALL Field Service epics from GUS...")
    records = sf_data_query(query)
    print(f"Found {len(records)} total Field Service epics")

    # Load project->program mapping
    project_to_program = load_project_to_program_mapping()
    print(f"Loaded {len(project_to_program)} project->program mappings")

    # Parse into standard format
    all_epics = []
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

        # Get project name - handle null case
        project_obj = record.get('Project__r')
        project_name = project_obj.get('Name', '-') if project_obj else '-'

        # Map project to program (same logic as map_capacity_to_programs.py)
        program_name = '-'
        if project_name and project_name != '-' and project_name in project_to_program:
            program_name = project_to_program[project_name]

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
            'status': record.get('Health__c', 'Unknown'),  # Using Health__c as status (no Status__c field)
            'created_date': record.get('CreatedDate', '')[:10] if record.get('CreatedDate') else '',
            'last_modified': record.get('LastModifiedDate', '')[:10] if record.get('LastModifiedDate') else '',
            'story_points': story_points,
            'program_name': program_name,
            'program_portfolio': '-',  # We'll fetch portfolio separately if needed
            'project_name': project_name
        }

        all_epics.append(epic)

    return all_epics

def check_epic_work_items(epic_ids):
    """
    Check work items for given epics to see if all work is closed/nevered.
    Returns set of epic IDs that have all work in terminal states.
    """
    print(f"Checking work items for {len(epic_ids)} epics...")

    terminal_states = {'Closed', 'Never', 'Cancelled', 'Duplicate'}
    all_closed_epic_ids = set()

    # Query in batches
    batch_size = 100
    for i in range(0, len(epic_ids), batch_size):
        batch = epic_ids[i:i+batch_size]
        ids_str = "', '".join(batch)

        query = f"""
        SELECT Epic__c, Status__c
        FROM ADM_Work__c
        WHERE Epic__c IN ('{ids_str}')
        """

        work_items = sf_data_query(query)

        # Group by epic
        from collections import defaultdict
        epic_work = defaultdict(list)
        for item in work_items:
            epic_id = item.get('Epic__c')
            status = item.get('Status__c', 'Unknown')
            epic_work[epic_id].append(status)

        # Check which epics have all work closed
        for epic_id in batch:
            work_statuses = epic_work.get(epic_id, [])
            if work_statuses:  # Has work items
                closed_count = sum(1 for s in work_statuses if s in terminal_states)
                if closed_count == len(work_statuses):
                    all_closed_epic_ids.add(epic_id)

    print(f"  Found {len(all_closed_epic_ids)} epics with all work closed/nevered")
    return all_closed_epic_ids

def filter_for_unallocated(all_epics):
    """
    Filter epics to find unallocated/orphaned ones:
    1. ORPHANED: Missing project OR program (no upstream nesting)
    2. FUTURE RELEASE: Scheduled for 266+ but may have proper nesting
    3. NO RELEASE: Has program/project but no scheduled build assigned

    Only includes epics for release 264 and beyond (current and future work).
    Excludes stale epics last modified before 2025 (removes 2023-2024 work).
    Only includes epics from active teams (28 current teams).
    Excludes epics owned by inactive employees.
    Excludes epics with all work items closed/nevered.
    """
    # Load active teams
    active_teams = load_active_teams()

    # First pass: collect epic IDs that pass initial filters
    candidate_epic_ids = []
    epic_by_id = {}

    for epic in all_epics:
        # Filter to only active teams
        team = epic.get('team', '')
        if team not in active_teams:
            continue

        # Filter out epics owned by inactive employees
        if not epic.get('owner_is_active', True):
            continue

        # Filter out epics with 0 story points created before 2026 (old work, likely abandoned)
        story_points = epic.get('story_points', 0)
        created_date = epic.get('created_date', '')
        if story_points == 0 and created_date and created_date < '2026-01-01':
            continue

        # Filter out epics not modified in 2026 (focus on current year work only)
        last_modified = epic.get('last_modified', '')
        if last_modified and last_modified < '2026-01-01':
            continue

        epic_id = epic.get('id', '')
        if epic_id:
            candidate_epic_ids.append(epic_id)
            epic_by_id[epic_id] = epic

    # Batch query for work activity (much faster than per-epic queries)
    active_epic_ids = fetch_epics_with_recent_activity(candidate_epic_ids)

    unallocated = []

    for epic_id in candidate_epic_ids:
        epic = epic_by_id[epic_id]

        scheduled_build = epic.get('scheduled_build', '-')
        last_modified = epic.get('last_modified', '')
        epic_name = epic.get('name', '')

        # Include epics with EITHER:
        # 1. Work activity since 2026 (Closed_On__c >= 2026-01-01) OR
        # 2. Scheduled for 264+/266+ releases (scheduled_build field) OR
        # 3. Epic name starts with 264/266/268/270/272 (common naming convention)
        has_future_release = (
            (scheduled_build and scheduled_build not in ['-', '', 'Backlog'] and any(scheduled_build.startswith(x) for x in ['264', '266', '268', '270', '272']))
            or any(epic_name.startswith(x) for x in ['264', '266', '268', '270', '272'])
        )

        if epic_id not in active_epic_ids and not has_future_release:
            continue

        # Filter out epics not modified in 6+ months UNLESS they have 264+ in the title
        six_months_ago = '2026-01-20'
        import re

        if last_modified and last_modified < six_months_ago:
            # Check if name contains current release numbers (264+)
            has_current_release = bool(re.search(r'\b(264|266|268|270|272)\b', epic_name))
            if not has_current_release:
                continue  # Skip old epics without current release in name

        # Filter out epics with old release numbers (246-262) in the title
        # These are leftover from old releases even if recently modified
        old_release_pattern = r'\b(246|248|250|252|254|256|258|260|262)\b'
        if re.search(old_release_pattern, epic_name):
            continue  # Skip epics with old release numbers in name

        program_name = epic.get('program_name', '')
        project_name = epic.get('project_name', '')

        # Parse release number from scheduled_build
        # Examples: "264", "266", "264.1.0", "FSL.Android.264", "SFS 258 patch #7", "Backlog", "-"
        import re
        release_num = None

        if scheduled_build and scheduled_build not in ['-', '', 'Backlog', 'Future build']:
            # Check for pre-264 releases explicitly (same as fetch_unmapped_details.py)
            if any(scheduled_build.startswith(old) for old in ['234', '236', '238', '240', '242', '244', '246', '248', '250', '252', '254', '256', '258', '260', '262']):
                continue  # Skip pre-264 releases

            # For standard releases: extract leading number (264, 266, 264.10)
            match = re.match(r'^(\d+)', scheduled_build)
            if match:
                release_num = int(match.group(1))
            else:
                # For mobile/platform/patch releases: extract ANY 3-digit number
                # Matches: "FSL.Android.232", "SFS 258 patch #7", "SFS.Xplatform.250.0.0"
                match = re.search(r'\b(\d{3})\b', scheduled_build)
                if match:
                    release_num = int(match.group(1))
                    if release_num < 264:
                        continue  # Skip if extracted number is pre-264

        # Only include epics for 264 and beyond (or no release/backlog)
        is_current_or_future = (
            release_num is None or  # No release assigned or special builds
            release_num >= 264 or   # 264 and beyond
            scheduled_build in ['Backlog', '-', '', 'Future build']
        )

        if not is_current_or_future:
            continue  # Skip old releases (< 264)

        # Check if truly orphaned (no project assigned in GUS)
        # If epic has no project, it can't have a program (can't skip hierarchy levels)
        is_orphaned = not project_name or project_name == '-'

        # ONLY include truly orphaned epics (no project assignment)
        # Epics with projects that aren't in the portfolio go to "Needs Attention"
        if is_orphaned:
            epic['is_orphaned'] = True
            unallocated.append(epic)

    print(f"Filtered to {len(unallocated)} unallocated epics (264+)")

    # Note: We no longer filter out epics with all work closed/completed
    # Completed work in 2026 that's orphaned represents unmapped capacity that should be visible

    return unallocated

def fetch_unallocated_epics():
    """
    Fetch Field Service epics that are:
    - Orphaned (missing program/project)
    - OR scheduled for future releases (266+)
    - OR not assigned to a release yet
    """
    all_epics = fetch_all_field_service_epics_direct()
    unallocated = filter_for_unallocated(all_epics)
    return unallocated

def parse_epic_data(epics):
    """
    Epics are already parsed and filtered.
    Add category labels for display.
    """
    for epic in epics:
        # Categorize based on flags set by filter_for_unallocated
        if epic.get('is_orphaned'):
            epic['category'] = '⚠️ Orphaned (No Program/Project)'
        elif epic.get('is_future_release'):
            epic['category'] = '🚀 Future Release (266+)'
        elif epic.get('is_unscheduled'):
            epic['category'] = '📅 Release Month Not Assigned'
        else:
            epic['category'] = 'Other'

    return epics

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

def extract_release_number(epic_name):
    """Extract release number from epic name for sorting (264, 266, etc.)"""
    import re
    # Look for 3-digit release numbers (264, 266, 268, etc.)
    match = re.search(r'\b(2\d{2})\b', epic_name)
    if match:
        return int(match.group(1))
    return 999  # No release number, sort to bottom

def group_by_team(epics):
    """Group epics by team with capacity calculations"""
    # Load active teams to filter
    active_teams = load_active_teams()
    print(f"Filtering to {len(active_teams)} active teams")

    teams = defaultdict(list)
    for epic in epics:
        team = epic['team']
        if team and team != '-':
            # Only include active teams
            if not active_teams or team in active_teams:
                teams[team].append(epic)

    # Convert to sorted list
    team_list = []
    for team_name, team_epics in sorted(teams.items()):
        # Sort epics within team by release number (264 first, 266 last)
        team_epics.sort(key=lambda e: (extract_release_number(e['name']), e['name']))
        # Calculate total story points (capacity)
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

    # Sort releases (TBD/null last)
    def sort_key(item):
        release = item[0]
        if release == 'Release Month Not Assigned':
            return (999, release)
        # Try to parse as version number
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
        # Sort epics within release by epic name
        release_epics.sort(key=lambda e: e['name'])

        # Calculate total story points (capacity)
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
    future_release = sum(1 for e in epics if e.get('is_future_release'))
    no_release = sum(1 for e in epics if e.get('is_unscheduled'))

    # Capacity calculations
    total_capacity = sum(e.get('story_points', 0) for e in epics)
    orphaned_capacity = sum(e.get('story_points', 0) for e in epics if e.get('is_orphaned'))
    future_capacity = sum(e.get('story_points', 0) for e in epics if e.get('is_future_release'))
    no_release_capacity = sum(e.get('story_points', 0) for e in epics if e.get('is_unscheduled'))

    # Health breakdown
    health_counts = defaultdict(int)
    for epic in epics:
        health_counts[epic['health']] += 1

    # Team count
    unique_teams = len(set(e['team'] for e in epics if e['team'] != '-'))

    return {
        'total_epics': total,
        'orphaned_epics': orphaned,
        'future_release_epics': future_release,
        'no_release_epics': no_release,
        'unique_teams': unique_teams,
        'total_capacity': round(total_capacity, 1),
        'orphaned_capacity': round(orphaned_capacity, 1),
        'future_capacity': round(future_capacity, 1),
        'no_release_capacity': round(no_release_capacity, 1),
        'health_breakdown': dict(health_counts)
    }

def main():
    """Main execution flow"""
    print("=" * 60)
    print("Fetching Unallocated Field Service Work")
    print("=" * 60)

    # Fetch raw data
    records = fetch_unallocated_epics()

    if not records:
        print("No unallocated epics found")
        return

    # Parse into structured format
    epics = parse_epic_data(records)

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
    print(f"  Future releases (266+): {summary['future_release_epics']}")
    print(f"  No release assigned: {summary['no_release_epics']}")
    print(f"  Unique teams: {summary['unique_teams']}")
    print(f"\n  Total Capacity: {summary['total_capacity']} PD")
    print(f"  Orphaned Capacity: {summary['orphaned_capacity']} PD")
    print(f"\nBy Team: {len(teams)} teams")
    print(f"By Release: {len(releases)} release groups")

if __name__ == '__main__':
    main()
