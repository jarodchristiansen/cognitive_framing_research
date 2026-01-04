# System Flow: End-to-End Process

This document explains the complete flow of data through the system, from ingestion to concept assignment.

## High-Level Flow

```
[Sources] → [Ingestion] → [Canonicalization] → [Concept Assignment] → [Analysis]
```

## Detailed Flow

### Step 1: Ingestion
**File**: `ingestion/ingestion.py`  
**Input**: RSS feeds, API endpoints, URLs  
**Output**: `ingested_data/documents.parquet`

**What happens**:
1. Fetch articles from configured sources (Guardian, NPR, BBC, etc.)
2. Extract text content (title, body, metadata)
3. Generate unique document ID (MD5 hash of source:url)
4. Store in parquet format with schema:
   - id, source_id, title, author, published_at, raw_text, url, ingestion_metadata

**Key principle**: Raw text is **immutable** - no cleaning, no interpretation

### Step 2: Canonicalization
**File**: `canonicalization/canonicalization.py`  
**Input**: Documents from `documents.parquet`  
**Output**: List of `TextSegment` objects (in-memory)

**What happens**:
1. Load documents from parquet
2. For each document:
   - Normalize whitespace (collapse multiple spaces, normalize line breaks)
   - Split into paragraphs (by double newlines `\n\n`)
   - Filter short segments (< 100 chars)
   - Split long segments (> 2000 chars) into chunks
3. Create `TextSegment` objects:
   - id: MD5 hash of document_id:paragraph_index:segment_index
   - document_id: Links back to parent document
   - text: The segment text
   - position: Index in document

**Key principle**: Light, mechanical normalization - **no semantics**

**Example**:
```
Document (2000 words)
  ↓
  Split into paragraphs
  ↓
  TextSegment 0 (200 words)
  TextSegment 1 (400 words) ← Might match concept
  TextSegment 2 (300 words)
  TextSegment 3 (350 words) ← Might match concept
  TextSegment 4 (150 words)
```

### Step 3: Concept Assignment
**File**: `concept_assignment/concept_assignment.py`  
**Input**: Text segments + Concept definitions  
**Output**: List of `ConceptInstance` objects

**What happens** (for each segment):

1. **Load concept definition**:
   - Get concept from `concepts/concept_definitions.py`
   - Extract seed terms, inclusion/exclusion criteria

2. **Check exclusion criteria**:
   - Quick check if text should be excluded
   - (Currently lenient - mainly for future expansion)

3. **Calculate keyword score**:
   - Normalize text (lowercase, remove punctuation)
   - Check for seed term matches:
     - Exact phrase matches: "income inequality" in text
     - Multi-word partial: "income" and "gap" appear separately
     - Single-word matches: "inequality" appears
   - Score based on match count (logarithmic scale)

4. **Calculate embedding score** (if embeddings available):
   - Get or create concept embedding (cached)
   - Create text embedding using sentence-transformers
   - Calculate cosine similarity

5. **Combine scores**:
   - confidence = (keyword_weight * keyword_score) + (embedding_weight * embedding_score)
   - Default: 40% keyword, 60% embedding

6. **Check threshold**:
   - If confidence >= min_confidence → create ConceptInstance
   - Otherwise → skip

7. **Create ConceptInstance**:
   - concept_id: Which concept matched
   - text_segment_id: Which segment matched
   - confidence: Combined score
   - assignment_method: 'keyword', 'embedding', or 'hybrid'
   - metadata: Detailed scores, text preview, etc.

**Key principle**: Probabilistic and **revisable** - can re-run with different parameters

### Step 4: Save Results
**File**: `concept_assignment/test_concept_assignment.py`  
**Input**: Concept instances + text segments  
**Output**: `ingested_data/concept_instances.parquet`

**What happens**:
1. Convert ConceptInstance objects to dictionary
2. Add document_id from segment lookup
3. Create DataFrame with columns:
   - concept_id, text_segment_id, document_id
   - confidence, assignment_method
   - keyword_score, embedding_score
   - text_length, text_preview
4. Save to parquet

**Key principle**: Include document_id for easy joins and analysis

## Data Transformations

### Document → Segments
```
1 document (2000 words)
  ↓ canonicalize
5 segments (varying lengths)
```

### Segments → Concept Instances
```
5 segments
  ↓ assign concepts
2 concept instances (only 2 segments matched)
```

### Concept Instances → Analysis
```
2 concept instances
  ↓ join with documents
Analysis DataFrame with full context
```

## Example: Complete Flow

**Input**: Article from Guardian about economic policy

**Step 1 - Ingestion**:
```python
Document {
    id: "abc123...",
    source_id: "Guardian",
    title: "New Mayor Announces Economic Reforms",
    raw_text: "The new mayor... [2000 words]",
    published_at: "2026-01-02 12:00:00"
}
```

**Step 2 - Canonicalization**:
```python
TextSegment {
    id: "seg_abc123_0",
    document_id: "abc123...",
    text: "The new mayor announced plans to address...",
    position: 0
}
TextSegment {
    id: "seg_abc123_1",
    document_id: "abc123...",
    text: "The wealth gap between rich and poor...",
    position: 1
}
# ... more segments
```

**Step 3 - Concept Assignment**:
```python
# Segment 0: No match (confidence = 0.05 < 0.15) → Skip

# Segment 1: Match!
ConceptInstance {
    concept_id: "income_wealth_inequality",
    text_segment_id: "seg_abc123_1",
    confidence: 0.26,
    keyword_score: 0.65,
    embedding_score: 0.0,
    assignment_method: "hybrid"
}
```

**Step 4 - Save**:
```python
# concept_instances.parquet row:
{
    'concept_id': 'income_wealth_inequality',
    'text_segment_id': 'seg_abc123_1',
    'document_id': 'abc123...',  # ← Added for analysis
    'confidence': 0.26,
    'keyword_score': 0.65,
    'embedding_score': 0.0,
    ...
}
```

## Key Design Decisions

### Why Segment?
- Articles discuss multiple topics
- More precise matching
- Captures partial relevance

### Why Hybrid Scoring?
- Keyword: Fast, explicit
- Embedding: Semantic, flexible
- Combined: Best of both

### Why document_id in Instances?
- Easy joins for analysis
- Count documents per concept
- Group segments by document

### Why Parquet?
- Efficient storage
- Fast reads
- Columnar format (good for analysis)
- Preserves types (datetime, etc.)

## Performance Characteristics

- **Ingestion**: ~1-2 seconds per article (network dependent)
- **Canonicalization**: ~1000 documents/second
- **Keyword matching**: ~1000 segments/second
- **Embedding**: ~15-20 segments/second (CPU)
- **Overall**: ~50-100 segments/second (embedding is bottleneck)

## Regeneration Strategy

Following architecture principle: **Representations are regeneratable**

You can:
1. Re-run canonicalization with different parameters → new segments
2. Re-run concept assignment with different concepts → new instances
3. Re-run concept assignment with different thresholds → different instances

**Without re-ingesting** - raw documents stay the same!

## Next Steps (Future Layers)

### Representation Extraction (Section 3.4)
- Input: Concept instances
- Process: Generate embeddings, extract keywords, optional LLM summaries
- Output: Representation objects

### Comparative Analysis (Section 3.5)
- Input: Representations
- Process: Calculate similarities, clusters, temporal drift
- Output: Comparison results

### Views/Outputs (Section 3.6)
- Input: Comparison results
- Process: Generate visualizations, tables, dashboards
- Output: Human-readable outputs

