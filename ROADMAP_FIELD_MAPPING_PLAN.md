# GUS Roadmap Field Mapping & Gap Analysis

**Date**: 2026-07-31  
**Purpose**: Plan for handling missing/incomplete data when migrating from Google Sheet to GUS Roadmap

---

## Current State

### ✅ Fields Available on RDMP_Item__c (Roadmap Items)

| Field | Source | Notes |
|-------|--------|-------|
| `Title__c` | Direct | Feature name |
| `Description__c` | Direct | Rich description |
| `Status__c` | Direct | Current status |
| `Health__c` | Direct | Health indicator |
| `Health_Comments__c` | Direct | Latest health notes |
| `Product_Owner__c` | Direct | Direct PM assignment |
| `Team__c` → `Product_Owner__r.Name` | Team lookup | Fallback PM from team |
| `Team__c` → `Supporting_Architect__r.Name` | Team lookup | Architect from team |
| `Target_Release__c` | Direct | Target release number |
| `T_Shirt_Size__c` | Direct | Size estimate |
| `Launch_Tier__c` | Direct | Launch tier classification |
| `Roadmap_Column__r.Name` | Relationship | Stage name (maps to phase) |

### ❌ Fields Missing on RDMP_Item__c

| Field Needed | Current Workaround | Proposed Solution |
|--------------|-------------------|-------------------|
| **TPM Lead** | ❌ No field on Team | Add custom field `Team__c.TPM__c` |
| **UX Lead** | ❌ No field on Team | Add custom field `Team__c.UX_Lead__c` |
| **CX Lead** | ❌ No field on Team | Add custom field `Team__c.CX_Lead__c` |
| **Portfolio** | ✅ Using `Team__r.Name` | Current approach works |
| **Subcolumn** (Phase 1) | ❌ N/A | Derive from `Roadmap_Column__r.Name` |

---

## 🔄 Roadmap Item → Program/Project Conversion

### What You Found
> "I see that you can connect a project but not convert the item itself to a project."

This means:
- **No automatic conversion**: Roadmap items stay as RDMP_Item__c records
- **Manual process**: Teams create ADM_Product_Tag__c (Program) separately
- **Potential link**: May be able to reference roadmap item from program (need to verify field)

### Proposed Workflow Options

#### **Option A: Roadmap Items Stay as Phase 0/1 Only**
```
Roadmap Item (RDMP_Item__c)  →  Manual creation  →  Program (ADM_Product_Tag__c)
     [Phase 0/1 view]                                  [Phase 2/3 execution tracking]
```

**Pros**: Clean separation, no duplicate tracking  
**Cons**: Manual handoff, potential for items to get lost

#### **Option B: Add Linkage Field**
Add custom field on ADM_Product_Tag__c:
- `Roadmap_Item__c` (lookup to RDMP_Item__c)
- Shows "Originated from Roadmap Item RMI-00043530"
- Fetch script can check if roadmap item already has a program

**Pros**: Traceability, prevents duplicates  
**Cons**: Requires custom field creation

#### **Option C: Promote with Metadata Copy**
Create a "Promote to Program" button/automation:
1. Creates ADM_Product_Tag__c from RDMP_Item__c data
2. Copies: Title, Description, Owner, Health, Target Release
3. Links back to original roadmap item
4. Moves roadmap item to "Promoted" column

**Pros**: Semi-automated, preserves history  
**Cons**: Requires Flow/Apex development

---

## 📋 Field Mapping Strategy

### Strategy 1: Enhance RDMP_Item__c (Minimal GUS Changes)

Add custom fields directly to roadmap items:
```
RDMP_Item__c additions:
- UX_Lead__c (User lookup)
- CX_Lead__c (User lookup)  
- TPM_Lead__c (User lookup)
```

**Timeline**: ~1-2 weeks (SF admin + testing)  
**Impact**: Roadmap items become more complete, no workarounds needed

### Strategy 2: Enhance Team Object (Scalable)

Add fields to ADM_Scrum_Team__c:
```
ADM_Scrum_Team__c additions:
- TPM__c (User lookup)
- UX_Lead__c (User lookup)
- CX_Lead__c (User lookup)
```

**Timeline**: ~1-2 weeks (SF admin + testing)  
**Impact**: Benefits ALL roadmap items + programs using that team  
**Recommended**: ✅ This scales better

### Strategy 3: Hybrid - Use Defaults for Missing Data

Keep current fields, provide fallback values:
```python
# In fetch_roadmap_phase01.py
DEFAULT_LEADS = {
    'Field Service Mobile': {
        'tpm': 'Julia Blanchard',
        'ux': 'TBD',
        'cx': 'TBD'
    },
    'Field Service Foundations': {
        'tpm': 'TBD',
        'ux': 'TBD', 
        'cx': 'TBD'
    }
}

# Fall back to portfolio defaults if team leads not set
if not tpm_lead:
    tpm_lead = DEFAULT_LEADS.get(portfolio, {}).get('tpm', '')
```

**Timeline**: Immediate (code-only)  
**Impact**: Quick fix, but data not in GUS  
**Use Case**: Temporary until Strategy 2 implemented

---

## 🎯 Recommended Approach

### Phase 1: Immediate (This Week)
1. ✅ **Use Strategy 3 (Defaults)** for missing TPM/UX/CX leads
2. ✅ **Add portfolio mapping** based on Team__c
3. ✅ **Document which roadmap items lack ownership** in weekly report

### Phase 2: Short-term (Next Sprint)
1. **Work with SF Admin** to add `TPM__c`, `UX_Lead__c`, `CX_Lead__c` to ADM_Scrum_Team__c
2. **Backfill existing teams** with current lead assignments
3. **Update fetch script** to use new fields when available

### Phase 3: Medium-term (Next Month)
1. **Evaluate Program linkage**: Test adding `Roadmap_Item__c` lookup on ADM_Product_Tag__c
2. **Build "Promote to Program"** automation if valuable
3. **Migrate Google Sheet items** into GUS Roadmap for single source of truth

### Phase 4: Long-term (Next Quarter)
1. **Deprecate Google Sheet** for Phase 0/1 tracking
2. **Train team** on using Roadmap columns directly in GUS
3. **Add automation** to update dashboard when roadmap items move columns

---

## 📊 Field Completeness Report

Run this query to see current data completeness:

```sql
SELECT 
    COUNT(*) as Total_Items,
    COUNT(Product_Owner__c) as Has_PM,
    COUNT(Team__c) as Has_Team,
    COUNT(Health__c) as Has_Health,
    COUNT(Target_Release__c) as Has_Release,
    COUNT(T_Shirt_Size__c) as Has_Size
FROM RDMP_Item__c
WHERE Roadmap__c = 'aIFEE0000001I7l4AE'
    AND Roadmap_Column__r.Name IN ('🌑 New', '🟣 Exploration & Ideation')
```

Expected output shows % of items with each field populated.

---

## 🚀 Next Steps

**For Julia to decide:**

1. **TPM/UX/CX Leads**: 
   - [ ] Live with defaults for now?
   - [ ] Request SF admin to add fields to Team object?
   - [ ] Manually maintain mapping file?

2. **Roadmap → Program Conversion**:
   - [ ] Keep manual (teams create programs themselves)?
   - [ ] Build "Promote" button/automation?
   - [ ] Just use linkage field for traceability?

3. **Google Sheet Sunset**:
   - [ ] When to stop maintaining the sheet?
   - [ ] Migrate existing sheet items to roadmap?
   - [ ] Keep sheet for non-roadmap brainstorming?

**Recommendation**: Start with Phase 1 (defaults), then work with admin on Phase 2 (Team fields) for a sustainable long-term solution.
