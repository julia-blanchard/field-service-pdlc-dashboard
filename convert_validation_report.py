#!/usr/bin/env python3
"""
Convert markdown PBD validation reports to HTML for Flask display
"""
import markdown
import sys
from pathlib import Path
from datetime import datetime

def convert_md_to_html(md_path, output_dir):
    """Convert markdown report to styled HTML"""

    with open(md_path, 'r') as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

    # Wrap in styled HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>PBD Validation Report</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            padding: 40px;
            max-width: 900px;
            margin: 0 auto;
            line-height: 1.6;
        }}
        h1 {{
            color: #1e293b;
            border-bottom: 3px solid #8b5cf6;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #475569;
            margin-top: 32px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #64748b;
            margin-top: 24px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border: 1px solid #e2e8f0;
        }}
        th {{
            background: #f1f5f9;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f8fafc;
        }}
        code {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 0.9em;
        }}
        pre {{
            background: #f1f5f9;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        blockquote {{
            border-left: 4px solid #8b5cf6;
            margin: 20px 0;
            padding-left: 20px;
            color: #64748b;
        }}
        ul, ol {{
            padding-left: 24px;
        }}
        li {{
            margin: 8px 0;
        }}
        hr {{
            border: none;
            border-top: 2px solid #e2e8f0;
            margin: 32px 0;
        }}
        .timestamp {{
            color: #94a3b8;
            font-size: 0.9em;
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid #e2e8f0;
        }}
    </style>
</head>
<body>
{html_body}
<div class="timestamp">
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div>
</body>
</html>"""

    # Generate output filename
    doc_name = md_path.stem
    output_path = Path(output_dir) / f"{doc_name}.html"

    with open(output_path, 'w') as f:
        f.write(html)

    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 convert_validation_report.py <markdown_file>")
        sys.exit(1)

    md_file = Path(sys.argv[1])
    output_dir = Path(__file__).parent / "validation_reports"
    output_dir.mkdir(exist_ok=True)

    result = convert_md_to_html(md_file, output_dir)
    print(f"✅ Converted: {result}")
