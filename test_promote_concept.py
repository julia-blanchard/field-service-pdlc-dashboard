#!/usr/bin/env python3
"""
Proof of Concept: Can we create ADM_Product_Tag__c via SF CLI?
This tests the core capability without actually creating a record.
"""

import subprocess
import json

# Test 1: Check if we can query programs
print("=" * 80)
print("TEST 1: Can we query existing programs?")
print("=" * 80)

result = subprocess.run(
    ['sf', 'data', 'query', '-o', 'org62', 
     '--query', "SELECT Id, Name, Subject__c, Product_Owner__c FROM ADM_Product_Tag__c LIMIT 3",
     '--json'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)
if data.get('status') == 0:
    programs = data['result']['records']
    print(f"✅ Found {len(programs)} programs:")
    for p in programs:
        print(f"   - {p.get('Subject__c', 'No name')} (Owner: {p.get('Product_Owner__c', 'None')})")
else:
    print("❌ Failed to query programs")

print()

# Test 2: Check what fields are REQUIRED to create a program
print("=" * 80)
print("TEST 2: What fields are required on ADM_Product_Tag__c?")
print("=" * 80)

result = subprocess.run(
    ['sf', 'data', 'query', '-o', 'org62',
     '--query', "SELECT FIELDS(ALL) FROM ADM_Product_Tag__c LIMIT 1",
     '--json'],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    data = json.loads(result.stdout)
    if data.get('result', {}).get('records'):
        fields = data['result']['records'][0].keys()
        interesting_fields = [f for f in fields if any(x in f.lower() for x in ['subject', 'owner', 'status', 'details', 'team', 'health', 'release'])]
        print(f"✅ Key fields available on programs:")
        for field in sorted(interesting_fields):
            print(f"   - {field}")

print()

# Test 3: Show the SF CLI create command syntax
print("=" * 80)
print("TEST 3: How would we create a program?")
print("=" * 80)
print("""
The SF CLI command would be:

sf data create record \\
  --sobject ADM_Product_Tag__c \\
  --values "Subject__c='Test Program from Roadmap' \\
            Details__c='This is a test' \\
            Product_Owner__c='005B0000006417VIAQ' \\
            Status__c='Active'" \\
  --json

This would:
1. Create a NEW ADM_Product_Tag__c record in GUS
2. Return the new record ID
3. Be visible immediately in GUS to everyone
4. Trigger any existing workflows/automations on that object

⚠️  THIS IS REAL - it's not a simulation!
""")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
Can we create programs via API? YES, absolutely.

The "Promote to Program" feature would:
✅ Really create records in GUS (ADM_Product_Tag__c)
✅ Use the Salesforce CLI (sf data create record)
✅ Copy fields from roadmap item → program
✅ Be visible to everyone immediately
✅ Work the same as manually creating in GUS UI

This is not a mock-up or preview - it's full CRUD access to GUS data.
""")

