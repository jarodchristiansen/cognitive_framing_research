"""
Diagnostic script to understand why no assignments are being made.
This will show us:
1. What keywords are actually being found in the documents
2. What scores are being calculated
3. Sample text from documents to see if they're relevant
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import re
from canonicalization import TextCanonicalizer
from concept_assignment import ConceptAssigner
from concepts import get_concept_by_id

print("=" * 80)
print("CONCEPT ASSIGNMENT DIAGNOSTIC")
print("=" * 80)

# Load documents
print("\n1. Loading documents...")
df = pd.read_parquet("ingested_data/documents.parquet")
print(f"   Loaded {len(df)} documents")

# Get concept
concept = get_concept_by_id('income_wealth_inequality')
print(f"\n2. Concept: {concept.name}")
print(f"   Seed terms: {len(concept.seed_terms)} terms")
print(f"   First 10 seed terms: {concept.seed_terms[:10]}")

# Initialize components
canonicalizer = TextCanonicalizer()
assigner = ConceptAssigner(
    min_confidence=0.25,
    use_embeddings=True
)

# Test keyword matching on all documents
print("\n3. Testing keyword matching across all documents...")
print("-" * 80)

all_keyword_scores = []
all_embedding_scores = []
all_combined_scores = []

for idx, row in df.iterrows():
    # Canonicalize
    segments = canonicalizer.canonicalize_document(row['id'], row['raw_text'])
    
    if not segments:
        continue
    
    # Test first segment (usually most relevant)
    segment = segments[0]
    
    # Calculate scores
    keyword_score = assigner._keyword_match_score(segment.text, concept)
    embedding_score = assigner._embedding_similarity_score(segment.text, concept) if assigner.use_embeddings else 0.0
    
    if assigner.use_embeddings:
        combined_score = assigner.keyword_weight * keyword_score + assigner.embedding_weight * embedding_score
    else:
        combined_score = keyword_score
    
    all_keyword_scores.append(keyword_score)
    all_embedding_scores.append(embedding_score)
    all_combined_scores.append(combined_score)
    
    # Show details for segments with any keyword matches
    if keyword_score > 0:
        print(f"\nDocument {idx}: {row['title'][:60]}...")
        print(f"  Source: {row['source_id']}")
        print(f"  Keyword score: {keyword_score:.3f}")
        print(f"  Embedding score: {embedding_score:.3f}")
        print(f"  Combined score: {combined_score:.3f}")
        print(f"  Threshold: {assigner.min_confidence}")
        print(f"  Would assign: {'YES' if combined_score >= assigner.min_confidence else 'NO'}")
        
        # Show which keywords matched
        normalized_text = segment.text.lower()
        normalized_text = re.sub(r'[^\w\s]', ' ', normalized_text)
        words = set(normalized_text.split())
        
        matched_terms = []
        for term in concept.seed_terms:
            normalized_term = term.lower()
            if normalized_term in normalized_text:
                matched_terms.append(term)
            elif ' ' in normalized_term:
                term_words = normalized_term.split()
                if all(word in words for word in term_words):
                    matched_terms.append(term)
        
        if matched_terms:
            print(f"  Matched terms: {matched_terms[:5]}...")  # Show first 5
        print(f"  Text preview: {segment.text[:200]}...")

# Summary statistics
print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)
print(f"Total documents tested: {len(all_keyword_scores)}")
print(f"\nKeyword Scores:")
print(f"  Max: {max(all_keyword_scores):.3f}")
print(f"  Mean: {sum(all_keyword_scores) / len(all_keyword_scores):.3f}")
print(f"  Min: {min(all_keyword_scores):.3f}")
print(f"  Documents with keyword_score > 0: {sum(1 for s in all_keyword_scores if s > 0)}")
print(f"  Documents with keyword_score >= 0.3: {sum(1 for s in all_keyword_scores if s >= 0.3)}")

if assigner.use_embeddings:
    print(f"\nEmbedding Scores:")
    print(f"  Max: {max(all_embedding_scores):.3f}")
    print(f"  Mean: {sum(all_embedding_scores) / len(all_embedding_scores):.3f}")
    print(f"  Min: {min(all_embedding_scores):.3f}")

print(f"\nCombined Scores:")
print(f"  Max: {max(all_combined_scores):.3f}")
print(f"  Mean: {sum(all_combined_scores) / len(all_combined_scores):.3f}")
print(f"  Min: {min(all_combined_scores):.3f}")
print(f"  Documents above threshold ({assigner.min_confidence}): {sum(1 for s in all_combined_scores if s >= assigner.min_confidence)}")

# Show top 5 by combined score
print("\n" + "=" * 80)
print("TOP 5 DOCUMENTS BY COMBINED SCORE")
print("=" * 80)

scores_with_docs = list(zip(all_combined_scores, range(len(df))))
scores_with_docs.sort(reverse=True, key=lambda x: x[0])

for i, (score, doc_idx) in enumerate(scores_with_docs[:5], 1):
    row = df.iloc[doc_idx]
    segments = canonicalizer.canonicalize_document(row['id'], row['raw_text'])
    if segments:
        segment = segments[0]
        keyword_score = assigner._keyword_match_score(segment.text, concept)
        embedding_score = assigner._embedding_similarity_score(segment.text, concept) if assigner.use_embeddings else 0.0
        
        print(f"\n[{i}] Combined Score: {score:.3f}")
        print(f"    Title: {row['title']}")
        print(f"    Source: {row['source_id']}")
        print(f"    Keyword: {keyword_score:.3f}, Embedding: {embedding_score:.3f}")
        print(f"    Preview: {segment.text[:300]}...")

# Check if documents contain any inequality-related terms at all
print("\n" + "=" * 80)
print("CHECKING FOR ANY INEQUALITY-RELATED TERMS IN ALL DOCUMENTS")
print("=" * 80)

inequality_indicators = ['inequality', 'inequal', 'wealth', 'income', 'wage', 'gap', 'disparity', 'distribution', 'gini', 'quintile']
found_any = False

for idx, row in df.iterrows():
    text_lower = row['raw_text'].lower()
    found_terms = [term for term in inequality_indicators if term in text_lower]
    if found_terms:
        found_any = True
        print(f"\nDocument {idx}: {row['title'][:60]}...")
        print(f"  Contains: {found_terms}")
        print(f"  Preview: {row['raw_text'][:200]}...")

if not found_any:
    print("\n⚠️  WARNING: No documents contain basic inequality-related terms!")
    print("   This suggests the documents may not be relevant to income/wealth inequality.")
    print("   Consider:")
    print("   1. Expanding ingestion to get more diverse content")
    print("   2. Adjusting concept definition to be broader")
    print("   3. Checking if your sources cover economic topics")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

