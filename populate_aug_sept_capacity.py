#!/usr/bin/env python3
"""
Populate August and September capacity by querying work items IN SPRINTS
that start in those months (NOT by epic build numbers).

CRITICAL: Epic Scheduled_Build__c indicates WHICH RELEASE, not WHEN work happens.
Work is scheduled by Sprint__r.Start_Date__c.
"""

import json
import subprocess
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
TEAMS_FILE = SCRIPT_DIR / "data" / "teams_data.json"
EXECUTION_FILE = SCRIPT_DIR / "data" / "execution_data.json"
UNMAPPED_DETAILS_FILE = SCRIPT_DIR / "data" / "unmapped_details.json"
TARGET_ORG = "org62"

def run_soql(query):
    """Execute SOQL query"""
    result = subprocess.run(
        ['sf', 'data', 'query', '--target-org', TARGET_ORG,
         '--query', query, '--json'],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    return data.get('result', {}).get('records', [])

# Load execution data to get program-project mappings
print("🔄 Loading execution data...")
with open(EXECUTION_FILE, 'r') as f:
    execution_data = json.load(f)

# Build project -> program mapping (all programs, not just 264)
project_to_program = {}
for program in execution_data.get('programs', []):
    program_name = program.get('name', '')
    for project in program.get('projects', []):
        project_name = project.get('name', '')
        project_to_program[project_name] = program_name

print(f"✅ Mapped {len(project_to_program)} projects to programs")

# Load teams data
print("🔄 Loading teams data...")
with open(TEAMS_FILE, 'r') as f:
    teams_data = json.load(f)

active_team_names = [team['name'] for team in teams_data['teams']]

# Get scrum team IDs
print("🔄 Fetching scrum team IDs...")
name_conditions = " OR ".join([f"Name = '{name}'" for name in active_team_names])
teams_query = f"""
SELECT Id, Name
FROM ADM_Scrum_Team__c
WHERE {name_conditions}
"""
scrum_teams = run_soql(teams_query)
team_name_map = {team['Id']: team['Name'] for team in scrum_teams}
team_ids = list(team_name_map.keys())
print(f"✅ Found {len(scrum_teams)} teams")

team_ids_str = "', '".join(team_ids)

# Query June work items (DELIVERED - by Closed_On__c date)
print("\n🔄 Finding June 2026 work items (delivered/closed in June)...")
june_delivered_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__c,
       Epic__r.Name, Epic__r.Project__r.Name, Epic__r.Scheduled_Build__r.Name,
       Epic__r.Health__c,
       Owner.Name, Status__c, Closed_On__c,
       Sprint__r.Name, Sprint__r.Start_Date__c
FROM ADM_Work__c
WHERE Closed_On__c >= 2026-06-01T00:00:00Z
  AND Closed_On__c < 2026-07-01T00:00:00Z
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
  AND CreatedBy.Name != 'Test Failure Sweeper User'
  AND Status__c != 'Never'
  AND Type__c != 'Duplicate'
LIMIT 50000
"""

june_items = run_soql(june_delivered_query)
print(f"✅ Found {len(june_items)} June work items (delivered)")

# Build epic-to-project mapping for June
june_epic_to_project = {}
for item in june_items:
    epic_id = item.get('Epic__c')
    if epic_id and epic_id not in june_epic_to_project:
        project = item.get('Epic__r', {}).get('Project__r', {}).get('Name') if item.get('Epic__r', {}).get('Project__r') else None
        june_epic_to_project[epic_id] = project

# Query July work items (for unmapped details only)
print("\n🔄 Finding July 2026 work items (by sprint start date)...")
july_sprinted_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__c,
       Epic__r.Name, Epic__r.Project__r.Name, Epic__r.Scheduled_Build__r.Name,
       Epic__r.Health__c,
       Owner.Name, Status__c,
       Sprint__r.Name, Sprint__r.Start_Date__c
FROM ADM_Work__c
WHERE Sprint__r.Start_Date__c >= 2026-07-01
  AND Sprint__r.Start_Date__c < 2026-08-01
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
  AND CreatedBy.Name != 'Test Failure Sweeper User'
  AND Status__c != 'Never'
  AND Type__c != 'Duplicate'
LIMIT 50000
"""

july_items = run_soql(july_sprinted_query)
print(f"✅ Found {len(july_items)} July work items")

# Build epic-to-project mapping for July
july_epic_to_project = {}
for item in july_items:
    epic_id = item.get('Epic__c')
    if epic_id and epic_id not in july_epic_to_project:
        project = item.get('Epic__r', {}).get('Project__r', {}).get('Name') if item.get('Epic__r', {}).get('Project__r') else None
        july_epic_to_project[epic_id] = project

# Query August work items - TWO sources:
# 1. Work in sprints starting in August 2026
# 2. Work with August patch builds (264.0-264.4) but NO sprint assignment yet
print("\n🔄 Finding August 2026 work items (by sprint start date)...")
august_sprinted_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__c,
       Epic__r.Name, Epic__r.Project__r.Name, Epic__r.Scheduled_Build__r.Name,
       Epic__r.Health__c,
       Owner.Name, Status__c,
       Sprint__r.Name, Sprint__r.Start_Date__c
FROM ADM_Work__c
WHERE Sprint__r.Start_Date__c >= 2026-08-01
  AND Sprint__r.Start_Date__c < 2026-09-01
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
  AND CreatedBy.Name != 'Test Failure Sweeper User'
  AND Status__c != 'Never'
  AND Type__c != 'Duplicate'
LIMIT 50000
"""

august_sprinted = run_soql(august_sprinted_query)
print(f"✅ Found {len(august_sprinted)} sprinted August work items")

print("🔄 Finding work assigned to August patches but not yet sprinted...")
august_unsprinted_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__c,
       Epic__r.Name, Epic__r.Project__r.Name, Epic__r.Scheduled_Build__r.Name,
       Epic__r.Health__c,
       Owner.Name, Status__c,
       Sprint__r.Name, Sprint__r.Start_Date__c
FROM ADM_Work__c
WHERE Epic__r.Scheduled_Build__r.Name IN ('264', '264.0', '264.1', '264.2', '264.3', '264.4')
  AND Sprint__c = null
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
  AND CreatedBy.Name != 'Test Failure Sweeper User'
  AND Status__c != 'Never'
  AND Type__c != 'Duplicate'
LIMIT 50000
"""

august_unsprinted = run_soql(august_unsprinted_query)
print(f"✅ Found {len(august_unsprinted)} unsprinted work items targeting August patches")

# Combine and dedupe (in case any appear in both)
august_items_dict = {item['Id']: item for item in august_sprinted}
for item in august_unsprinted:
    if item['Id'] not in august_items_dict:
        august_items_dict[item['Id']] = item

august_items = list(august_items_dict.values())
print(f"✅ Total August work items: {len(august_items)}")

# Build epic-to-project mapping
august_epic_to_project = {}
for item in august_items:
    epic_id = item.get('Epic__c')
    if epic_id and epic_id not in august_epic_to_project:
        project = item.get('Epic__r', {}).get('Project__r', {}).get('Name') if item.get('Epic__r', {}).get('Project__r') else None
        august_epic_to_project[epic_id] = project

# Query September work items - TWO sources:
# 1. Work in sprints starting in September 2026
# 2. Work with September patch builds (264.5, 264.6, 266.0) but NO sprint assignment yet
print("\n🔄 Finding September 2026 work items (by sprint start date)...")
september_sprinted_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__c,
       Epic__r.Name, Epic__r.Project__r.Name, Epic__r.Scheduled_Build__r.Name,
       Epic__r.Health__c,
       Owner.Name, Status__c,
       Sprint__r.Name, Sprint__r.Start_Date__c
FROM ADM_Work__c
WHERE Sprint__r.Start_Date__c >= 2026-09-01
  AND Sprint__r.Start_Date__c < 2026-10-01
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
  AND CreatedBy.Name != 'Test Failure Sweeper User'
  AND Status__c != 'Never'
  AND Type__c != 'Duplicate'
LIMIT 50000
"""

september_sprinted = run_soql(september_sprinted_query)
print(f"✅ Found {len(september_sprinted)} sprinted September work items")

print("🔄 Finding work assigned to September patches but not yet sprinted...")
september_unsprinted_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__c,
       Epic__r.Name, Epic__r.Project__r.Name, Epic__r.Scheduled_Build__r.Name,
       Epic__r.Health__c,
       Owner.Name, Status__c,
       Sprint__r.Name, Sprint__r.Start_Date__c
FROM ADM_Work__c
WHERE Epic__r.Scheduled_Build__r.Name IN ('264.5', '264.6', '266', '266.0', '266.1')
  AND Sprint__c = null
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
  AND CreatedBy.Name != 'Test Failure Sweeper User'
  AND Status__c != 'Never'
  AND Type__c != 'Duplicate'
LIMIT 50000
"""

september_unsprinted = run_soql(september_unsprinted_query)
print(f"✅ Found {len(september_unsprinted)} unsprinted work items targeting September patches")

# Combine and dedupe (in case any appear in both)
september_items_dict = {item['Id']: item for item in september_sprinted}
for item in september_unsprinted:
    if item['Id'] not in september_items_dict:
        september_items_dict[item['Id']] = item

september_items = list(september_items_dict.values())
print(f"✅ Total September work items: {len(september_items)}")

# Build epic-to-project mapping
september_epic_to_project = {}
for item in september_items:
    epic_id = item.get('Epic__c')
    if epic_id and epic_id not in september_epic_to_project:
        project = item.get('Epic__r', {}).get('Project__r', {}).get('Name') if item.get('Epic__r', {}).get('Project__r') else None
        september_epic_to_project[epic_id] = project

# Aggregate June capacity by team + program
june_team_program = defaultdict(lambda: defaultdict(float))
june_unmapped = defaultdict(float)

for item in june_items:
    team_id = item.get('Scrum_Team__c')
    points = item.get('Story_Points__c', 0) or 0
    epic_id = item.get('Epic__c')

    project_name = june_epic_to_project.get(epic_id)

    if team_id in team_name_map:
        team_name = team_name_map[team_id]

        if project_name and project_name in project_to_program:
            program_name = project_to_program[project_name]
            june_team_program[team_name][program_name] += points
        else:
            # Unmapped (no project assignment or project not in execution data)
            june_unmapped[team_name] += points

# Aggregate July capacity by team + program
july_team_program = defaultdict(lambda: defaultdict(float))
july_unmapped = defaultdict(float)

for item in july_items:
    team_id = item.get('Scrum_Team__c')
    points = item.get('Story_Points__c', 0) or 0
    epic_id = item.get('Epic__c')

    project_name = july_epic_to_project.get(epic_id)

    if team_id in team_name_map:
        team_name = team_name_map[team_id]

        if project_name and project_name in project_to_program:
            program_name = project_to_program[project_name]
            july_team_program[team_name][program_name] += points
        else:
            # Unmapped (no project assignment or project not in execution data)
            july_unmapped[team_name] += points

# Aggregate August capacity by team + program
august_team_program = defaultdict(lambda: defaultdict(float))
august_unmapped = defaultdict(float)

for item in august_items:
    team_id = item.get('Scrum_Team__c')
    points = item.get('Story_Points__c', 0) or 0
    epic_id = item.get('Epic__c')

    project_name = august_epic_to_project.get(epic_id)

    if team_id in team_name_map:
        team_name = team_name_map[team_id]

        if project_name and project_name in project_to_program:
            program_name = project_to_program[project_name]
            august_team_program[team_name][program_name] += points
        else:
            # Unmapped (no project assignment or project not in execution data)
            august_unmapped[team_name] += points

# Aggregate September capacity by team + program
september_team_program = defaultdict(lambda: defaultdict(float))
september_unmapped = defaultdict(float)

for item in september_items:
    team_id = item.get('Scrum_Team__c')
    points = item.get('Story_Points__c', 0) or 0
    epic_id = item.get('Epic__c')

    project_name = september_epic_to_project.get(epic_id)

    if team_id in team_name_map:
        team_name = team_name_map[team_id]

        if project_name and project_name in project_to_program:
            program_name = project_to_program[project_name]
            september_team_program[team_name][program_name] += points
        else:
            # Unmapped (no project assignment or project not in execution data)
            september_unmapped[team_name] += points

# Update teams data with program breakdown (June-September)
for team in teams_data['teams']:
    team_name = team['name']

    # June delivered by program
    june_by_prog = dict(june_team_program.get(team_name, {}))
    june_unmapped_val = june_unmapped.get(team_name, 0)

    team['june_delivered_by_program'] = june_by_prog
    team['june_delivered_unmapped'] = june_unmapped_val
    team['capacity_delivered_june'] = sum(june_by_prog.values()) + june_unmapped_val
    team['work_items_delivered_june'] = len([i for i in june_items if team_name_map.get(i.get('Scrum_Team__c')) == team_name])

    # July committed by program
    july_by_prog = dict(july_team_program.get(team_name, {}))
    july_unmapped_val = july_unmapped.get(team_name, 0)

    team['july_committed_by_program'] = july_by_prog
    team['july_committed_unmapped'] = july_unmapped_val
    team['capacity_committed_july'] = sum(july_by_prog.values()) + july_unmapped_val
    team['work_items_committed_july'] = len([i for i in july_items if team_name_map.get(i.get('Scrum_Team__c')) == team_name])

    # August committed by program
    august_by_prog = dict(august_team_program.get(team_name, {}))
    august_unmapped_val = august_unmapped.get(team_name, 0)

    team['august_committed_by_program'] = august_by_prog
    team['august_committed_unmapped'] = august_unmapped_val
    team['capacity_committed_august'] = sum(august_by_prog.values()) + august_unmapped_val
    team['work_items_committed_august'] = len([i for i in august_items if team_name_map.get(i.get('Scrum_Team__c')) == team_name])

    # September committed by program
    september_by_prog = dict(september_team_program.get(team_name, {}))
    september_unmapped_val = september_unmapped.get(team_name, 0)

    team['september_committed_by_program'] = september_by_prog
    team['september_committed_unmapped'] = september_unmapped_val
    team['capacity_committed_september'] = sum(september_by_prog.values()) + september_unmapped_val
    team['work_items_committed_september'] = len([i for i in september_items if team_name_map.get(i.get('Scrum_Team__c')) == team_name])

# Save updated data
with open(TEAMS_FILE, 'w') as f:
    json.dump(teams_data, f, indent=2)

# Print summary for all four months
print("\n📊 June Delivered Capacity by Program:")
june_program_totals = defaultdict(float)
for team_name, programs in june_team_program.items():
    for program, points in programs.items():
        june_program_totals[program] += points

for program, points in sorted(june_program_totals.items(), key=lambda x: x[1], reverse=True):
    print(f"  {program}: {points:.1f} points")

total_june_unmapped = sum(june_unmapped.values())
print(f"  [Unmapped]: {total_june_unmapped:.1f} points")

print("\n📊 July Committed Capacity by Program:")
july_program_totals = defaultdict(float)
for team_name, programs in july_team_program.items():
    for program, points in programs.items():
        july_program_totals[program] += points

for program, points in sorted(july_program_totals.items(), key=lambda x: x[1], reverse=True):
    print(f"  {program}: {points:.1f} points")

total_july_unmapped = sum(july_unmapped.values())
print(f"  [Unmapped]: {total_july_unmapped:.1f} points")

print("\n📊 August Committed Capacity by Program:")
august_program_totals = defaultdict(float)
for team_name, programs in august_team_program.items():
    for program, points in programs.items():
        august_program_totals[program] += points

for program, points in sorted(august_program_totals.items(), key=lambda x: x[1], reverse=True):
    print(f"  {program}: {points:.1f} points")

total_august_unmapped = sum(august_unmapped.values())
print(f"  [Unmapped]: {total_august_unmapped:.1f} points")

print("\n📊 September Committed Capacity by Program:")
september_program_totals = defaultdict(float)
for team_name, programs in september_team_program.items():
    for program, points in programs.items():
        september_program_totals[program] += points

for program, points in sorted(september_program_totals.items(), key=lambda x: x[1], reverse=True):
    print(f"  {program}: {points:.1f} points")

total_september_unmapped = sum(september_unmapped.values())
print(f"  [Unmapped]: {total_september_unmapped:.1f} points")

print(f"\n✅ Updated {TEAMS_FILE}")

# Build unmapped work item details grouped by epic for UI expansion (June-September)
print("\n🔄 Building unmapped work item details grouped by epic (June-September)...")
unmapped_by_team_epic = defaultdict(lambda: defaultdict(lambda: {
    'epic_id': None,
    'epic_name': None,
    'epic_status': None,
    'story_points': 0,
    'work_items': [],
    'months': set()
}))

# Add June unmapped work items
for item in june_items:
    team_id = item.get('Scrum_Team__c')
    epic_id = item.get('Epic__c') or 'no-epic'

    if team_id in team_name_map:
        team_name = team_name_map[team_id]
        project_name = june_epic_to_project.get(epic_id)

        # Only include items without project assignment (orphaned)
        if not project_name or project_name not in project_to_program:
            epic_name = item.get('Epic__r', {}).get('Name', '[No Epic Assignment]') if item.get('Epic__r') else '[No Epic Assignment]'
            epic_build = item.get('Epic__r', {}).get('Scheduled_Build__r') if item.get('Epic__r') else None
            build = epic_build.get('Name', '-') if epic_build else '-'
            sprint_info = item.get('Sprint__r')
            sprint_name = sprint_info.get('Name', 'No Sprint') if sprint_info else 'No Sprint'

            epic_key = epic_id if epic_id != 'no-epic' else 'no-epic'
            epic_group = unmapped_by_team_epic[team_name][epic_key]

            if not epic_group['epic_id']:
                epic_group['epic_id'] = epic_id if epic_id != 'no-epic' else 'no-epic'
                epic_group['epic_name'] = epic_name
                epic_health = item.get('Epic__r', {}).get('Health__c') if item.get('Epic__r') else None
                epic_group['epic_status'] = epic_health

            epic_group['story_points'] += item.get('Story_Points__c', 0)
            epic_group['months'].add('June')

            owner_info = item.get('Owner')
            assignee_name = owner_info.get('Name', '-') if owner_info else '-'

            epic_group['work_items'].append({
                'work_item_name': item.get('Name', ''),
                'work_item_id': item.get('Id', ''),
                'scheduled_build': build,
                'sprint_name': sprint_name,
                'story_points': item.get('Story_Points__c', 0),
                'assignee': assignee_name,
                'status': item.get('Status__c', '-'),
                'month': 'June'
            })

# Add July unmapped work items
for item in july_items:
    team_id = item.get('Scrum_Team__c')
    epic_id = item.get('Epic__c') or 'no-epic'

    if team_id in team_name_map:
        team_name = team_name_map[team_id]
        project_name = july_epic_to_project.get(epic_id)

        # Only include items without project assignment (orphaned)
        if not project_name or project_name not in project_to_program:
            epic_name = item.get('Epic__r', {}).get('Name', '[No Epic Assignment]') if item.get('Epic__r') else '[No Epic Assignment]'
            epic_build = item.get('Epic__r', {}).get('Scheduled_Build__r') if item.get('Epic__r') else None
            build = epic_build.get('Name', '-') if epic_build else '-'
            sprint_info = item.get('Sprint__r')
            sprint_name = sprint_info.get('Name', 'No Sprint') if sprint_info else 'No Sprint'

            epic_key = epic_id if epic_id != 'no-epic' else 'no-epic'
            epic_group = unmapped_by_team_epic[team_name][epic_key]

            if not epic_group['epic_id']:
                epic_group['epic_id'] = epic_id if epic_id != 'no-epic' else 'no-epic'
                epic_group['epic_name'] = epic_name
                epic_health = item.get('Epic__r', {}).get('Health__c') if item.get('Epic__r') else None
                epic_group['epic_status'] = epic_health

            epic_group['story_points'] += item.get('Story_Points__c', 0)
            epic_group['months'].add('July')

            owner_info = item.get('Owner')
            assignee_name = owner_info.get('Name', '-') if owner_info else '-'

            epic_group['work_items'].append({
                'work_item_name': item.get('Name', ''),
                'work_item_id': item.get('Id', ''),
                'scheduled_build': build,
                'sprint_name': sprint_name,
                'story_points': item.get('Story_Points__c', 0),
                'assignee': assignee_name,
                'status': item.get('Status__c', '-'),
                'month': 'July'
            })

# Add August unmapped work items
for item in august_items:
    team_id = item.get('Scrum_Team__c')
    epic_id = item.get('Epic__c') or 'no-epic'

    if team_id in team_name_map:
        team_name = team_name_map[team_id]
        project_name = august_epic_to_project.get(epic_id)

        # Only include items without project assignment (orphaned)
        if not project_name or project_name not in project_to_program:
            epic_name = item.get('Epic__r', {}).get('Name', '[No Epic Assignment]') if item.get('Epic__r') else '[No Epic Assignment]'
            epic_build = item.get('Epic__r', {}).get('Scheduled_Build__r') if item.get('Epic__r') else None
            build = epic_build.get('Name', '-') if epic_build else '-'
            sprint_info = item.get('Sprint__r')
            sprint_name = sprint_info.get('Name', 'No Sprint') if sprint_info else 'No Sprint'

            epic_key = epic_id if epic_id != 'no-epic' else 'no-epic'
            epic_group = unmapped_by_team_epic[team_name][epic_key]

            if not epic_group['epic_id']:
                epic_group['epic_id'] = epic_id if epic_id != 'no-epic' else 'no-epic'
                epic_group['epic_name'] = epic_name
                # Get Epic Health from Epic__r.Health__c
                epic_health = item.get('Epic__r', {}).get('Health__c') if item.get('Epic__r') else None
                epic_group['epic_status'] = epic_health

            epic_group['story_points'] += item.get('Story_Points__c', 0)
            epic_group['months'].add('August')

            owner_info = item.get('Owner')
            assignee_name = owner_info.get('Name', '-') if owner_info else '-'

            epic_group['work_items'].append({
                'work_item_name': item.get('Name', ''),
                'work_item_id': item.get('Id', ''),
                'scheduled_build': build,
                'sprint_name': sprint_name,
                'story_points': item.get('Story_Points__c', 0),
                'assignee': assignee_name,
                'status': item.get('Status__c', '-'),
                'month': 'August'
            })

# Add September unmapped work items
for item in september_items:
    team_id = item.get('Scrum_Team__c')
    epic_id = item.get('Epic__c') or 'no-epic'

    if team_id in team_name_map:
        team_name = team_name_map[team_id]
        project_name = september_epic_to_project.get(epic_id)

        # Only include items without project assignment (orphaned)
        if not project_name or project_name not in project_to_program:
            epic_name = item.get('Epic__r', {}).get('Name', '[No Epic Assignment]') if item.get('Epic__r') else '[No Epic Assignment]'
            epic_build = item.get('Epic__r', {}).get('Scheduled_Build__r') if item.get('Epic__r') else None
            build = epic_build.get('Name', '-') if epic_build else '-'
            sprint_info = item.get('Sprint__r')
            sprint_name = sprint_info.get('Name', 'No Sprint') if sprint_info else 'No Sprint'

            epic_key = epic_id if epic_id != 'no-epic' else 'no-epic'
            epic_group = unmapped_by_team_epic[team_name][epic_key]

            if not epic_group['epic_id']:
                epic_group['epic_id'] = epic_id if epic_id != 'no-epic' else 'no-epic'
                epic_group['epic_name'] = epic_name
                # Get Epic Health from Epic__r.Health__c
                epic_health = item.get('Epic__r', {}).get('Health__c') if item.get('Epic__r') else None
                epic_group['epic_status'] = epic_health

            epic_group['story_points'] += item.get('Story_Points__c', 0)
            epic_group['months'].add('September')

            owner_info = item.get('Owner')
            assignee_name = owner_info.get('Name', '-') if owner_info else '-'

            epic_group['work_items'].append({
                'work_item_name': item.get('Name', ''),
                'work_item_id': item.get('Id', ''),
                'scheduled_build': build,
                'sprint_name': sprint_name,
                'story_points': item.get('Story_Points__c', 0),
                'assignee': assignee_name,
                'status': item.get('Status__c', '-'),
                'month': 'September'
            })

# Convert to final structure
unmapped_details = {}
for team_name, epics in unmapped_by_team_epic.items():
    unmapped_details[team_name] = []
    for epic_key, epic_data in epics.items():
        epic_data['months'] = list(epic_data['months'])  # Convert set to list for JSON
        unmapped_details[team_name].append(epic_data)

# Save unmapped details
with open(UNMAPPED_DETAILS_FILE, 'w') as f:
    json.dump(unmapped_details, f, indent=2)

total_epics = sum(len(epics) for epics in unmapped_details.values())
total_work_items = sum(len(epic['work_items']) for epics in unmapped_details.values() for epic in epics)
print(f"✅ Saved {total_epics} epic groups with {total_work_items} work items across {len(unmapped_details)} teams to {UNMAPPED_DETAILS_FILE}")
