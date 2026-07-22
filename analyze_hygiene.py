#!/usr/bin/env python3
"""
Analyze execution data for GUS hygiene issues.
Identifies epics that need attention (missing fields, blocked status, etc.)
"""

import json
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
EXECUTION_FILE = SCRIPT_DIR / 'data' / 'execution_data.json'
OUTPUT_FILE = SCRIPT_DIR / 'data' / 'hygiene_issues.json'

def check_epic_hygiene(epic):
    """
    Check an epic for hygiene issues.
    Returns list of issue types found.
    """
    issues = []

    # Missing scheduled build (release month)
    if not epic.get('scheduled_build') or epic.get('scheduled_build') in ['-', '', 'null']:
        issues.append('missing_scheduled_build')

    # Missing priority
    if not epic.get('priority') or epic.get('priority') in ['-', '', 'null']:
        issues.append('missing_priority')

    # Missing owner
    if not epic.get('owner') or epic.get('owner') in ['-', '', 'Unknown']:
        issues.append('missing_owner')

    # Blocked or On Hold without health comments
    health = epic.get('health', '')
    comments = epic.get('health_comments', '')
    if health in ['Blocked', 'On Hold'] and (not comments or comments in ['-', '', 'null']):
        issues.append('blocked_no_comments')

    # Missing planned release
    if not epic.get('planned_release') or epic.get('planned_release') in ['-', '', 'null']:
        issues.append('missing_planned_release')

    return issues

def analyze_execution_data():
    """
    Analyze all epics in execution data for hygiene issues.
    """
    print("Loading execution data...")
    with open(EXECUTION_FILE, 'r') as f:
        execution_data = json.load(f)

    all_issues = []
    issue_counts = defaultdict(int)
    teams_affected = set()
    programs_affected = set()

    # Walk through all epics
    for program in execution_data.get('programs', []):
        program_name = program.get('name', '')
        portfolio = program.get('portfolio', '')

        for project in program.get('projects', []):
            project_name = project.get('name', '')

            for epic in project.get('epics', []):
                epic_issues = check_epic_hygiene(epic)

                if epic_issues:
                    # Track this epic's issues
                    # NOTE: epic.id is empty in report, so we use name as the key
                    epic_data = {
                        'epic_id': epic.get('id', ''),
                        'epic_name': epic.get('name', ''),
                        'epic_name_key': epic.get('name', '').strip(),  # Normalized name for matching
                        'team': epic.get('team', ''),
                        'owner': epic.get('owner', ''),
                        'health': epic.get('health', ''),
                        'scheduled_build': epic.get('scheduled_build', ''),
                        'priority': epic.get('priority', ''),
                        'story_points': epic.get('story_points', 0),
                        'program': program_name,
                        'portfolio': portfolio,
                        'project': project_name,
                        'issues': epic_issues
                    }
                    all_issues.append(epic_data)

                    # Track counts
                    for issue_type in epic_issues:
                        issue_counts[issue_type] += 1

                    teams_affected.add(epic.get('team', ''))
                    programs_affected.add(program_name)

    # Group by team
    by_team = defaultdict(list)
    for epic in all_issues:
        by_team[epic['team']].append(epic)

    # Convert to sorted list
    teams_list = [
        {
            'name': team,
            'epic_count': len(epics),
            'epics': epics
        }
        for team, epics in sorted(by_team.items())
    ]

    # Summary
    summary = {
        'total_epics_needing_attention': len(all_issues),
        'teams_affected': len(teams_affected),
        'programs_affected': len(programs_affected),
        'issue_breakdown': {
            'missing_scheduled_build': issue_counts['missing_scheduled_build'],
            'missing_priority': issue_counts['missing_priority'],
            'missing_owner': issue_counts['missing_owner'],
            'blocked_no_comments': issue_counts['blocked_no_comments'],
            'missing_planned_release': issue_counts['missing_planned_release']
        }
    }

    output = {
        'summary': summary,
        'epics': all_issues,
        'by_team': teams_list
    }

    # Save to file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Analyzed {len(execution_data.get('programs', []))} programs")
    print(f"   Found {len(all_issues)} epics needing attention")
    print(f"   {teams_affected} teams affected")
    print(f"\nIssue Breakdown:")
    for issue_type, count in issue_counts.items():
        print(f"   {issue_type}: {count}")
    print(f"\nSaved to {OUTPUT_FILE}")

if __name__ == '__main__':
    analyze_execution_data()
