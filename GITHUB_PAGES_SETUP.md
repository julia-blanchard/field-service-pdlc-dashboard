# GitHub Pages Deployment Guide

## Quick Start

Your static dashboard is ready in the `docs/` folder! Here's how to deploy it to GitHub Pages.

## Step 1: Push to GitHub

```bash
cd /Users/julia.blanchard/field-service-execution-dashboard

# Add all files
git add docs/

# Commit
git commit -m "Add static GitHub Pages dashboard"

# Push (you may need to pull first if remote has content)
git pull origin main --rebase
git push origin main
```

## Step 2: Enable GitHub Pages

1. Go to your repository: https://git.soma.salesforce.com/julia-blanchard/field-service-tpm-pdlc
2. Click **Settings**
3. Click **Pages** in the left sidebar
4. Under "Build and deployment":
   - Source: **Deploy from a branch**
   - Branch: **main**
   - Folder: **/docs**
5. Click **Save**

## Step 3: Access Your Dashboard

After 1-2 minutes, your dashboard will be available at:
```
https://pages.git.soma.salesforce.com/julia-blanchard/field-service-tpm-pdlc/
```

(The exact URL depends on your enterprise GitHub Pages configuration)

## Updating the Dashboard

### Manual Update

1. Fetch fresh data from GUS:
   ```bash
   cd /Users/julia.blanchard/field-service-execution-dashboard
   python3 fetch_execution_data.py
   ```

2. Copy to docs:
   ```bash
   cp data/execution_data.json docs/execution_data.json
   ```

3. Commit and push:
   ```bash
   git add docs/execution_data.json
   git commit -m "Update dashboard data - $(date +%Y-%m-%d)"
   git push
   ```

### Automated Update (Optional)

You can set up a cron job to auto-update:

```bash
# Edit crontab
crontab -e

# Add this line to update daily at 6am:
0 6 * * * cd /Users/julia.blanchard/field-service-execution-dashboard && python3 fetch_execution_data.py && cp data/execution_data.json docs/ && git add docs/execution_data.json && git commit -m "Auto-update data" && git push
```

## Local Testing

Test the static version locally before deploying:

```bash
cd docs
python3 -m http.server 8080
# Open http://localhost:8080 in your browser
```

## What's Included

- ✅ **index.html** - Static dashboard with all styling and JavaScript
- ✅ **execution_data.json** - Current Field Service data from GUS
- ✅ **README.md** - Documentation
- ✅ All expand/collapse functionality works client-side
- ✅ Stats cards with health breakdowns
- ✅ Pillbox project containers
- ✅ Color-coded epic health indicators
- ✅ Direct GUS links (for users with access)

## Differences from Flask Version

| Feature | Flask (Port 5002) | Static (GitHub Pages) |
|---------|-------------------|----------------------|
| Data updates | Live via API | Manual JSON refresh |
| Hosting | Requires Python server | Free GitHub hosting |
| Styling | Identical | Identical |
| Expand/collapse | ✅ Works | ✅ Works |
| Sharing | localhost only | Public URL |
| Demo-ready | No (local only) | ✅ Yes |

## Troubleshooting

**Page not loading?**
- Check if GitHub Pages is enabled in repo settings
- Verify the `docs/` folder exists on the main branch
- Wait 1-2 minutes for deployment

**Data looks old?**
- Run `fetch_execution_data.py` to get fresh data
- Copy JSON to docs/ and push

**Styling broken?**
- All CSS is inline in index.html - no external dependencies
- Check browser console for errors
