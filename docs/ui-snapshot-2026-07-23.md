# PDLC Dashboard UI Snapshot - July 23, 2026

## Git Tag
`ui-snapshot-2026-07-23-orphaned-views`

## Dashboard State Summary
- **Local**: http://localhost:5002
- **Staging**: https://fieldservice-adlc-staging-146cc68a9d19.rose-virginia.herokuapp.com/
- **Production**: https://fieldservice-adlc-prod-f5fb6723c2e1.aster-virginia.herokuapp.com/

## Major Features Completed

### 1. Orphaned/Unallocated Tab Views
- **By Team**: Expandable team rows showing all orphaned epics per team
- **By Engineering Manager**: Groups orphaned work by EM with expand/collapse
- **By Product Manager**: Groups orphaned work by PM with expand/collapse

### 2. Phase 0/1 Google Sheets Integration
- Complete data capture: 128 programs (was 12 before)
- Breakdown: 118 PM Backlog (Phase 0), 10 Prototyping/Review
- Multi-batch MCP reading to avoid truncation

### 3. Status Badge Color Consistency
All views now use consistent status colors:
- On Track: #10b981 (green)
- Watch: #f59e0b (amber)
- Blocked: #dc2626 (red)
- Completed: #60a5fa (blue)
- On Hold: #eab308 (yellow)
- Canceled: #bca2d3 (purple)
- Not Started: #94a3b8 (gray)
- Default: #64748b (slate)

## Tab Layout Details

### Overview Tab
- Portfolio dropdown filter (Field Service/UWM only, no old releases)
- Three stat cards: PROGRAMS, PROJECTS, EPICS with status breakdowns
- Program list with expand/collapse hierarchy
- Programs → Projects → Epics → Work Items

### Execution Tab
- Three stat cards at top (PROGRAMS, PROJECTS, EPICS)
- Filter view dropdown: All Programs, 264 Field Service Foundations, 264 Field Service Mobile, etc.
- Table columns: Program/Project, Status, PM, Est. Delivery, Epic Count
- Expand/collapse for program → project → epic hierarchy
- Status pills for filtering

### Allocations Tab
- Portfolio filter dropdown
- Program filter dropdown (All Programs or specific)
- Allocation type toggle: All Teams / Unmapped Only
- Table: Team, Filled/Total Headcount, Jun Delivered, Jul-Sep Committed
- Expandable rows show program breakdown with epic details
- "Unmapped" section for work without portfolio/program mapping

### Orphaned/Unallocated Tab
**Three view toggles**: By Team | By Engineering Manager | By Product Manager

#### By Team View
- Columns: Team, Epic Count, Orphaned Capacity, Scheduled Build
- Expandable team rows reveal epic details
- Each epic shows: Name (linked to GUS), Status badge, Owner, Scheduled Build

#### By Engineering Manager View
- Columns: Engineering Manager, Epic Count, Orphaned Capacity, Scheduled Build
- Groups all epics by their team's EM
- "Unassigned" shown for teams without EM
- Epic details include Team name

#### By Product Manager View
- Columns: Product Manager, Epic Count, Orphaned Capacity, Scheduled Build
- Groups all epics by their team's PM
- "Unassigned" shown for teams without PM
- Epic details include Team name

### Phase 0 Tab
- Displays initiatives from Google Sheets "Phase 0 & Phase 1 Priorites"
- Filters by portfolio and stage
- Shows: Initiative, Portfolio, Theme, Stage, PM Lead
- 128 total programs displayed

## Key CSS Components

### Status Badge Styles
```css
.status-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    white-space: nowrap;
    color: white;
}

/* Inline styles used in JS rendering */
background: #10b981; /* On Track */
background: #f59e0b; /* Watch */
background: #dc2626; /* Blocked */
background: #60a5fa; /* Completed */
background: #eab308; /* On Hold */
background: #bca2d3; /* Canceled */
background: #94a3b8; /* Not Started */
background: #64748b; /* Default */
```

### Status Pills (Filter Bar)
```css
.status-pill {
    padding: 8px 18px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    cursor: default;
    transition: all 0.2s;
    border: 1px solid;
}

.status-pill.pill-on-track {
    background: #d1fae5;
    color: #047857;
    border-color: #10b981;
}

.status-pill.pill-not-started {
    background: #f3f4f6;
    color: #6b7280;
    border-color: #d1d5db;
}

.status-pill.pill-on-watch {
    background: #fef3c7;
    color: #d97706;
    border-color: #fbbf24;
}

.status-pill.pill-blocked {
    background: #fee2e2;
    color: #dc2626;
    border-color: #ef4444;
}

.status-pill.pill-completed {
    background: #dbeafe;
    color: #1e40af;
    border-color: #60a5fa;
}
```

### View Toggle Buttons
```css
.view-toggle {
    padding: 10px 20px;
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 14px;
    font-weight: 600;
}

.view-toggle.active {
    background: rgba(255, 255, 255, 0.95);
    color: #1e293b;
    border-color: rgba(255, 255, 255, 0.95);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

### Expandable Row Styling
```css
/* Team/Manager summary row */
.team-row, .em-row, .pm-row {
    background: #f8fafc;
    border-bottom: 1px solid #e5e7eb;
    cursor: pointer;
}

/* Expand/collapse icon */
.expand-icon {
    width: 16px;
    height: 16px;
    margin-right: 8px;
    transition: transform 0.2s;
}

.expand-icon.expanded {
    transform: rotate(90deg);
}

/* Epic detail rows (hidden by default) */
.breakdown-orphaned-* {
    display: none;
    border-bottom: 1px solid #f1f5f9;
}
```

### Stat Cards
```css
.stat-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    padding: 24px;
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.stat-card-value {
    font-size: 48px;
    font-weight: 700;
    background: linear-gradient(135deg, #ffffff 0%, rgba(255,255,255,0.8) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
    margin-bottom: 8px;
}

.stat-card-label {
    font-size: 14px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
    text-transform: uppercase;
    letter-spacing: 1px;
}
```

## Data Sources

### GUS Queries
- **Execution Data**: Reports 00OEE000003DBgQ2AW (264), 00OEE000003DBgV2AW (262)
- **Teams Roster**: Report 00OEE000002a9YH2AY
- **Team Managers**: ADM_Scrum_Team__c (Engineering_Manager__r.Name, Product_Owner__r.Name)
- **Work Items**: ADM_Work__c with Sprint, Epic, Team joins

### Google Sheets
- **Phase 0/1 Programs**: Sheet ID 1ERWXm6wVS5ItzxCqR6pX1tTf6_ec2_D-jPZeEF5V89c
- **Tab**: "Phase 0 & Phase 1 Priorites"
- **Columns**: Portfolio, Theme, Tier, Stage, Initiative, PM Lead, Arch Lead, etc.

## JavaScript Functions

### Orphaned Tab Rendering
- `renderOrphanedByTeam()` - Lines 16340-16408
- `renderOrphanedByEM()` - Lines 16431-16498
- `renderOrphanedByPM()` - Lines 16500-16567
- `toggleOrphanedTeamBreakdown()` - Expand/collapse team epics
- `toggleOrphanedEMBreakdown()` - Expand/collapse EM epics
- `toggleOrphanedPMBreakdown()` - Expand/collapse PM epics
- `switchOrphanedView()` - Toggle between Team/EM/PM views

### Data Loading
- `fetchOrphanedData()` - Loads /api/orphaned endpoint
- `fetchExecutionData()` - Loads execution programs/projects/epics
- `fetchPhase0Data()` - Loads Phase 0 programs from Google Sheets

## Backend Endpoints

### Flask Routes (app.py)
- `/` - Main dashboard page
- `/api/execution` - Execution tab data (programs, projects, epics)
- `/api/orphaned` - Orphaned tab data (by_team, by_em, by_pm)
- `/api/phase0` - Phase 0 programs from Google Sheets
- `/api/allocations` - Allocations tab data (team capacity by program)

### Data Refresh Scripts
- `fetch_execution_data.py` - Refresh 264/262 program data
- `fetch_teams_data.py` - Refresh team roster + manager data
- `populate_aug_sept_capacity.py` - Populate Jul/Aug/Sep capacity by sprint
- `refresh_phase0_local.py` - Process Phase 0 Google Sheet data

## Recent Fixes (July 23, 2026)

1. **Engineering Manager & Product Manager Views**
   - Added to Orphaned tab (replaced "By Release" view)
   - Manager data fetched from ADM_Scrum_Team__c
   - Title case applied to all manager names
   - "Unassigned" shown for teams without managers

2. **Phase 0 Google Sheet Refresh**
   - Fixed MCP truncation issue (was only getting 12 programs)
   - Now reads in 3 batches: rows 1-50, 51-100, 101-158
   - Captures all 128 programs (118 PM Backlog, 10 Prototyping/Review)

3. **Status Badge Color Consistency**
   - Updated all three Orphaned views to use complete color scheme
   - Matches Allocations tab colors
   - Added colors for Completed, On Hold, Canceled, Not Started

4. **Manager Data Integration**
   - `fetch_team_managers()` added to fetch_teams_data.py
   - Runs during normal team refresh (no separate script needed)
   - Data committed to teams_data.json with roster counts
   - Deployed to staging/production via GitHub auto-deploy

## Files Modified (July 23, 2026)

- `templates/field_service_dynamic.html` - EM/PM views, status colors
- `app.py` - /api/orphaned endpoint with by_em/by_pm groupings
- `fetch_teams_data.py` - fetch_team_managers() function
- `data/teams_data.json` - Added engineering_manager, product_owner fields
- `data/phase_0_programs.json` - Complete 128 program dataset

## Known Issues / Future Work

1. **Heroku Scheduler** - Needs setup for automated data refresh
2. **Dependency Indicators** - Not yet added to programs/projects/epics
3. **Execution Tab Filter View** - Needs verification it's working correctly
4. **teams_data.json Overwrite** - Capacity fields occasionally get wiped (needs investigation)

## Screenshots Required

To complete this snapshot, capture screenshots of:
1. Overview tab - expanded program view
2. Execution tab - with stat cards and filters
3. Allocations tab - showing program breakdown
4. Orphaned tab - By Team view (expanded)
5. Orphaned tab - By Engineering Manager view (expanded)
6. Orphaned tab - By Product Manager view (expanded)
7. Phase 0 tab - showing all programs

---
*Snapshot created: July 23, 2026*
*Git tag: `ui-snapshot-2026-07-23-orphaned-views`*
*Commit: fafa547*
