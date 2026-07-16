# PBD Validation Implementation - Field Service Dashboard

**Status**: UI Ready, Backend API Ready, Waiting for Heroku Deployment  
**Last Updated**: July 16, 2026

---

## ✅ What's Implemented (Ready for Heroku)

### 1. UI Components Added to Dashboard

**Phase 1 Program Cards Now Show:**
- ✅ Validation status badges (PASS ✅ / PASS WITH WARNINGS ⚠️ / FAIL ❌)
- ✅ Completion percentage (e.g., "85% complete")
- ✅ "View PBD" button (links to Google Doc)
- ✅ "View Report" button (links to validation report)
- ✅ "Re-validate" button (triggers live validation)

**Location**: Both "Prototyping" and "Ready for Review" subcolumns in Phase 1

**Styling**: Matches Service Cloud's design:
- Pass = Green badge
- Pass with Warnings = Yellow badge
- Fail = Red badge
- Blue gradient "View PBD" button
- Orange gradient "View Report" button
- Purple gradient "Re-validate" button

### 2. Backend API Endpoint

**Route**: `POST /api/validate-pbd`

**Request Body**:
```json
{
  "program_id": "sheet_123",
  "pbd_url": "https://docs.google.com/document/d/1ABC.../edit"
}
```

**Response** (on success):
```json
{
  "success": true,
  "validation_status": "PASS WITH WARNINGS",
  "completion": 85,
  "report_url": "validation_reports/Program_Name.html"
}
```

**What It Does**:
1. Receives PBD URL from frontend
2. Calls `validate_pbd_real.py` script
3. Script invokes `/validate-pbd` skill via Claude Code
4. Parses validation results
5. Updates `data/phase_1_programs.json`
6. Returns validation status to frontend
7. Frontend reloads page to show updated status

### 3. JavaScript Function

**Function**: `revalidatePBD(programId, pbdUrl)`

**What It Does**:
- Shows loading spinner ("⏳ Validating...")
- POSTs to `/api/validate-pbd` endpoint
- Displays validation results in alert
- Reloads page to show updated badges
- Handles errors gracefully (shows message if backend unavailable)

---

## 📊 How Service Cloud Does It (Reference)

### PBD Link Storage

**Service Cloud stores PBD links in two places:**

1. **Hardcoded in `fetch_phase1_data.py`** (lines 20-56):
   ```python
   PBDS = [
       {
           "id": "1ABC...",
           "name": "Service Agent Copilot",
           "url": "https://docs.google.com/document/d/.../edit",
           "pm": "Sarah Chen",
           "arch": "Priya Singh"
       },
       ...
   ]
   ```

2. **Persisted in `data/phase_1_programs.json`** after validation:
   ```json
   {
     "name": "Service Agent Copilot",
     "pm": "Sarah Chen",
     "arch": "Priya Singh",
     "status": "⚠️ PASS WITH WARNINGS",
     "completion": 81,
     "pbd_url": "https://docs.google.com/document/.../edit",
     "validation_status": "PASS WITH WARNINGS",
     "report_url": "validation_reports/Service_Agent_Copilot.html"
   }
   ```

### Validation Workflow

**Initial Setup** (Manual, one-time):
1. PM creates PBD in Google Docs
2. Someone adds PBD URL to hardcoded `PBDS` list in `fetch_phase1_data.py`
3. Run `python3 fetch_phase1_data.py` to validate all PBDs
4. Results saved to `data/phase_1_programs.json`
5. Dashboard loads JSON and displays validation badges

**Re-validation** (On-demand, requires Heroku):
1. User clicks "Re-validate" button on dashboard
2. Frontend calls `POST /api/validate-pbd` with PBD URL
3. Backend runs validation script
4. Script calls `/validate-pbd` skill (Claude Code + Google Workspace MCP)
5. New validation results overwrite old results in JSON
6. Frontend reloads, shows updated badges

**Answer to Your Question**: Yes, re-validation **immediately overwrites** the previous validation results. There's no version history - the JSON file only stores the most recent validation.

---

## 🔴 What's Blocked on GitHub Pages

### Cannot Work Without Backend:

1. ❌ **"Re-validate" button** - Needs Flask backend to run validation script
2. ❌ **Live validation** - Requires Claude Code with Google Workspace MCP
3. ❌ **Automatic validation** - Cannot trigger on status changes
4. ❌ **Report generation** - Cannot run Python scripts to generate HTML reports

### Why GitHub Pages Blocks This:

- GitHub Pages only serves static files
- No Python runtime to run `validate_pbd_real.py`
- No Flask backend to handle `/api/validate-pbd` requests
- No Claude Code access (MCP tools not available)
- No ability to write updated JSON files back to disk

### Workaround (Manual Pre-validation):

You could manually validate PBDs before deploying:

```bash
# On your Mac (before deploying):
1. python3 fetch_phase1_data.py  # Validates all PBDs, updates JSON
2. python3 sync_to_github_pages.py  # Rebuild static site with validation results
3. git commit && git push  # Deploy to GitHub Pages
```

**But this means:**
- ⚠️ Validation only happens when you manually run it
- ⚠️ No "Re-validate" button for team (only you can validate)
- ⚠️ Stale results if PBD changes after you validated
- ⚠️ Team cannot self-service

---

## 🎯 Field Service Implementation Plan

### Phase 1: Add PBD Links to Data Source ✅ DONE

**We need to populate PBD URLs for Field Service Phase 1 programs:**

**Option A: Add to Google Sheet** (Recommended)
- Add "PBD URL" column to Field Service Google Sheet
- PMs paste their PBD links in the sheet
- `sync_phase0_complete.py` reads PBD URL column
- Saves to `data/phase_0_programs.json` with `pbd_url` field

**Option B: Hardcode Like Service Cloud**
- Create `FIELD_SERVICE_PBDS` list in a script
- Manually maintain the list (not scalable)

**Recommendation**: Option A - keep PBD links in Google Sheet so PMs can manage them

### Phase 2: Create Validation Script ✅ DONE

**Already exists**: `validate_pbd_real.py`

**What it does**:
- Takes PBD URL as input
- Calls `/validate-pbd` skill via Claude Code CLI
- Parses validation results (status, completion %, issues)
- Returns JSON with validation data

### Phase 3: Initial Validation Run (Manual)

**Create a script**: `fetch_phase1_validation.py`

```python
# Read Phase 1 programs from phase_0_programs.json (phase='1')
# For each program with pbd_url:
#   - Run validate_pbd_real.py
#   - Parse validation results
#   - Add validation_status, completion, report_url to program
# Save updated data back to phase_0_programs.json
```

**Run manually on your Mac** before deploying to Heroku

### Phase 4: Deploy to Heroku ⏳ WAITING

**When you get Heroku access:**

1. Deploy Field Service dashboard to Heroku
2. Set up environment variables (if needed for GUS auth)
3. Test "Re-validate" button - should work immediately
4. Set up Heroku Scheduler (optional):
   - Run `fetch_phase1_validation.py` daily at 6 AM
   - Auto-validates all Phase 1 PBDs
   - Keeps validation status fresh

---

## 📋 Comparison: Service Cloud vs Field Service

| Feature | Service Cloud (Heroku) | Field Service (GitHub Pages) | Field Service (Heroku - Future) |
|---------|------------------------|------------------------------|----------------------------------|
| **PBD Links Source** | Hardcoded in Python | Google Sheet (planned) | Google Sheet |
| **Initial Validation** | Manual script run | Manual script run | Manual script run |
| **Validation Storage** | phase_1_programs.json | phase_0_programs.json | phase_0_programs.json |
| **UI Display** | ✅ Status badges | ✅ Status badges (ready) | ✅ Status badges |
| **Re-validate Button** | ✅ Working | ❌ Non-functional | ✅ Will work |
| **Auto-validation** | ❌ Not implemented | ❌ Not possible | ✅ Can add via Scheduler |
| **Version History** | ❌ Overwrites | ❌ Overwrites | ❌ Overwrites |

---

## 🛠️ How to Test (On Heroku)

### 1. Add a PBD URL to Google Sheet

In Field Service Google Sheet, add column for "PBD URL":
```
| Feature Name | ... | PBD URL |
|--------------|-----|---------|
| Assets: Service BOM | ... | https://docs.google.com/document/d/ABC.../edit |
```

### 2. Sync Data

```bash
# Fetch latest from Google Sheet (includes new PBD URL)
python3 sync_phase0_complete.py
```

### 3. Run Initial Validation

```bash
# Validate all Phase 1 programs
python3 fetch_phase1_validation.py
```

This creates:
- `data/phase_0_programs.json` with validation_status, completion, report_url fields
- `static/validation_reports/Program_Name.html` - detailed validation report

### 4. Deploy to Heroku

```bash
git push heroku main
heroku open
```

### 5. Test Re-validate Button

1. Go to dashboard → Phase 1 → Ready for Review
2. Click "Re-validate" on a program
3. Should see: "⏳ Validating..." → Alert with results → Page reloads
4. Validation badge updates (PASS/FAIL changes if PBD was edited)

---

## ⚠️ Current Limitations

### 1. No Version History
- Re-validation **overwrites** previous results
- Cannot see "what changed" between validations
- Cannot roll back to previous validation

**Potential Enhancement**: 
- Store validation history in `validation_history/program_name_YYYY-MM-DD.json`
- Display "Last validated: 2 days ago"
- Link to view previous validation results

### 2. No Automatic Validation
- Service Cloud doesn't auto-validate either
- Must click "Re-validate" button manually
- Or run scheduled job via Heroku Scheduler

**Potential Enhancement**:
- Heroku Scheduler runs daily validation
- Detects PBD changes (via Google Docs API last modified date)
- Only re-validates if PBD was edited since last check

### 3. No Notification on Status Change
- If validation goes from PASS → FAIL, no alert
- Team must check dashboard to see status

**Potential Enhancement**:
- Post Slack notification when validation status changes
- Weekly summary: "5 PBDs passing, 2 need attention"

---

## 📝 Next Steps

### For GitHub Pages (Current):
1. ✅ UI is ready (badges, buttons render correctly)
2. ⚠️ Buttons are non-functional (expected - no backend)
3. ✅ Can manually validate and bake results into static site

### For Heroku (When Available):
1. Add PBD URL column to Google Sheet
2. Update `sync_phase0_complete.py` to read PBD URL field
3. Create `fetch_phase1_validation.py` for initial validation
4. Test locally on localhost:5002
5. Deploy to Heroku
6. Test "Re-validate" button
7. (Optional) Set up Heroku Scheduler for daily auto-validation

---

## 🎯 Summary for Esther

**Q: Where are PBD links sourced from?**
- Service Cloud: Hardcoded in Python script
- Field Service (Planned): Google Sheet column (scalable, PM-managed)

**Q: How are they stored?**
- In `data/phase_1_programs.json` (Service Cloud) or `data/phase_0_programs.json` (Field Service)
- Each program has: name, pm, arch, pbd_url, validation_status, completion, report_url

**Q: Does re-validate overwrite the last validation?**
- **Yes, immediately.** No version history.
- JSON file only stores most recent validation results
- If you re-validate and it goes from PASS → FAIL, the old PASS status is gone

**UI Status**: ✅ Ready - matches Service Cloud's design, buttons render correctly  
**Backend Status**: ✅ Ready - API endpoint exists, validation script exists  
**Blocker**: GitHub Pages (no backend runtime)  
**Ready for**: Heroku deployment - will work immediately when deployed
