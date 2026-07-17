#!/usr/bin/env python3
"""
Generate static HTML pages for GitHub Pages deployment
"""

import os
from pathlib import Path
from app import app

OUTPUT_DIR = Path(__file__).parent / "docs"

def generate_static_site():
    """Generate static HTML files from Flask app"""

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Copy static assets
    import shutil
    static_src = Path(__file__).parent / "static"
    static_dst = OUTPUT_DIR / "static"
    if static_dst.exists():
        shutil.rmtree(static_dst)
    shutil.copytree(static_src, static_dst)

    # Copy data directory
    data_src = Path(__file__).parent / "data"
    data_dst = OUTPUT_DIR / "data"
    if data_dst.exists():
        shutil.rmtree(data_dst)
    shutil.copytree(data_src, data_dst)

    with app.test_client() as client:
        # Generate Field Service dashboard as index
        print("Generating index.html (Field Service execution dashboard)...")
        response = client.get('/')
        with open(OUTPUT_DIR / "index.html", 'wb') as f:
            f.write(response.data)

        print(f"✅ Static site generated in {OUTPUT_DIR}")
        print(f"   - index.html (Field Service dashboard)")
        print(f"   - static/ (CSS, JS, images)")
        print(f"   - data/ (JSON data files)")

if __name__ == '__main__':
    generate_static_site()
