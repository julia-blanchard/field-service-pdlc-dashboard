#!/usr/bin/env python3
"""
Fetch Field Service Teams Roster data from GUS
Report: Field Service Gus Roster - June 2026 (00OEE000002a9YH2AY)
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data" / "teams_data.json"
REPORT_ID = "00OEE000002a9YH2AY"
TARGET_ORG = "org62"

def fetch_report():
    """Fetch report from GUS"""
    print("🔄 Fetching teams roster from GUS...")
    result = subprocess.run(
        ['sf', 'api', 'request', 'rest', '--target-org', TARGET_ORG,
         f'/services/data/v64.0/analytics/reports/{REPORT_ID}?includeDetails=true',
         '--method', 'GET'],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)

def count_filled_nonfilled(groupings, factMap):
    """Recursively count filled/non-filled positions in subgroupings"""
    filled = 0
    non_filled = 0

    for group in groupings:
        group_key = group.get('key', '')
        fact_key = f"{group_key}!T"
        fact_data = factMap.get(fact_key, {})
        rows = fact_data.get('rows', [])

        for row in rows:
            cells = row.get('dataCells', [])
            if len(cells) >= 6:
                status = cells[5].get('label', '')
                if status == 'Filled':
                    filled += 1
                elif status == 'Non-filled':
                    non_filled += 1

        if group.get('groupings'):
            sub_filled, sub_nonfilled = count_filled_nonfilled(
                group.get('groupings'), factMap
            )
            filled += sub_filled
            non_filled += sub_nonfilled

    return filled, non_filled

def derive_team_portfolios():
    """Derive team→portfolio mapping from actual epic assignments in GUS data"""
    exec_data_path = os.path.join(SCRIPT_DIR, 'data', 'execution_data.json')
    team_portfolio_map = {}

    if os.path.exists(exec_data_path):
        with open(exec_data_path, 'r') as f:
            exec_data = json.load(f)

        # Build map of team → set of portfolios from epic assignments
        for prog in exec_data.get('programs', []):
            portfolio = prog.get('portfolio', '')
            if not portfolio:
                continue
            for proj in prog.get('projects', []):
                for epic in proj.get('epics', []):
                    epic_team = epic.get('team', '')
                    if epic_team and epic_team != '-':
                        if epic_team not in team_portfolio_map:
                            team_portfolio_map[epic_team] = set()
                        team_portfolio_map[epic_team].add(portfolio)

    # Convert sets to sorted lists for JSON serialization
    for team in team_portfolio_map:
        team_portfolio_map[team] = sorted(list(team_portfolio_map[team]))

    return team_portfolio_map

def parse_teams(report_data):
    """Parse teams from report groupings"""
    teams_list = []

    groupings_down = report_data.get('groupingsDown', {})
    top_groups = groupings_down.get('groupings', [])
    factMap = report_data.get('factMap', {})

    # Load derived team→portfolio mapping from actual GUS data
    print("🔍 Deriving team portfolios from GUS execution data...")
    team_portfolio_map = derive_team_portfolios()
    print(f"   ✓ Found portfolio mappings for {len(team_portfolio_map)} teams")

    for team_group in top_groups:
        team_name = team_group.get('label', 'Unknown')
        team_key = team_group.get('key', '')

        # Get aggregate count for this team
        fact_key = f"{team_key}!T"
        fact_data = factMap.get(fact_key, {})
        aggregates = fact_data.get('aggregates', [])
        total_count = aggregates[0].get('value', 0) if aggregates else 0

        # Count filled vs non-filled
        filled, non_filled = count_filled_nonfilled(
            team_group.get('groupings', []), factMap
        )

        # Use derived mapping or fall back to name-based logic
        if team_name in team_portfolio_map:
            portfolios = team_portfolio_map[team_name]
        else:
            # Fallback for teams with no current epic assignments
            portfolios = []
            if team_name.startswith('FSL'):
                portfolios.append('264 Field Service Foundations')
            elif team_name.startswith('SFS Mobile') or 'SFS Mobile' in team_name:
                portfolios.append('264 Field Service Mobile')
            elif 'Scheduling' in team_name or 'Optimization' in team_name:
                portfolios.append('264 Field Service Scheduling & Optimization')
            elif 'WFM' in team_name or 'Worker' in team_name:
                portfolios.append('264 Field Service Workforce Scheduling')
            else:
                portfolios.append('264 Field Service Foundations')

        teams_list.append({
            'name': team_name,
            'filled': filled,
            'non_filled': non_filled,
            'total': total_count,
            'portfolios': portfolios
        })

    return teams_list

print("🔄 Fetching teams roster data from GUS...")
report_data = fetch_report()

teams = parse_teams(report_data)

# Load existing teams data to preserve capacity fields
existing_data = {}
if DATA_FILE.exists():
    try:
        existing_data = json.loads(DATA_FILE.read_text())
        print(f"📋 Loaded existing teams data to preserve capacity fields")
    except Exception as e:
        print(f"⚠️  Could not load existing data: {e}")

# Build a map of existing team capacity data
existing_teams_map = {}
if existing_data.get('teams'):
    for team in existing_data['teams']:
        existing_teams_map[team['name']] = team

# Merge new roster data with existing capacity data
for team in teams:
    team_name = team['name']
    if team_name in existing_teams_map:
        existing_team = existing_teams_map[team_name]
        # Preserve all capacity-related fields and manager data
        capacity_fields = [
            'capacity_delivered_june', 'work_items_closed_june',
            'capacity_committed_july', 'work_items_committed_july',
            'capacity_committed_august', 'work_items_committed_august',
            'capacity_committed_september', 'work_items_committed_september',
            'june_delivered_by_program', 'june_delivered_unmapped',
            'july_committed_by_program', 'july_committed_unmapped',
            'august_committed_by_program', 'august_committed_unmapped',
            'september_committed_by_program', 'september_committed_unmapped',
            'engineering_manager', 'product_owner'
        ]
        for field in capacity_fields:
            if field in existing_team:
                team[field] = existing_team[field]
        print(f"   ✓ Preserved capacity data for {team_name}")

output = {
    'last_updated': datetime.now().isoformat(),
    'teams': teams
}

DATA_FILE.parent.mkdir(exist_ok=True)
DATA_FILE.write_text(json.dumps(output, indent=2))

total_filled = sum(t['filled'] for t in teams)
total_non_filled = sum(t['non_filled'] for t in teams)
total_all = sum(t['total'] for t in teams)

print(f"✅ Saved {len(teams)} teams to {DATA_FILE}")
print(f"   Total filled: {total_filled}")
print(f"   Total non-filled: {total_non_filled}")
print(f"   Total positions: {total_all}")
