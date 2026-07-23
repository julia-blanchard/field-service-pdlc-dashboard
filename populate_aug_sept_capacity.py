#!/usr/bin/env python3
"""
Populate August and September capacity by querying work items with
Scheduled_Build__c containing August/September patches or 266 releases
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

# Build project -> program mapping
project_to_program = {}
for program in execution_data.get('programs', []):
    if not program.get('portfolio', '').startswith('264'):
        continue
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

# Query August work items directly (264.0 through 264.4) for Field Service teams only
print("\n🔄 Finding August work items (264, 264.1, 264.2, 264.3, 264.4) for Field Service teams...")
august_items_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__c,
       Epic__r.Name, Epic__r.Scheduled_Build__r.Name, Epic__r.Project__r.Name
FROM ADM_Work__c
WHERE Epic__r.Scheduled_Build__r.Name IN ('264', '264.0', '264.1', '264.2', '264.3', '264.4')
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
LIMIT 50000
"""

august_items = run_soql(august_items_query)
print(f"✅ Found {len(august_items)} August work items for Field Service teams")

# Build epic-to-project mapping from work items
august_epic_to_project = {}
august_epic_ids = set()
for item in august_items:
    epic_id = item.get('Epic__c')
    if epic_id:
        august_epic_ids.add(epic_id)
        if epic_id not in august_epic_to_project:
            project = item.get('Epic__r', {}).get('Project__r', {}).get('Name') if item.get('Epic__r', {}).get('Project__r') else None
            august_epic_to_project[epic_id] = project

print(f"✅ Found {len(august_epic_ids)} unique August epics")

# Aggregate by team + program
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
        elif not project_name:
            # Unmapped (no project assignment)
            august_unmapped[team_name] += points

# Query September work items directly (264.4, 264.5, 264.6 + 266) for Field Service teams only
print("\n🔄 Finding September work items (264.4, 264.5, 264.6 + 266) for Field Service teams...")
september_items_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__c,
       Epic__r.Name, Epic__r.Scheduled_Build__r.Name, Epic__r.Project__r.Name
FROM ADM_Work__c
WHERE Epic__r.Scheduled_Build__r.Name IN ('264.4', '264.5', '264.6', '266', '266.0', '266.1')
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
LIMIT 50000
"""

september_items = run_soql(september_items_query)
print(f"✅ Found {len(september_items)} September work items for Field Service teams")

# Build epic-to-project mapping from work items
september_epic_to_project = {}
september_epic_ids = set()
for item in september_items:
    epic_id = item.get('Epic__c')
    if epic_id:
        september_epic_ids.add(epic_id)
        if epic_id not in september_epic_to_project:
            project = item.get('Epic__r', {}).get('Project__r', {}).get('Name') if item.get('Epic__r', {}).get('Project__r') else None
            september_epic_to_project[epic_id] = project

print(f"✅ Found {len(september_epic_ids)} unique September epics")

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
        elif not project_name:
            # Unmapped (no project assignment)
            september_unmapped[team_name] += points

# Update teams data with program breakdown
for team in teams_data['teams']:
    team_name = team['name']

    # August committed by program
    august_by_prog = dict(august_team_program.get(team_name, {}))
    august_unmapped_val = august_unmapped.get(team_name, 0)

    # Add unmapped capacity as "Orphaned" program
    if august_unmapped_val > 0:
        august_by_prog['Orphaned'] = august_unmapped_val

    team['august_committed_by_program'] = august_by_prog
    team['august_committed_unmapped'] = august_unmapped_val
    team['capacity_committed_august'] = sum(august_by_prog.values())
    team['work_items_committed_august'] = len([i for i in august_items if team_name_map.get(i.get('Scrum_Team__c')) == team_name])

    # September committed by program
    september_by_prog = dict(september_team_program.get(team_name, {}))
    september_unmapped_val = september_unmapped.get(team_name, 0)

    # Add unmapped capacity as "Orphaned" program
    if september_unmapped_val > 0:
        september_by_prog['Orphaned'] = september_unmapped_val

    team['september_committed_by_program'] = september_by_prog
    team['september_committed_unmapped'] = september_unmapped_val
    team['capacity_committed_september'] = sum(september_by_prog.values())
    team['work_items_committed_september'] = len([i for i in september_items if team_name_map.get(i.get('Scrum_Team__c')) == team_name])

# Save updated data
with open(TEAMS_FILE, 'w') as f:
    json.dump(teams_data, f, indent=2)

# Print summary
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

# Build unmapped work item details for UI expansion
print("\n🔄 Building unmapped work item details...")
unmapped_details = defaultdict(list)

# Add August unmapped work items
for item in august_items:
    team_id = item.get('Scrum_Team__c')
    epic_id = item.get('Epic__c')

    if team_id in team_name_map:
        team_name = team_name_map[team_id]
        project_name = august_epic_to_project.get(epic_id)

        # Only include items without project assignment (orphaned)
        if not project_name:
            epic_name = item.get('Epic__r', {}).get('Name', 'Unknown Epic')
            build = item.get('Epic__r', {}).get('Scheduled_Build__r', {}).get('Name', 'Unknown')

            unmapped_details[team_name].append({
                'work_item_name': item.get('Name', ''),
                'epic_name': epic_name,
                'epic_id': epic_id,
                'scheduled_build': build,
                'story_points': item.get('Story_Points__c', 0),
                'month': 'August'
            })

# Add September unmapped work items
for item in september_items:
    team_id = item.get('Scrum_Team__c')
    epic_id = item.get('Epic__c')

    if team_id in team_name_map:
        team_name = team_name_map[team_id]
        project_name = september_epic_to_project.get(epic_id)

        # Only include items without project assignment (orphaned)
        if not project_name:
            epic_name = item.get('Epic__r', {}).get('Name', 'Unknown Epic')
            build = item.get('Epic__r', {}).get('Scheduled_Build__r', {}).get('Name', 'Unknown')

            unmapped_details[team_name].append({
                'work_item_name': item.get('Name', ''),
                'epic_name': epic_name,
                'epic_id': epic_id,
                'scheduled_build': build,
                'story_points': item.get('Story_Points__c', 0),
                'month': 'September'
            })

# Save unmapped details
with open(UNMAPPED_DETAILS_FILE, 'w') as f:
    json.dump(dict(unmapped_details), f, indent=2)

total_unmapped_items = sum(len(items) for items in unmapped_details.values())
print(f"✅ Saved {total_unmapped_items} unmapped work items across {len(unmapped_details)} teams to {UNMAPPED_DETAILS_FILE}")
