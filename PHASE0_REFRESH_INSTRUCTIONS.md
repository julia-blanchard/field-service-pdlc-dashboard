# Phase 0/1 Google Sheets Data Refresh Instructions

## Background
Phase 0 and Phase 1 program data comes from the "FS Phase 0 & Phase 1" Google Sheet.
This data cannot be automatically refreshed by cron because it requires MCP (Model Context Protocol) access, which is only available in interactive Claude Code sessions.

## How to Refresh

When you want to refresh Phase 0/1 data, ask Claude in this project:

```
Please refresh Phase 0 and Phase 1 data from the Google Sheet
```

Claude will:
1. Use the MCP Google Workspace plugin to read the sheet
2. Parse the data (all rows, no caps)
3. Update `data/phase_0_programs.json`
4. Show you a summary of what was loaded

## Sheet Details

- **Sheet ID**: `1ERWXm6wVS5ItzxCqR6pX1tTf6_ec2_D-jPZeEF5V89c`
- **Sheet Name**: "Phase 0 & Phase 1 Priorites"
- **Range**: All columns (A:Z), all rows (no row limit)

## What Gets Loaded

- **Phase 0**: Items with "PM Backlog" in the Stage column
- **Phase 1**: Items with "Prototyping" or "Ready for Review" in Stage column
- **Columns mapped**:
  - Portfolio (A)
  - Stage (D)
  - Initiative (E)
  - Feature (I) - used as name if present, else Initiative
  - Status (Q)
  - PM Lead (R)
  - Arch Lead (S)
  - TPM Lead (T)
  - UX Lead (U)
  - CX Lead (V)

## Automated Updates

Phase 0/1 data is NOT included in the automated cron updates (9 AM / 2 PM).

You should refresh it manually:
- When you know the sheet has been updated
- Before presenting dashboard to leadership
- At the start of each sprint/release cycle

## After Refreshing

If you want the updated data on GitHub Pages or Heroku staging:
1. Refresh Phase 0/1 data (ask Claude)
2. Run the automated update: `./auto_update_dashboard.sh` (this rebuilds GitHub Pages)
3. For Heroku staging: push to GitHub, it will auto-deploy
