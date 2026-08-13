#!/usr/bin/env python3
"""
Test script to show how we'd fetch Phase 0/1 data from GUS instead of Google Sheets.

Proposed Structure:
  Portfolio (Pillar Backlog) - exists as PPM_Portfolio__c
    └─ Program (Major Investment - PBD holder) - PPM_Program__c with Google_Doc_URL__c
        └─ Project (Prototype/Feature) - PPM_Project__c
            └─ Epic - ADM_Epic__c (work items)
"""
import subprocess
import json

def run_soql(query):
    """Execute SOQL via sf CLI"""
    try:
        result = subprocess.run(
            ['sf', 'data', 'query', '--query', query, '--json', '--target-org', 'org62'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        return data.get('result', {}).get('records', [])
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

print("🔍 Testing GUS-based PDLC structure")
print("=" * 60)

# Query: Get Programs with Google Doc URLs (PBD holders)
print("\n📋 Programs with PBD URLs:\n")
programs_query = """
SELECT Id, Name, Portfolio__r.Name, Google_Doc_URL__c,
       Program_Manager__r.Name, Engineering_Lead__r.Name,
       Program_Health__c
FROM PPM_Program__c
WHERE Google_Doc_URL__c != null
  AND Portfolio__r.Name LIKE '%Field Service%'
LIMIT 5
"""

programs = run_soql(programs_query)
for prog in programs:
    print(f"✅ {prog.get('Name')}")
    print(f"   Portfolio: {prog.get('Portfolio__r', {}).get('Name')}")
    print(f"   PM: {prog.get('Program_Manager__r', {}).get('Name', 'TBD')}")
    print(f"   PBD: {prog.get('Google_Doc_URL__c', '')[:60]}...")
    print()

# Query: Get Projects under a specific Program
if programs:
    prog_id = programs[0].get('Id')
    print(f"\n📦 Projects under '{programs[0].get('Name')}':\n")

    projects_query = f"""
    SELECT Id, Name, Project_Manager__r.Name
    FROM PPM_Project__c
    WHERE Program__c = '{prog_id}'
    LIMIT 5
    """

    projects = run_soql(projects_query)
    if projects:
        for proj in projects:
            print(f"   → {proj.get('Name')}")
            print(f"      PM: {proj.get('Project_Manager__r', {}).get('Name', 'TBD')}")
    else:
        print("   (No projects found)")

print("\n" + "=" * 60)
print("\n💡 Proposed Workflow:")
print("1. Create a Portfolio for each Pillar's Backlog (Mobile, AGX, WFM, etc.)")
print("2. Programs are the Major Investment Areas with PBDs")
print("3. Projects are the Prototypes/Features")
print("4. We fetch from GUS instead of Google Sheets")
print("5. Google_Doc_URL__c on Program can hold multiple labeled URLs:")
print("   PBD: https://...")
print("   HLD: https://...")
print("   PRD: https://...")
