#!/usr/bin/env python3
"""
Test fetching PBD URLs from GUS PPM_Program__c.Google_Doc_URL__c field
instead of Google Sheets
"""
import subprocess
import json

def run_soql(query):
    """Execute SOQL via sf CLI and return parsed results"""
    try:
        result = subprocess.run(
            ['sf', 'data', 'query', '--query', query, '--json', '--target-org', 'org62'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        return data.get('result', {}).get('records', [])
    except subprocess.CalledProcessError as e:
        print(f"❌ SOQL Error: {e.stderr}")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

# Test query: Find "Guided Experience" program with Google Doc URL
print("🔍 Searching for 'Guided Experience' program in GUS...")

query = """
    SELECT Id, Name, Google_Doc_URL__c, Program_Health__c,
           Program_Manager__r.Name, Engineering_Lead__r.Name,
           Portfolio__r.Name
    FROM PPM_Program__c
    WHERE Name LIKE '%Guided Experience%'
      AND Google_Doc_URL__c != null
    LIMIT 5
"""

programs = run_soql(query)

if programs:
    print(f"✅ Found {len(programs)} program(s):\n")
    for prog in programs:
        print(f"Name: {prog.get('Name')}")
        print(f"ID: {prog.get('Id')}")
        print(f"Google Doc URL: {prog.get('Google_Doc_URL__c')}")
        print(f"PM: {prog.get('Program_Manager__r', {}).get('Name', 'TBD')}")
        print(f"Portfolio: {prog.get('Portfolio__r', {}).get('Name', 'N/A')}")
        print()
else:
    print("❌ No programs found with 'Guided Experience' and a Google Doc URL")
    print("\n🔍 Let's search without the Google Doc URL requirement:")

    query2 = """
        SELECT Id, Name, Google_Doc_URL__c
        FROM PPM_Program__c
        WHERE Name LIKE '%Guided%'
        LIMIT 10
    """

    all_guided = run_soql(query2)
    if all_guided:
        print(f"✅ Found {len(all_guided)} program(s) with 'Guided' in name:")
        for prog in all_guided:
            print(f"  - {prog.get('Name')}: {prog.get('Google_Doc_URL__c') or '(no URL)'}")
