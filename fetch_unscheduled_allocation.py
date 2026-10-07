#!/usr/bin/env python3
"""
Fetch inputs for the "Unscheduled SWE Allocations by Portfolio" donut.

Unscheduled work = open ADM_Work__c with story points and no Sprint__c, on the
same active Field Service epics counted by the "Epics with No Sprint" stat card
(Health__c not Completed/Canceled). Points are grouped by scrum team and by the
epic's program; app.py maps program -> portfolio and converts points to SWEs
using each team's velocity (delivered points over the last 90 days).

Output: data/unscheduled_allocation.json
"""

import json
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
TEAMS_FILE = DATA_DIR / "teams_data.json"
EXEC_DATA_FILE = DATA_DIR / "execution_data.json"
OUTPUT_FILE = DATA_DIR / "unscheduled_allocation.json"
TARGET_ORG = "org62"
VELOCITY_WINDOW_DAYS = 90
BATCH_SIZE = 200
EXCLUDED_STATUSES = "'Never', 'Duplicate', 'Not Reproducible', 'Closed'"


def run_soql(query):
    result = subprocess.run(
        ['sf', 'data', 'query', '--target-org', TARGET_ORG,
         '--query', query, '--json'],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout).get('result', {}).get('records', [])


def load_active_epics():
    """epic_id -> program_name for epics that are not Completed/Canceled."""
    with open(EXEC_DATA_FILE) as f:
        exec_data = json.load(f)
    epic_to_program = {}
    for program in exec_data.get('programs', []):
        for project in program.get('projects', []):
            for epic in project.get('epics', []):
                health = (epic.get('health_status') or '').lower()
                if epic.get('id') and not any(s in health for s in ('complete', 'cancel')):
                    epic_to_program[epic['id']] = program.get('name', 'Unknown')
    return epic_to_program


def main():
    with open(TEAMS_FILE) as f:
        team_names = [t['name'] for t in json.load(f)['teams']]
    name_conditions = " OR ".join(f"Name = '{n}'" for n in team_names)
    team_name_map = {
        t['Id']: t['Name']
        for t in run_soql(f"SELECT Id, Name FROM ADM_Scrum_Team__c WHERE {name_conditions}")
    }
    team_ids_str = "','".join(team_name_map)

    epic_to_program = load_active_epics()
    print(f"Active epics in scope: {len(epic_to_program)}")

    teams = defaultdict(lambda: {'unscheduled_by_program': defaultdict(float), 'delivered_90d': 0.0})

    epic_ids = list(epic_to_program)
    for i in range(0, len(epic_ids), BATCH_SIZE):
        ids_str = "','".join(epic_ids[i:i + BATCH_SIZE])
        items = run_soql(
            f"SELECT Scrum_Team__c, Epic__c, Story_Points__c FROM ADM_Work__c "
            f"WHERE Epic__c IN ('{ids_str}') AND Sprint__c = null "
            f"AND Scrum_Team__c IN ('{team_ids_str}') AND Story_Points__c != null "
            f"AND Status__c NOT IN ({EXCLUDED_STATUSES}) LIMIT 50000"
        )
        for item in items:
            team = team_name_map.get(item['Scrum_Team__c'])
            if team:
                program = epic_to_program[item['Epic__c']]
                teams[team]['unscheduled_by_program'][program] += item['Story_Points__c'] or 0
    print(f"Teams with unscheduled work: {len(teams)}")

    since = (datetime.utcnow() - timedelta(days=VELOCITY_WINDOW_DAYS)).strftime('%Y-%m-%dT00:00:00Z')
    delivered = run_soql(
        f"SELECT Scrum_Team__c, SUM(Story_Points__c) pts FROM ADM_Work__c "
        f"WHERE Closed_On__c >= {since} AND Scrum_Team__c IN ('{team_ids_str}') "
        f"AND Story_Points__c != null "
        f"AND Status__c NOT IN ('Never', 'Duplicate', 'Not Reproducible') "
        f"GROUP BY Scrum_Team__c"
    )
    for row in delivered:
        team = team_name_map.get(row['Scrum_Team__c'])
        if team:
            teams[team]['delivered_90d'] = row['pts'] or 0

    output = {
        'generated': datetime.now().isoformat(),
        'velocity_window_days': VELOCITY_WINDOW_DAYS,
        'teams': {
            name: {
                'unscheduled_by_program': dict(data['unscheduled_by_program']),
                'delivered_90d': round(data['delivered_90d'], 1),
            }
            for name, data in teams.items()
        },
    }
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    total = sum(sum(t['unscheduled_by_program'].values()) for t in output['teams'].values())
    print(f"Wrote {OUTPUT_FILE.name}: {total:.0f} unscheduled points across {len(output['teams'])} teams")


if __name__ == '__main__':
    main()
