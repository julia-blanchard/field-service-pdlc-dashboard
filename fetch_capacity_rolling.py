#!/usr/bin/env python3
"""
Dynamic rolling 4-month capacity fetch system.
Automatically determines:
- Month -1: Historical (delivered via Closed_On__c)
- Month 0: Current month (committed via Sprint start dates)
- Month +1: Next month (planned via Sprint start dates + unsprinted work)
- Month +2: Future month (planned via Sprint start dates + unsprinted work)

No manual updates needed - automatically adjusts as calendar advances.
"""

import json
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from calendar import monthrange

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data" / "teams_data.json"
EXEC_DATA_FILE = SCRIPT_DIR / "data" / "execution_data.json"
TARGET_ORG = "org62"

# Map build numbers to calendar months (update as needed for future releases)
# Format: build_number -> (year, month)
BUILD_TO_MONTH_MAP = {
    '262': (2026, 6),   # June 2026
    '264': (2026, 8),   # August 2026 (264.0-264.4)
    '266': (2026, 10),  # October 2026 (264.5-264.6, 266.0)
    '268': (2026, 12),  # December 2026
    '270': (2027, 2),   # February 2027
    '272': (2027, 4),   # April 2027
    '274': (2027, 6),   # June 2027
}

def get_rolling_months():
    """Calculate the 4 rolling months based on current date"""
    today = datetime.now()
    current_year = today.year
    current_month = today.month

    months = []

    # Month -1: Previous month (historical)
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    months.append({
        'offset': -1,
        'year': prev_year,
        'month': prev_month,
        'name': datetime(prev_year, prev_month, 1).strftime('%B').lower(),
        'label': datetime(prev_year, prev_month, 1).strftime('%B'),
        'type': 'delivered',
        'sublabel': 'Capacity Delivered'
    })

    # Month 0: Current month
    months.append({
        'offset': 0,
        'year': current_year,
        'month': current_month,
        'name': datetime(current_year, current_month, 1).strftime('%B').lower(),
        'label': datetime(current_year, current_month, 1).strftime('%B'),
        'type': 'committed',
        'sublabel': 'Capacity Committed'
    })

    # Month +1: Next month
    next_month = current_month + 1 if current_month < 12 else 1
    next_year = current_year if current_month < 12 else current_year + 1
    months.append({
        'offset': 1,
        'year': next_year,
        'month': next_month,
        'name': datetime(next_year, next_month, 1).strftime('%B').lower(),
        'label': datetime(next_year, next_month, 1).strftime('%B'),
        'type': 'planned',
        'sublabel': 'Capacity Planned'
    })

    # Month +2: Future month
    future_month = current_month + 2 if current_month <= 10 else (current_month + 2) - 12
    future_year = current_year if current_month <= 10 else current_year + 1
    months.append({
        'offset': 2,
        'year': future_year,
        'month': future_month,
        'name': datetime(future_year, future_month, 1).strftime('%B').lower(),
        'label': datetime(future_year, future_month, 1).strftime('%B'),
        'type': 'planned',
        'sublabel': 'Capacity Planned'
    })

    return months

def get_patch_builds_for_month(year, month):
    """Get all patch build numbers that target a specific month"""
    builds = []
    for build_num, (build_year, build_month) in BUILD_TO_MONTH_MAP.items():
        if build_year == year and build_month == month:
            # Add main build and common patches
            builds.append(build_num)
            builds.append(f"{build_num}.0")
            builds.append(f"{build_num}.1")
            builds.append(f"{build_num}.2")
            builds.append(f"{build_num}.3")
            builds.append(f"{build_num}.4")
            builds.append(f"{build_num}.5")
            builds.append(f"{build_num}.6")
    return builds

def run_soql(query):
    """Execute SOQL query"""
    result = subprocess.run(
        ['sf', 'data', 'query', '--target-org', TARGET_ORG,
         '--query', query, '--json'],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    return data.get('result', {}).get('records', [])

def build_epic_to_program_map():
    """Build lookup: epic_name -> program_name from execution data"""
    epic_to_program = {}
    try:
        with open(EXEC_DATA_FILE, 'r') as f:
            exec_data = json.load(f)
        for program in exec_data.get('programs', []):
            program_name = program.get('name', 'Unknown')
            for project in program.get('projects', []):
                for epic in project.get('epics', []):
                    epic_name = epic.get('name')
                    if epic_name:
                        epic_to_program[epic_name] = program_name
        print(f"✅ Built epic → program map with {len(epic_to_program)} epics")
        return epic_to_program
    except Exception as e:
        print(f"⚠️  Could not load execution data: {e}")
        return {}

def fetch_capacity_for_month(month_config, team_ids, team_name_map, epic_to_program):
    """Fetch capacity data for a single month based on its type"""
    year = month_config['year']
    month = month_config['month']
    month_type = month_config['type']
    month_name = month_config['name']

    print(f"\n🔄 Fetching {month_name.title()} {year} capacity ({month_type})...")

    team_ids_str = "', '".join(team_ids)

    if month_type == 'delivered':
        # Historical: Query by Closed_On__c date
        first_day = f"{year}-{month:02d}-01T00:00:00Z"
        last_day = datetime(year, month, monthrange(year, month)[1])
        last_day_str = f"{last_day.year}-{last_day.month:02d}-{last_day.day:02d}T23:59:59Z"

        query = f"""
        SELECT Id, Name, Scrum_Team__c, Story_Points__c, Closed_On__c, Status__c, Epic__r.Name
        FROM ADM_Work__c
        WHERE Closed_On__c >= {first_day}
          AND Closed_On__c <= {last_day_str}
          AND Scrum_Team__c IN ('{team_ids_str}')
          AND Story_Points__c != null
          AND Status__c NOT IN ('Never', 'Duplicate', 'Not Reproducible')
        LIMIT 50000
        """

        items = run_soql(query)
        print(f"✅ Found {len(items)} delivered work items")

    else:
        # Committed/Planned: Query by Sprint start date + unsprinted work targeting patches
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1)
        else:
            last_day = datetime(year, month + 1, 1)

        first_day_str = first_day.strftime('%Y-%m-%d')
        last_day_str = last_day.strftime('%Y-%m-%d')

        # Part 1: Sprinted work
        sprinted_query = f"""
        SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__r.Name,
               Sprint__r.Name, Sprint__r.Start_Date__c
        FROM ADM_Work__c
        WHERE Sprint__r.Start_Date__c >= {first_day_str}
          AND Sprint__r.Start_Date__c < {last_day_str}
          AND Scrum_Team__c IN ('{team_ids_str}')
          AND Story_Points__c != null
          AND Status__c NOT IN ('Never', 'Duplicate', 'Not Reproducible', 'Closed')
        LIMIT 50000
        """

        sprinted_items = run_soql(sprinted_query)
        print(f"✅ Found {len(sprinted_items)} sprinted work items")

        # Part 2: Unsprinted work targeting patch builds for this month
        patch_builds = get_patch_builds_for_month(year, month)

        if patch_builds:
            builds_str = "', '".join(patch_builds)
            unsprinted_query = f"""
            SELECT Id, Name, Scrum_Team__c, Story_Points__c, Epic__r.Name,
                   Epic__r.Scheduled_Build__r.Name
            FROM ADM_Work__c
            WHERE Epic__r.Scheduled_Build__r.Name IN ('{builds_str}')
              AND Sprint__c = null
              AND Scrum_Team__c IN ('{team_ids_str}')
              AND Story_Points__c != null
              AND Status__c NOT IN ('Never', 'Duplicate', 'Not Reproducible', 'Closed')
            LIMIT 50000
            """

            unsprinted_items = run_soql(unsprinted_query)
            print(f"✅ Found {len(unsprinted_items)} unsprinted work items targeting patches: {', '.join(patch_builds[:3])}{'...' if len(patch_builds) > 3 else ''}")

            # Combine and dedupe
            items_dict = {item['Id']: item for item in sprinted_items}
            for item in unsprinted_items:
                if item['Id'] not in items_dict:
                    items_dict[item['Id']] = item

            items = list(items_dict.values())
            print(f"✅ Total {month_name.title()} work items: {len(items)}")
        else:
            items = sprinted_items

    # Aggregate by team and program
    team_capacity = defaultdict(lambda: {'points': 0, 'work_items': 0, 'by_program': defaultdict(float)})

    for item in items:
        team_id = item.get('Scrum_Team__c')
        story_points = item.get('Story_Points__c', 0) or 0
        epic_name = item.get('Epic__r', {}).get('Name') if item.get('Epic__r') else None

        if team_id in team_name_map:
            team_name = team_name_map[team_id]
            team_capacity[team_name]['points'] += story_points
            team_capacity[team_name]['work_items'] += 1

            # Map to program via epic name
            if epic_name and epic_name in epic_to_program:
                program_name = epic_to_program[epic_name]
                team_capacity[team_name]['by_program'][program_name] += story_points
            else:
                team_capacity[team_name]['by_program']['Unmapped'] += story_points

    return team_capacity

def main():
    print("=" * 80)
    print("🔄 DYNAMIC ROLLING CAPACITY FETCH")
    print("=" * 80)

    # Calculate rolling months
    months = get_rolling_months()

    print("\n📅 Rolling 4-month window:")
    for m in months:
        print(f"   {m['label']} {m['year']} ({m['offset']:+d}) - {m['type'].upper()}: {m['sublabel']}")

    # Build epic → program mapping
    epic_to_program = build_epic_to_program_map()

    # Load teams data
    print("\n🔄 Loading active Field Service teams...")
    with open(DATA_FILE, 'r') as f:
        teams_data = json.load(f)

    active_team_names = [team['name'] for team in teams_data['teams']]
    print(f"✅ Loaded {len(active_team_names)} active teams")

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
    print(f"✅ Found {len(scrum_teams)} matching scrum teams")

    # Fetch capacity for each month
    all_capacity_data = {}
    for month_config in months:
        capacity = fetch_capacity_for_month(month_config, team_ids, team_name_map, epic_to_program)
        all_capacity_data[month_config['name']] = {
            'config': month_config,
            'capacity': capacity
        }

    # Update teams data with all months
    for team in teams_data['teams']:
        team_name = team['name']
        filled = team.get('filled', 0)

        for month_config in months:
            month_name = month_config['name']
            month_type = month_config['type']

            # Calculate theoretical capacity
            capacity_limit_key = f"{month_name}_capacity_limit"
            team[capacity_limit_key] = filled * 0.8 * 22

            # Set actual capacity data
            capacity_data = all_capacity_data[month_name]['capacity']

            if month_type == 'delivered':
                points_key = f"{month_name}_delivered"
                items_key = f"{month_name}_work_items"
                by_program_key = f"{month_name}_delivered_by_program"
            else:
                points_key = f"{month_name}_committed"
                items_key = f"{month_name}_work_items"
                by_program_key = f"{month_name}_committed_by_program"

            if team_name in capacity_data:
                team[points_key] = round(capacity_data[team_name]['points'], 1)
                team[items_key] = capacity_data[team_name]['work_items']
                team[by_program_key] = dict(capacity_data[team_name]['by_program'])
            else:
                team[points_key] = 0
                team[items_key] = 0
                team[by_program_key] = {}

    # Store month metadata
    teams_data['capacity_months'] = months
    teams_data['last_updated'] = datetime.now().isoformat()

    # Save updated data
    with open(DATA_FILE, 'w') as f:
        json.dump(teams_data, f, indent=2)

    # Print summary
    print("\n" + "=" * 80)
    print("📊 CAPACITY SUMMARY")
    print("=" * 80)

    for month_config in months:
        month_name = month_config['name']
        month_label = month_config['label']
        month_type = month_config['type']
        capacity_data = all_capacity_data[month_name]['capacity']

        total_points = sum(data['points'] for data in capacity_data.values())
        total_items = sum(data['work_items'] for data in capacity_data.values())

        print(f"\n{month_label} {month_config['year']} ({month_type.upper()}):")
        print(f"  Total Story Points: {total_points:.1f}")
        print(f"  Total Work Items: {total_items}")

    print("\n✅ Updated " + str(DATA_FILE))
    print("\n💡 Month configuration saved to teams_data.capacity_months")
    print("   Template will auto-render based on this metadata")

if __name__ == '__main__':
    main()
