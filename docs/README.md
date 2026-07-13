# Field Service PDLC Dashboard

Static GitHub Pages version of the Field Service PDLC Dashboard showing Programs, Projects, and Epics execution status.

## Features

- **Three-level hierarchy**: Programs → Projects → Epics
- **Health status indicators**: Color-coded status badges and left borders on epics
- **Expand/collapse navigation**: Click program headers to see projects, click project headers to see epics
- **Stats cards**: Summary view of Programs, Projects, and Epics with health breakdowns
- **Pillbox project design**: Clean, modern UI matching Service Cloud PDLC patterns
- **GUS integration**: Direct links to GUS records (requires Salesforce access)

## Data Source

Data comes from GUS Report `00OEE000002tswH2AQ` (264 Field Service Program Epic Admin) and is stored in `execution_data.json`.

## Updating Data

To refresh the data:

1. Run the data fetch script:
   ```bash
   cd /Users/julia.blanchard/field-service-execution-dashboard
   python3 fetch_execution_data.py
   ```

2. Copy the updated JSON to docs:
   ```bash
   cp data/execution_data.json docs/execution_data.json
   ```

3. Commit and push to GitHub:
   ```bash
   git add docs/execution_data.json
   git commit -m "Update execution data"
   git push
   ```

## Local Testing

Open `index.html` in a browser:
```bash
open docs/index.html
```

Or run a local web server:
```bash
cd docs
python3 -m http.server 8000
# Visit http://localhost:8000
```

## GitHub Pages Setup

1. Push the `docs/` folder to your repository
2. Go to Settings → Pages
3. Select "Deploy from a branch"
4. Choose `main` branch and `/docs` folder
5. Save

Your dashboard will be available at: `https://<username>.github.io/<repository-name>/`

## Last Data Update

Check the "Last Updated" timestamp in the dashboard header for the most recent data fetch time.
