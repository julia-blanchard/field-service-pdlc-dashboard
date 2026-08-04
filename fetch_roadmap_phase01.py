#!/usr/bin/env python3
"""
Fetch Phase 0/1 programs from GUS Roadmap (RDMP_Item__c)

Maps roadmap stages to PDLC phases:
- Phase 0 (PM Backlog): Items in "🌑 New" column
- Phase 1 (Prototyping): Items in "🟣 Exploration & Ideation" column

For ownership:
- If Product_Owner__c is set, use that person's details
- If Team__c is set but no Product Owner, use team's PM/Arch/TPM/UX leads
"""

import json
import subprocess
import sys
from typing import Dict, List, Optional

# Roadmap ID for Field Service Mobile
ROADMAP_ID = 'aIFEE0000001I7l4AE'

# Stage to Phase mapping
STAGE_PHASE_MAP = {
    '🌑 New': '0',
    '🟣 Exploration & Ideation': '1'
}

# Default leads by portfolio (fallback when Team doesn't specify)
# Sourced from Field Service UX team (Adrian Rapp) and Field Service Shared CX team (Rachelle Cohen)
DEFAULT_LEADS = {
    'Field Service Mobile': {
        'tpm': 'Julia Blanchard',
        'ux': 'Adrian Rapp',  # From Field Service UX team
        'cx': 'Rachelle Cohen'  # From Field Service Shared CX team
    },
    'Field Service Foundations': {
        'tpm': 'Julia Blanchard',
        'ux': 'Adrian Rapp',
        'cx': 'Rachelle Cohen'
    },
    'Field Service Scheduling & Optimization': {
        'tpm': 'Irit Gillath',
        'ux': 'Adrian Rapp',
        'cx': 'Rachelle Cohen'
    },
    'Field Service': {  # Generic fallback
        'tpm': 'Julia Blanchard',
        'ux': 'Adrian Rapp',
        'cx': 'Rachelle Cohen'
    }
}


def get_field_service_team_leads() -> Dict[str, str]:
    """Query Field Service UX and CX teams to get current leads"""

    # Query UX team
    ux_query = """
        SELECT Product_Owner__r.Name
        FROM ADM_Scrum_Team__c
        WHERE Name = 'Field Service UX'
    """
    ux_result = run_sf_query(ux_query)
    ux_lead = 'Adrian Rapp'  # Fallback
    if ux_result.get('records'):
        ux_po = ux_result['records'][0].get('Product_Owner__r')
        if ux_po:
            ux_lead = ux_po.get('Name', ux_lead)

    # Query CX team
    cx_query = """
        SELECT Product_Owner__r.Name
        FROM ADM_Scrum_Team__c
        WHERE Name = 'Field Service Shared CX'
    """
    cx_result = run_sf_query(cx_query)
    cx_lead = 'Rachelle Cohen'  # Fallback
    if cx_result.get('records'):
        cx_po = cx_result['records'][0].get('Product_Owner__r')
        if cx_po:
            cx_lead = cx_po.get('Name', cx_lead)

    return {'ux': ux_lead, 'cx': cx_lead}


def run_sf_query(query: str, org: str = 'org62') -> Dict:
    """Execute Salesforce CLI query and return JSON result"""
    try:
        result = subprocess.run(
            ['sf', 'data', 'query', '-o', org, '--query', query, '--json'],
            capture_output=True,
            text=True
        )

        # Try to parse even if return code != 0, SF CLI can return data with error code
        data = json.loads(result.stdout)

        if result.returncode != 0:
            print(f"SF CLI warning (code {result.returncode}): {result.stderr}", file=sys.stderr)
            print(f"Response status: {data.get('status')}", file=sys.stderr)
            print(f"Response message: {data.get('message', 'none')}", file=sys.stderr)

        if data.get('status') == 0:
            return data.get('result', {})
        else:
            print(f"Query failed status {data.get('status')}: {data.get('message', 'Unknown error')}", file=sys.stderr)
            return {}
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}", file=sys.stderr)
        print(f"Raw output: {result.stdout[:500]}", file=sys.stderr)
        return {}


def fetch_roadmap_items() -> List[Dict]:
    """Fetch all roadmap items from GUS"""
    query = (
        f"SELECT Id, Name, Title__c, Description__c, Status__c, "
        f"Roadmap_Column__r.Name, Roadmap_Column__r.Order__c, "
        f"Product_Owner__r.Name, Team__r.Name, "
        f"Team__r.Product_Owner__r.Name, Team__r.Supporting_Architect__r.Name, "
        f"Health__c, Health_Comments__c, T_Shirt_Size__c, "
        f"Target_Release__c, Target_Release_Date__c, Launch_Tier__c, "
        f"Start_Date__c, End_Date__c, Business_Value__c, "
        f"Executive_Sponsor__c, Slack_Channel__c, "
        f"Progress__c, Progress_Type__c, "
        f"Risks_and_Dependencies__c, Release_Type__c, "
        f"Total_Estimated_HC__c, New_SKU__c "
        f"FROM RDMP_Item__c "
        f"WHERE Roadmap__c = '{ROADMAP_ID}' "
        f"ORDER BY Roadmap_Column__r.Order__c, Title__c"
    )

    print(f"DEBUG: Running query: {query[:100]}...", file=sys.stderr)
    result = run_sf_query(query)
    print(f"DEBUG: Got result with {len(result.get('records', []))} records", file=sys.stderr)
    return result.get('records', [])


def map_to_phase_program(item: Dict) -> Optional[Dict]:
    """Map a roadmap item to Phase 0/1 program structure"""

    # Get stage/column name
    stage_name = item.get('Roadmap_Column__r', {}).get('Name', '')

    # Only process items in Phase 0 or Phase 1 stages
    phase = STAGE_PHASE_MAP.get(stage_name)
    if not phase:
        return None

    # Get title
    title = item.get('Title__c', '').strip()
    if not title:
        return None

    # Determine ownership
    pm_lead = None
    arch_lead = None
    portfolio = None

    # Priority 1: Direct Product Owner
    product_owner = item.get('Product_Owner__r')
    if product_owner:
        pm_lead = product_owner.get('Name', '')

    # Priority 2: Team leads
    team = item.get('Team__r')
    if team:
        portfolio = team.get('Name', '')

        # Only use team leads if no direct Product Owner
        if not pm_lead:
            team_po = team.get('Product_Owner__r')
            if team_po:
                pm_lead = team_po.get('Name', '')

        team_arch = team.get('Supporting_Architect__r')
        if team_arch:
            arch_lead = team_arch.get('Name', '')

    # Apply default leads by portfolio for missing roles
    portfolio_key = portfolio or 'Field Service'
    defaults = DEFAULT_LEADS.get(portfolio_key, DEFAULT_LEADS['Field Service'])

    tpm_lead = defaults.get('tpm', '')
    ux_lead = defaults.get('ux', '')
    cx_lead = defaults.get('cx', '')

    # Format dates nicely
    def format_date(date_str):
        if not date_str:
            return ''
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
            return dt.strftime('%b %d, %Y')
        except:
            return date_str

    # Build program dict with ALL the rich roadmap data
    program = {
        # Core identification
        'id': item.get('Id'),
        'name': item.get('Name'),  # RMI-00043530
        'feature': title,
        'phase': phase,
        'stage': stage_name,

        # Status & Health
        'status': item.get('Status__c', ''),
        'health': item.get('Health__c', ''),
        'health_comments': item.get('Health_Comments__c', ''),
        'progress': item.get('Progress__c', ''),
        'progress_type': item.get('Progress_Type__c', ''),

        # Team & Portfolio
        'portfolio': portfolio or 'Field Service',
        'pm_lead': pm_lead or '',
        'arch_lead': arch_lead or '',
        'tpm_lead': tpm_lead,
        'ux_lead': ux_lead,
        'cx_lead': cx_lead,

        # Timeline & Release
        'target_release': item.get('Target_Release__c', ''),
        'target_release_date': format_date(item.get('Target_Release_Date__c')),
        'start_date': format_date(item.get('Start_Date__c')),
        'end_date': format_date(item.get('End_Date__c')),

        # Sizing & Estimation
        't_shirt_size': item.get('T_Shirt_Size__c', ''),
        'estimated_hc': item.get('Total_Estimated_HC__c', ''),

        # Business Context
        'business_value': item.get('Business_Value__c', ''),
        'launch_tier': item.get('Launch_Tier__c', ''),
        'release_type': item.get('Release_Type__c', ''),
        'executive_sponsor': item.get('Executive_Sponsor__c', ''),
        'new_sku': item.get('New_SKU__c', ''),

        # Collaboration
        'slack_channel': item.get('Slack_Channel__c', ''),
        'risks_and_dependencies': item.get('Risks_and_Dependencies__c', ''),

        # Rich Content
        'description': item.get('Description__c', ''),

        # Metadata
        'source': 'gus_roadmap',
        'roadmap_id': ROADMAP_ID
    }

    return program


def main():
    """Main execution"""
    print(f"Fetching roadmap items from GUS roadmap {ROADMAP_ID}...")

    # Get current UX/CX leads from team records
    print("Querying Field Service team leads...")
    team_leads = get_field_service_team_leads()
    print(f"  UX Lead: {team_leads['ux']}")
    print(f"  CX Lead: {team_leads['cx']}")

    # Update defaults with queried leads
    for portfolio_leads in DEFAULT_LEADS.values():
        portfolio_leads['ux'] = team_leads['ux']
        portfolio_leads['cx'] = team_leads['cx']

    items = fetch_roadmap_items()
    if not items:
        print("No roadmap items found!", file=sys.stderr)
        sys.exit(1)

    print(f"Retrieved {len(items)} total roadmap items")

    # Map to Phase 0/1 programs
    phase0_programs = []
    phase1_programs = []

    for item in items:
        program = map_to_phase_program(item)
        if program:
            if program['phase'] == '0':
                phase0_programs.append(program)
            elif program['phase'] == '1':
                phase1_programs.append(program)

    print(f"Mapped {len(phase0_programs)} Phase 0 programs (NEW)")
    print(f"Mapped {len(phase1_programs)} Phase 1 programs (Exploration & Ideation)")

    # Save to JSON files
    output_data = {
        'phase_0': phase0_programs,
        'phase_1': phase1_programs,
        'total_items': len(items),
        'phase_0_count': len(phase0_programs),
        'phase_1_count': len(phase1_programs),
        'last_updated': subprocess.run(
            ['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'],
            capture_output=True,
            text=True
        ).stdout.strip()
    }

    # Write combined file
    with open('data/roadmap_phase01.json', 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved to data/roadmap_phase01.json")
    print(f"  Phase 0: {len(phase0_programs)} programs")
    print(f"  Phase 1: {len(phase1_programs)} programs")

    return 0


if __name__ == '__main__':
    sys.exit(main())
