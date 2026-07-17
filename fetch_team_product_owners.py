#!/usr/bin/env python3
"""
Fetch Product Owner mapping from GUS ADM_Scrum_Team__c
Creates a mapping of Team Name → Product Owner Name
"""

import json
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data" / "team_product_owners.json"
TARGET_ORG = "org62"

def fetch_team_product_owners():
    """Query ADM_Scrum_Team__c for teams and their Product Owners and Dev Leads (Engineering Manager or Scrum Master)"""
    print("🔄 Fetching team Product Owners and Dev Leads from GUS...")

    query = """
    SELECT Name, Product_Owner__r.Name, Engineering_Manager__r.Name, Scrum_Master__r.Name
    FROM ADM_Scrum_Team__c
    WHERE (Name LIKE 'FSL%' OR Name LIKE 'SFS%')
    ORDER BY Name
    """

    result = subprocess.run(
        ['sf', 'data', 'query', '--query', query,
         '--target-org', TARGET_ORG, '--json'],
        capture_output=True, text=True, check=True
    )

    data = json.loads(result.stdout)
    records = data.get('result', {}).get('records', [])

    # Build team → Product Owner and Dev Lead mappings
    team_po_map = {}
    team_dev_lead_map = {}

    for record in records:
        team_name = record.get('Name', '')

        # Handle null values safely
        po_ref = record.get('Product_Owner__r')
        po_name = po_ref.get('Name', '') if po_ref else ''

        em_ref = record.get('Engineering_Manager__r')
        em_name = em_ref.get('Name', '') if em_ref else ''

        sm_ref = record.get('Scrum_Master__r')
        sm_name = sm_ref.get('Name', '') if sm_ref else ''

        # Use Engineering Manager as primary, fallback to Scrum Master if no EM
        dev_lead_name = em_name if em_name else sm_name

        if team_name:
            if po_name:
                team_po_map[team_name] = po_name
            if dev_lead_name:
                team_dev_lead_map[team_name] = dev_lead_name

    print(f"✅ Found {len(team_po_map)} teams with Product Owners")
    print(f"✅ Found {len(team_dev_lead_map)} teams with Dev Leads (EM or Scrum Master)")
    return team_po_map, team_dev_lead_map

def main():
    team_po_map, team_dev_lead_map = fetch_team_product_owners()

    # Save to JSON
    output = {
        'team_product_owners': team_po_map,
        'team_dev_leads': team_dev_lead_map,
        'last_updated': subprocess.run(
            ['date', '+%Y-%m-%d %H:%M:%S'],
            capture_output=True, text=True
        ).stdout.strip()
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(output, indent=2))

    print(f"💾 Saved team→Product Owner and Dev Lead mappings to {DATA_FILE}")
    print(f"\nSample Product Owner mappings:")
    for team, po in list(team_po_map.items())[:3]:
        print(f"  {team} → PO: {po}")
    print(f"\nSample Dev Lead mappings:")
    for team, dev_lead in list(team_dev_lead_map.items())[:3]:
        print(f"  {team} → Dev Lead: {dev_lead}")

if __name__ == '__main__':
    main()
