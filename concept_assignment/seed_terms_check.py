"""
Quick check to see if documents contain any seed terms at all.
This will help us understand if it's a matching problem or content problem.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import re
from concepts import get_concept_by_id

print("Quick Check: Do documents contain seed terms?")
print("=" * 80)

# Load documents
df = pd.read_parquet("ingested_data/documents.parquet")
print(f"Loaded {len(df)} documents\n")

# Get concept
concept = get_concept_by_id('income_wealth_inequality')
print(f"Concept: {concept.name}")
print(f"Testing {len(concept.seed_terms)} seed terms\n")

# Check each document
matches_found = 0
for idx, row in df.iterrows():
    text_lower = row['raw_text'].lower()
    
    # Simple check: does any seed term appear?
    found_terms = []
    for term in concept.seed_terms:
        if term.lower() in text_lower:
            found_terms.append(term)
    
    if found_terms:
        matches_found += 1
        print(f"✓ Document {idx}: {row['title'][:60]}...")
        print(f"  Source: {row['source_id']}")
        print(f"  Found terms: {found_terms[:5]}...")  # Show first 5
        print(f"  Preview: {row['raw_text'][:150]}...")
        print()

print("=" * 80)
print(f"Summary: {matches_found} out of {len(df)} documents contain seed terms")
print("=" * 80)

if matches_found == 0:
    print("\n⚠️  No seed terms found in any documents!")
    print("   This means either:")
    print("   1. The documents don't cover income/wealth inequality topics")
    print("   2. The seed terms need to be adjusted")
    print("\n   Let's check what topics the documents DO cover...")
    print("\n   Sample titles:")
    for i, row in df.head(10).iterrows():
        print(f"     - {row['title']}")

