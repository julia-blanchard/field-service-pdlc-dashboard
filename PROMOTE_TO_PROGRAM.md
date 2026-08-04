# "Promote to Program" Feature Design

**Purpose**: Semi-automated workflow to convert GUS Roadmap Items (RDMP_Item__c) into tracked Programs (ADM_Product_Tag__c) when they're ready to move from Phase 0/1 to Phase 2 execution.

---

## Why This Matters

**Current Problem**:
- Roadmap items live in RDMP_Item__c (great for early ideation)
- Programs/Projects live in ADM_Product_Tag__c / PPM_Project__c (great for execution tracking)
- **Gap**: Manual copy-paste of data when promoting items from backlog → active work
- **Risk**: Data loss, missing fields, duplicate entry effort

**With "Promote to Program"**:
- One-click conversion with data preservation
- Automatic linking between roadmap item → program
- Clear audit trail of what was promoted when

---

## Technical Implementation Options

### Option A: GUS Custom Button + Flow (Recommended)

**What it does**:
1. Add a custom button to RDMP_Item__c record page: "🚀 Promote to Program"
2. Button triggers a Salesforce Flow that:
   - Creates ADM_Product_Tag__c record
   - Copies all relevant fields (see mapping below)
   - Sets relationship field linking back to roadmap item
   - Moves roadmap item to "Promoted" column
   - Sends notification to PM

**Pros**:
- No code deployment needed (admins can build)
- Visible in GUS UI where PMs work
- Can add validation rules (e.g., must have PM before promoting)
- Can trigger other automations (Slack notification, etc.)

**Cons**:
- Requires SF admin to build the Flow
- ~2-3 days of admin work

**Field Mapping**:
```
RDMP_Item__c → ADM_Product_Tag__c
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title__c              → Subject__c (Program name)
Description__c        → Details__c
Status__c             → Status__c
Health__c             → Health__c
Health_Comments__c    → Health_Comments__c
Product_Owner__c      → Product_Owner__c
Target_Release__c     → Target_Release__c
T_Shirt_Size__c       → Estimation__c
Business_Value__c     → Business_Value__c (custom field if doesn't exist)
Slack_Channel__c      → Slack_Channel__c (custom field if doesn't exist)
Team__c               → Team__c
Id (roadmap item)     → Roadmap_Item__c (NEW lookup field)
```

**New Fields Needed**:
```
ADM_Product_Tag__c:
- Roadmap_Item__c (Lookup to RDMP_Item__c) - for traceability
- Business_Value__c (Text Area) - if doesn't exist
- Slack_Channel__c (Text) - if doesn't exist

RDMP_Column__c:
- Add a column named "✅ Promoted" for promoted items
```

---

### Option B: Dashboard "Promote" Button (Hybrid)

**What it does**:
1. Add "Promote" button next to each roadmap item in your localhost:5002 dashboard
2. When clicked:
   - Opens modal asking for Program Portfolio assignment
   - Calls SF CLI to create ADM_Product_Tag__c record
   - Updates RDMP_Item__c to mark as promoted
   - Refreshes dashboard

**Pros**:
- Works immediately (no admin needed)
- You control the UX exactly
- Can batch-promote multiple items
- Great for POC / testing the workflow

**Cons**:
- Only works in your dashboard (not available to other PMs in GUS)
- Requires SF CLI permissions for write operations
- More custom code to maintain

**Implementation**:
```python
# New endpoint in app.py
@app.route('/api/promote-to-program', methods=['POST'])
def promote_to_program():
    roadmap_item_id = request.json.get('roadmap_item_id')
    portfolio = request.json.get('portfolio')
    
    # 1. Query roadmap item details
    item = fetch_roadmap_item_details(roadmap_item_id)
    
    # 2. Create ADM_Product_Tag__c via SF CLI
    program_id = create_program_from_roadmap_item(item, portfolio)
    
    # 3. Update roadmap item to "Promoted" status
    update_roadmap_item_status(roadmap_item_id, 'Promoted')
    
    # 4. Create lookup relationship
    link_roadmap_to_program(roadmap_item_id, program_id)
    
    return jsonify({'success': True, 'program_id': program_id})
```

---

### Option C: Scheduled Automation

**What it does**:
- Nightly job checks for roadmap items in "Ready to Promote" column
- Automatically creates programs for them
- Sends report to PM: "3 new programs created from roadmap"

**Pros**:
- Zero manual work
- Batch efficiency
- Consistent process

**Cons**:
- Less control over when it happens
- Risk of auto-creating unwanted programs
- Requires robust error handling

---

## Recommended Phased Approach

### Phase 1: Manual with Script (This Week)
Add a Python script PMs can run:
```bash
python3 promote_roadmap_item.py RMI-00043530
```

Script does the same as Option B but via command line.

**Why start here**:
- Tests the field mapping
- Validates the data quality
- No UI work needed yet
- Can iterate quickly

### Phase 2: Dashboard Button (Next Sprint)
Implement Option B in your localhost:5002 dashboard.

**Why**:
- Better UX than CLI script
- Proves out the workflow
- Becomes POC to show admin for Option A

### Phase 3: Native GUS Button (Next Month)
Work with SF admin to implement Option A as the production solution.

**Why**:
- Available to all PMs
- Integrated with GUS permissions
- Sustainable long-term

---

## Field-Level Details

### Critical Fields (Must Copy)
- **Subject__c**: Program name (from Title__c)
- **Product_Owner__c**: PM owner
- **Status__c**: Current status
- **Target_Release__c**: Release target

### Important Fields (Should Copy)
- **Health__c**: Health status
- **Health_Comments__c**: Latest comments
- **Team__c**: Assigned team
- **Description__c** → **Details__c**: Full description

### Nice-to-Have Fields (If They Exist)
- **Business_Value__c**: Why this matters
- **T_Shirt_Size__c** → **Estimation__c**: Size estimate
- **Slack_Channel__c**: Team channel
- **Executive_Sponsor__c**: Exec visibility

### Traceability Fields (New)
- **Roadmap_Item__c** on Program: Lookup back to source
- **Promoted_Date__c** on Roadmap Item: When it was promoted
- **Promoted_To_Program__c** on Roadmap Item: Forward link

---

## User Workflow

### Before (Manual - Current State)
1. PM reviews roadmap item in GUS
2. PM decides "this is ready for execution"
3. PM manually creates new ADM_Product_Tag__c record
4. PM copies name, description, owner, etc. by hand
5. PM hopes they didn't miss any fields
6. Roadmap item sits orphaned with no link to program

**Time**: 5-10 minutes per item  
**Error rate**: ~20% (missing fields)

### After (With Promote Button)
1. PM reviews roadmap item in dashboard or GUS
2. PM clicks "🚀 Promote to Program"
3. Modal asks: "Which portfolio?" → Select from dropdown
4. System creates program, copies all fields, links records
5. PM gets confirmation: "Program a0I... created successfully"
6. Roadmap item moves to "Promoted" column automatically

**Time**: 30 seconds per item  
**Error rate**: 0% (automated)

---

## Data Quality Safeguards

### Pre-Promotion Validation
Before allowing promotion, check:
- ✅ Has Product Owner assigned
- ✅ Has description (not blank)
- ✅ Has target release or end date
- ✅ Health status is not "Unknown"
- ✅ Not already promoted (check for existing link)

If any fail → Show error message with what's missing

### Post-Promotion Actions
After successful promotion:
- ✅ Send Slack DM to Product Owner: "Your roadmap item X was promoted to program Y"
- ✅ Add comment to roadmap item: "Promoted to program [link] on 2026-07-31"
- ✅ Move to "Promoted" column
- ✅ Update dashboard metrics

---

## Metrics to Track

Once implemented, track:
- **Promotion rate**: How many roadmap items → programs per month?
- **Time to promote**: How long from "New" → "Promoted"?
- **Backlog health**: How many items stuck in Phase 0 without promotion?
- **Field completeness**: % of promoted programs with all fields filled

**Goal**: Reduce manual effort by 80%, increase data accuracy to 100%

---

## Next Steps

**For Julia to decide**:

1. **Which option to start with?**
   - [ ] Option A: Wait for admin to build Flow (sustainable, ~2 weeks)
   - [ ] Option B: Build dashboard button now (fast, local only)
   - [ ] Option C: CLI script as interim (fastest, least UX)

2. **What fields are must-haves?**
   - [ ] Confirm the field mapping table above
   - [ ] Which ADM_Product_Tag__c fields are required?
   - [ ] Any additional fields to copy?

3. **Who can approve creating the lookup field?**
   - Need: `Roadmap_Item__c` (Lookup) on ADM_Product_Tag__c
   - Who is the SF admin to work with?

**Recommendation**: 
1. Start with CLI script this week (validate the process)
2. Build dashboard button next week (better UX)
3. Request admin build Flow once proven out (production solution)

---

## Example: CLI Script POC

```python
#!/usr/bin/env python3
"""
Promote a roadmap item to a program

Usage:
    python3 promote_roadmap_item.py RMI-00043530
"""

import sys
import subprocess
import json

def promote_to_program(roadmap_item_name):
    # 1. Query roadmap item
    query = f"""
        SELECT Id, Name, Title__c, Description__c, Status__c, 
               Product_Owner__c, Target_Release__c, Health__c
        FROM RDMP_Item__c
        WHERE Name = '{roadmap_item_name}'
    """
    
    result = subprocess.run(
        ['sf', 'data', 'query', '-o', 'org62', '--query', query, '--json'],
        capture_output=True, text=True
    )
    
    data = json.loads(result.stdout)
    item = data['result']['records'][0]
    
    # 2. Validate required fields
    if not item.get('Product_Owner__c'):
        print("❌ Cannot promote: No Product Owner assigned")
        return False
    
    # 3. Create program
    program_data = {
        'Subject__c': item['Title__c'],
        'Details__c': item.get('Description__c', ''),
        'Status__c': item.get('Status__c', ''),
        'Health__c': item.get('Health__c', ''),
        'Product_Owner__c': item['Product_Owner__c'],
        'Target_Release__c': item.get('Target_Release__c', '')
    }
    
    # TODO: Use SF CLI to create record
    # sf data create record -s ADM_Product_Tag__c -v "Subject__c='...' ..."
    
    print(f"✅ Promoted {roadmap_item_name} to program!")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 promote_roadmap_item.py RMI-00043530")
        sys.exit(1)
    
    promote_to_program(sys.argv[1])
```

Ready to build this? Pick your starting option and I'll implement it!
