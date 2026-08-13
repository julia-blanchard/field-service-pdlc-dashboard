#!/usr/bin/env python3
"""
Parse multiple labeled Google Doc URLs from a single field.
Expected format in Google_Doc_URL__c:
  PBD: https://docs.google.com/document/d/abc123
  HLD: https://docs.google.com/document/d/def456
  PRD: https://docs.google.com/document/d/ghi789
"""
import re

def parse_labeled_urls(text):
    """
    Extract labeled URLs from text.
    Returns dict like: {'PBD': 'https://...', 'HLD': 'https://...'}
    """
    if not text:
        return {}

    urls = {}

    # Pattern: Label: URL or Label - URL
    # Supports: "PBD:", "PBD -", "[PBD]", etc.
    pattern = r'(?:^|\n)\s*([A-Za-z\s]+?)[\s:-]+\s*(https?://[^\s\n]+)'

    matches = re.findall(pattern, text, re.MULTILINE)

    for label, url in matches:
        # Clean up label
        label = label.strip().upper()
        # Remove brackets if present
        label = re.sub(r'[\[\]]', '', label)
        urls[label] = url.strip()

    # If no labels found, check if it's just a single URL
    if not urls:
        single_url = re.search(r'(https?://[^\s]+)', text)
        if single_url:
            # Try to guess the type from context
            urls['PBD'] = single_url.group(1)

    return urls

# Test cases
test_cases = [
    # Multi-line labeled
    """
    PBD: https://docs.google.com/document/d/1QCXLHOwl6bQ8iTng3qGKhZLpZuz_TIrgS6jmq0606bo/edit
    HLD: https://docs.google.com/document/d/abc123/edit
    PRD: https://docs.google.com/document/d/def456/edit
    """,

    # Dash separator
    """
    PBD - https://docs.google.com/document/d/123
    HLD - https://docs.google.com/document/d/456
    """,

    # Single URL (current format)
    "https://docs.google.com/document/d/1QCXLHOwl6bQ8iTng3qGKhZLpZuz_TIrgS6jmq0606bo/edit",

    # Bracketed labels
    """
    [PBD] https://docs.google.com/document/d/123
    [HLD] https://docs.google.com/document/d/456
    """,
]

print("🧪 Testing URL parser:\n")
for i, test in enumerate(test_cases, 1):
    print(f"Test {i}:")
    print(f"Input: {test.strip()[:80]}...")
    result = parse_labeled_urls(test)
    print(f"Output: {result}")
    print()
