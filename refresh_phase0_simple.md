# Simple Phase 0/1 Refresh

## Current Status
- **Localhost data**: July 20, 2026 (79 Phase 0, 8 Phase 1)
- **Google Sheet**: ~82 Phase 0 items (3 more than cached data)

## To Refresh Now

In this Claude Code session, just say:

```
Please update Phase 0/1 data from the Google Sheet to match the current 82 items
```

I'll:
1. Fetch the full sheet (all 124 rows)
2. Process and parse it
3. Update `data/phase_0_programs.json`
4. Show you the new breakdown

## Why the Difference?

The sheet has 3 more Phase 0 items than your July 20 cache. This means:
- New items were added, OR
- Items were moved from other stages to "PM Backlog (Phase 0)"

## After Updating

To deploy the fresh data:
- **Local testing**: Restart Flask (`python3 app.py`)
- **GitHub Pages**: Run `./auto_update_dashboard.sh`
- **Heroku staging**: Push to GitHub (auto-deploys)

## Automation Note

Since you don't have Google service account permissions, Phase 0/1 refresh will remain manual through Claude Code sessions. The Google Workspace MCP plugin you have works perfectly - it just requires an interactive session.
