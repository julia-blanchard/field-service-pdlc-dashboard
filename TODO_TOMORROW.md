# TODO - July 17, 2026

## 1. Phase 2 Card Font Weight
**Location:** Overview tab, Phase 2 "In Progress" column
**Change:** Reduce font weight from 700 to 600 for cards sourced from GUS query

**Files:**
- `templates/field_service_dynamic.html` - Find Phase 2 card styles in Overview section

---

## 2. Allocations Tab - Program Styling & Links
**Location:** Allocations tab, team rows

### 2a. Program Font Color
**Change:** Update program color to blue (#2563eb) to match Overview tab styling

**Current:** Grey color for portfolio badges under team names
**New:** Blue color (#2563eb) for program names

### 2b. Program Links to GUS
**Change:** Make program names clickable links to their GUS records

**Implementation:** Add `<a href="https://gus.lightning.force.com/lightning/r/...">` wrapper around program names

### 2c. Remove Portfolio Column
**Change:** Remove the "PORTFOLIOS" column from the allocations table at team view

**Current:** Table has columns: TEAM | PORTFOLIOS | HEADCOUNT | JUNE | JULY | AUG | SEPT
**New:** Table has columns: TEAM | HEADCOUNT | JUNE | JULY | AUG | SEPT

### 2d. Portfolio Inline with Program (Expanded View)
**Change:** When team is expanded to show program breakdowns, display portfolio inline to the right of program name (like Service Cloud)

**Current Structure (Expanded):**
```
▾ FSL - Asset - 360
    264 Scheduling Flows
    Unmapped
```

**New Structure (Expanded):**
```
▾ FSL - Asset - 360
    264 Scheduling Flows          264 Field Service Foundations
    Unmapped                       [no portfolio]
```

**Implementation Notes:**
- Program name stays left-aligned and indented
- Portfolio name appears to the right on the same line
- Portfolio should be in lighter/secondary color (similar to Service Cloud styling)
- Use epic → project → program → portfolio relationship from execution_data.json

**Files:**
- `templates/field_service_dynamic.html` - Lines ~14470-14543 (allocations table)
- May need to update `app.py` to pass program → portfolio mapping to template

---

## 3. Other Issues to Address
- [ ] Fix broken logo in top-left corner on GitHub Pages
- [ ] Investigate what's overwriting teams_data.json and add safeguards

---

## Reference
- Service Cloud dashboard: https://sc-adlc-ca7d6c0714fd.herokuapp.com/
- Field Service localhost: http://localhost:5002
- Field Service GitHub Pages: https://julia-blanchard.github.io/field-service-pdlc-dashboard/
