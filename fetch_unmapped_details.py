#!/usr/bin/env python3
"""
Fetch details of unmapped work items for Allocations tab.
Shows which specific epics are contributing to the "Unmapped" capacity.
"""

import json
import subprocess
import os
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
TEAMS_FILE = SCRIPT_DIR / "data" / "teams_data.json"
EXECUTION_FILE = SCRIPT_DIR / "data" / "execution_data.json"
OUTPUT_FILE = SCRIPT_DIR / "data" / "unmapped_details.json"
TARGET_ORG = os.getenv("TARGET_ORG", "org62")  # Use env var or default to org62

def run_soql(query):
    """Execute SOQL query"""
    result = subprocess.run(
        ['sf', 'data', 'query', '--target-org', TARGET_ORG,
         '--query', query, '--json'],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    return data.get('result', {}).get('records', [])

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

print("🔄 Loading teams data...")
with open(TEAMS_FILE, 'r') as f:
    teams_data = json.load(f)

active_team_names = [team['name'] for team in teams_data['teams']]

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

# Query June delivered unmapped work items
print("\n🔄 Fetching June delivered unmapped work...")
team_ids_str = "', '".join(team_ids)
june_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c,
       Epic__r.Id, Epic__r.Name, Epic__r.Health__c,
       Epic__r.Scheduled_Build__r.Name, Epic__r.LastModifiedDate,
       Epic__r.Project__r.Name, Epic__r.Owner.Name,
       Assignee__r.Name, Subject__c, Status__c
FROM ADM_Work__c
WHERE First_Time_In_Progress__c >= 2026-06-01T00:00:00Z
  AND Closed_On__c >= 2026-06-01T00:00:00Z
  AND Closed_On__c < 2026-07-01T00:00:00Z
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
LIMIT 50000
"""

june_items = run_soql(june_query)
print(f"✅ Found {len(june_items)} June work items")

# Group unmapped items by team and epic
june_unmapped_by_team = defaultdict(lambda: defaultdict(lambda: {
    'epic_id': '',
    'epic_name': '',
    'epic_health': '',
    'epic_owner': '',
    'story_points': 0,
    'work_items': []
}))

def should_include_epic(epic):
    """Filter out pre-264 releases and ancient epics"""
    if not epic:
        return True  # Include work items with no epic (teams need to assign)

    # Check scheduled build
    scheduled_build_obj = epic.get('Scheduled_Build__r')
    if scheduled_build_obj:
        build_name = scheduled_build_obj.get('Name', '')
        if build_name and build_name != '-':
            # Exclude anything that's clearly pre-264
            if build_name.startswith(('234', '236', '238', '240', '242', '244', '246',
                                     '248', '250', '252', '254', '256', '258', '260', '262')):
                return False

    # Check last modified date - exclude anything not touched in 2026
    last_modified = epic.get('LastModifiedDate', '')
    if last_modified:
        # LastModifiedDate format: 2026-07-21T...
        year = last_modified.split('-')[0] if last_modified else ''
        if year and year < '2026':
            return False

    return True

for item in june_items:
    team_id = item.get('Scrum_Team__c')
    points = item.get('Story_Points__c', 0) or 0

    epic = item.get('Epic__r')
    project = epic.get('Project__r') if epic else None
    project_name = project.get('Name') if project else None

    if team_id in team_name_map:
        team_name = team_name_map[team_id]

        # Only include if unmapped (no project assigned) AND epic is 264+ or recent
        if not project_name and should_include_epic(epic):
            if epic:
                epic_id = epic.get('Id', 'unknown')
                epic_name = epic.get('Name', 'Unknown Epic')
                epic_health = epic.get('Health__c', 'Unknown')

                # Get epic owner
                owner_obj = epic.get('Owner')
                epic_owner = owner_obj.get('Name', '-') if owner_obj else '-'
            else:
                # No epic assigned - group under special "No Epic" entry
                epic_id = 'no-epic'
                epic_name = '[No Epic]'
                epic_health = 'Unknown'
                epic_owner = '-'

            # Aggregate by epic (or "No Epic")
            june_unmapped_by_team[team_name][epic_id]['epic_id'] = epic_id
            june_unmapped_by_team[team_name][epic_id]['epic_name'] = epic_name
            june_unmapped_by_team[team_name][epic_id]['epic_health'] = epic_health
            june_unmapped_by_team[team_name][epic_id]['epic_owner'] = epic_owner
            june_unmapped_by_team[team_name][epic_id]['story_points'] += points

            # Get work item assignee and subject
            assignee_obj = item.get('Assignee__r')
            assignee_name = assignee_obj.get('Name', '-') if assignee_obj else '-'
            subject = item.get('Subject__c', '')
            status = item.get('Status__c', 'Unknown')

            june_unmapped_by_team[team_name][epic_id]['work_items'].append({
                'id': item.get('Id', ''),
                'name': item.get('Name', ''),
                'subject': subject,
                'assignee': assignee_name,
                'status': status,
                'points': points
            })

# Query July committed unmapped work items
print("\n🔄 Fetching July committed unmapped work...")
july_query = f"""
SELECT Id, Name, Scrum_Team__c, Story_Points__c,
       Epic__r.Id, Epic__r.Name, Epic__r.Health__c,
       Epic__r.Scheduled_Build__r.Name, Epic__r.LastModifiedDate,
       Epic__r.Project__r.Name, Epic__r.Owner.Name,
       Assignee__r.Name, Subject__c, Status__c
FROM ADM_Work__c
WHERE Sprint_Timeframe__c LIKE '2026.07%'
  AND Scrum_Team__c IN ('{team_ids_str}')
  AND Story_Points__c != null
  AND Status__c NOT IN ('Closed', 'Never', 'Cancelled', 'Duplicate')
LIMIT 50000
"""

july_items = run_soql(july_query)
print(f"✅ Found {len(july_items)} July work items")

july_unmapped_by_team = defaultdict(lambda: defaultdict(lambda: {
    'epic_id': '',
    'epic_name': '',
    'epic_health': '',
    'epic_owner': '',
    'story_points': 0,
    'work_items': []
}))

for item in july_items:
    team_id = item.get('Scrum_Team__c')
    points = item.get('Story_Points__c', 0) or 0

    epic = item.get('Epic__r')
    project = epic.get('Project__r') if epic else None
    project_name = project.get('Name') if project else None

    if team_id in team_name_map:
        team_name = team_name_map[team_id]

        if not project_name and should_include_epic(epic):
            if epic:
                epic_id = epic.get('Id', 'unknown')
                epic_name = epic.get('Name', 'Unknown Epic')
                epic_health = epic.get('Health__c', 'Unknown')

                owner_obj = epic.get('Owner')
                epic_owner = owner_obj.get('Name', '-') if owner_obj else '-'
            else:
                # No epic assigned - group under special "No Epic" entry
                epic_id = 'no-epic'
                epic_name = '[No Epic]'
                epic_health = 'Unknown'
                epic_owner = '-'

            july_unmapped_by_team[team_name][epic_id]['epic_id'] = epic_id
            july_unmapped_by_team[team_name][epic_id]['epic_name'] = epic_name
            july_unmapped_by_team[team_name][epic_id]['epic_health'] = epic_health
            july_unmapped_by_team[team_name][epic_id]['epic_owner'] = epic_owner
            july_unmapped_by_team[team_name][epic_id]['story_points'] += points

            # Get work item assignee and subject
            assignee_obj = item.get('Assignee__r')
            assignee_name = assignee_obj.get('Name', '-') if assignee_obj else '-'
            subject = item.get('Subject__c', '')
            status = item.get('Status__c', 'Unknown')

            july_unmapped_by_team[team_name][epic_id]['work_items'].append({
                'id': item.get('Id', ''),
                'name': item.get('Name', ''),
                'subject': subject,
                'assignee': assignee_name,
                'status': status,
                'points': points
            })

# Convert to list format
june_unmapped_list = {}
for team_name, epics in june_unmapped_by_team.items():
    june_unmapped_list[team_name] = list(epics.values())

july_unmapped_list = {}
for team_name, epics in july_unmapped_by_team.items():
    july_unmapped_list[team_name] = list(epics.values())

# Save output
output = {
    'june_delivered_unmapped': june_unmapped_list,
    'july_committed_unmapped': july_unmapped_list
}

with open(OUTPUT_FILE, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Saved unmapped details to {OUTPUT_FILE}")
print(f"   June: {sum(len(epics) for epics in june_unmapped_list.values())} unmapped epics")
print(f"   July: {sum(len(epics) for epics in july_unmapped_list.values())} unmapped epics")
