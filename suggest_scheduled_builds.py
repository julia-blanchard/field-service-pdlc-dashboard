#!/usr/bin/env python3
"""
Suggest scheduled builds for epics missing one, based on their stories' builds.

Read-only prototype: queries ADM_Work__c for each epic flagged with
missing_scheduled_build in hygiene_issues.json, takes the majority
Scheduled_Build__r.Name across its stories, and writes suggestions to
data/scheduled_build_suggestions.json. Nothing is written back to GUS.
"""

import json
import re
import subprocess
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).parent
HYGIENE_FILE = SCRIPT_DIR / 'data' / 'hygiene_issues.json'
OUTPUT_FILE = SCRIPT_DIR / 'data' / 'scheduled_build_suggestions.json'
TARGET_ORG = 'org62'
BATCH_SIZE = 50
MAJORITY_THRESHOLD = 0.7

# GUS has placeholder ADM_Build__c records ("orgfarm", "None", etc.) that
# aren't real releases -- a real build name always carries a release number.
RELEASE_NUMBER_RE = re.compile(r'\d{3}')


def run_soql(query):
    result = subprocess.run(
        ['sf', 'data', 'query', '--target-org', TARGET_ORG,
         '--query', query, '--json'],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    return data.get('result', {}).get('records', [])


def fetch_story_builds(epic_ids):
    """
    Query ADM_Work__c for stories under these epics, grouped by epic.
    Returns {epic_id: {'builds': [...], 'total_stories': N}} -- builds only
    includes real release builds (has a release number); total_stories
    counts every story regardless of whether a build is set, so the
    majority ratio reflects true coverage, not just populated stories.
    """
    stories_by_epic = {epic_id: {'builds': [], 'total_stories': 0} for epic_id in epic_ids}

    for i in range(0, len(epic_ids), BATCH_SIZE):
        batch = epic_ids[i:i + BATCH_SIZE]
        ids_str = "', '".join(batch)
        query = f"""
        SELECT Epic__c, Scheduled_Build__c, Scheduled_Build__r.Name
        FROM ADM_Work__c
        WHERE Epic__c IN ('{ids_str}')
        """
        records = run_soql(query)
        for record in records:
            epic_id = record.get('Epic__c')
            if epic_id not in stories_by_epic:
                continue

            stories_by_epic[epic_id]['total_stories'] += 1

            build_id = record.get('Scheduled_Build__c')
            build_rel = record.get('Scheduled_Build__r')
            build_name = build_rel.get('Name') if build_rel else None
            if build_id and build_name and RELEASE_NUMBER_RE.search(build_name):
                stories_by_epic[epic_id]['builds'].append((build_id, build_name))

        print(f"  Queried {min(i + BATCH_SIZE, len(epic_ids))}/{len(epic_ids)} epics' stories...")

    return stories_by_epic


def suggest_build(builds, total_stories):
    """
    Majority-vote a suggested build. Ratio is matching-builds / ALL stories
    on the epic (not just stories that have a build set), so an epic where
    most stories simply have no build assigned won't look confidently
    resolved.
    """
    if not builds or not total_stories:
        return None

    counts = Counter(builds)
    (top_build_id, top_build_name), top_count = counts.most_common(1)[0]
    ratio = top_count / total_stories

    if ratio < MAJORITY_THRESHOLD:
        return None

    return {
        'suggested_build': top_build_name,
        'suggested_build_id': top_build_id,
        'matching_stories': top_count,
        'total_stories': total_stories,
        'ratio': round(ratio, 2)
    }


def main():
    print("Loading hygiene issues...")
    with open(HYGIENE_FILE, 'r') as f:
        hygiene_data = json.load(f)

    missing_build_epics = [
        e for e in hygiene_data['epics']
        if 'missing_scheduled_build' in e.get('issues', []) and e.get('epic_id')
    ]
    epic_ids = [e['epic_id'] for e in missing_build_epics]

    print(f"Found {len(epic_ids)} epics missing scheduled build")
    print("Fetching story builds from GUS...")
    stories_by_epic = fetch_story_builds(epic_ids)

    suggestions = []
    no_stories = 0
    no_majority = 0

    for epic in missing_build_epics:
        info = stories_by_epic.get(epic['epic_id'], {'builds': [], 'total_stories': 0})
        if not info['total_stories']:
            no_stories += 1
            continue

        suggestion = suggest_build(info['builds'], info['total_stories'])
        if not suggestion:
            no_majority += 1
            continue

        suggestions.append({
            'epic_id': epic['epic_id'],
            'epic_name': epic['epic_name'],
            'epic_name_key': epic['epic_name_key'],
            'team': epic['team'],
            'owner': epic['owner'],
            'program': epic['program'],
            'project': epic['project'],
            **suggestion
        })

    output = {
        'total_epics_checked': len(epic_ids),
        'suggestions_found': len(suggestions),
        'no_stories_found': no_stories,
        'no_majority_build': no_majority,
        'majority_threshold': MAJORITY_THRESHOLD,
        'suggestions': suggestions
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Checked {len(epic_ids)} epics")
    print(f"   {len(suggestions)} suggestions found")
    print(f"   {no_stories} had no stories with a scheduled build")
    print(f"   {no_majority} had no build reaching the {MAJORITY_THRESHOLD:.0%} majority threshold")
    print(f"\nSaved to {OUTPUT_FILE}")

    print("\nSample suggestions:")
    for s in suggestions[:10]:
        print(f"  {s['epic_name'][:55]:<55} -> {s['suggested_build']} "
              f"({s['matching_stories']}/{s['total_stories']} stories)")


if __name__ == '__main__':
    main()
