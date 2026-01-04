# Data Schemas

This document describes the data structures used throughout the system, following the architecture's layered approach.

## Overview

The system uses a layered data architecture:

1. **Documents** (raw, immutable)
2. **Text Segments** (canonicalized)
3. **Concept Instances** (assigned)
4. **Representations** (future - embeddings, features)
5. **Comparisons** (future - derived analyses)

## 1. Document Schema

**Location**: `ingested_data/documents.parquet`  
**Layer**: Ingestion (Section 3.1)

```python
{
    'id': str,                    # MD5 hash of source_id:url
    'source_id': str,             # e.g., "Guardian", "NPR", "BBC_News"
    'title': str,                 # Article title
    'author': str,                # Author name(s), comma-separated
    'published_at': datetime,     # Publication timestamp (timezone-aware)
    'raw_text': str,              # Full article text (immutable, sacred)
    'url': str,                   # Original article URL
    'ingestion_metadata': str     # JSON string with ingestion details
}
```

**Key Principles**:

- `raw_text` is **immutable** - never modify it
- No semantic processing at this layer
- All fields are preserved as-is from source

## 2. Text Segment Schema

**Location**: In-memory (created during canonicalization)  
**Layer**: Canonicalization (Section 3.2)  
**Python Class**: `TextSegment`

```python
@dataclass
class TextSegment:
    id: str                       # MD5 hash of document_id:para_idx:seg_idx
    document_id: str              # Links back to parent document
    text: str                     # Segment text (normalized)
    position: int                 # Position in document (0-indexed)
    metadata: Dict[str, Any]      # Optional metadata (segmentation method, etc.)
```

**Key Principles**:

- One document → many segments (paragraphs)
- Segments are **regeneratable** - can re-segment without re-ingesting
- No semantics - just structural normalization

## 3. Concept Instance Schema

**Location**: `ingested_data/concept_instances.parquet`  
**Layer**: Concept Assignment (Section 3.3)  
**Python Class**: `ConceptInstance`

```python
@dataclass
class ConceptInstance:
    concept_id: str              # Which concept (e.g., "income_wealth_inequality")
    text_segment_id: str         # Which segment was assigned
    confidence: float            # Combined confidence score (0-1)
    assignment_method: str       # 'keyword', 'embedding', or 'hybrid'
    metadata: Dict[str, Any]      # Detailed scores and info
```

**Parquet Schema** (what gets saved):

```python
{
    'concept_id': str,           # Concept identifier
    'text_segment_id': str,      # Segment identifier
    'document_id': str,          # Parent document identifier (for analysis)
    'confidence': float,         # Combined confidence score (0-1)
    'assignment_method': str,    # 'keyword', 'embedding', or 'hybrid'
    'keyword_score': float,      # Raw keyword matching score (0-1)
    'embedding_score': float,    # Raw embedding similarity score (0-1)
    'text_length': int,          # Length of segment text
    'text_preview': str          # First 200 chars of segment
}
```

**Key Principles**:

- One segment can have multiple concept instances (if it matches multiple concepts)
- One document can have multiple concept instances (different segments match)
- `confidence` is the **combined score** used for threshold filtering
- `document_id` is included for easy joins with documents table

## 4. Concept Schema

**Location**: `concepts/concept_definitions.py`  
**Layer**: Concept Definition (Section 3.3)  
**Python Class**: `Concept`

```python
@dataclass
class Concept:
    id: str                      # Unique identifier
    name: str                    # Human-readable name
    description: str             # What the concept represents
    inclusion_criteria: List[str] # What should be included
    exclusion_criteria: List[str] # What should be excluded
    seed_terms: List[str]        # Terms for keyword matching
    metadata: Dict[str, Any]      # Version info, creation date, etc.
```

## Relationships

```
Document (1)
  ↓
  has many
  ↓
TextSegment (N)
  ↓
  can be assigned to
  ↓
ConceptInstance (M)
  ↑
  references
  ↑
Concept (1)
```

**Example**:

- 1 Document → 5 Text Segments
- 5 Text Segments → 2 Concept Instances (only 2 segments matched)
- Both Concept Instances reference the same Concept
- Both Concept Instances have the same `document_id` for easy grouping

## Data Flow

```
documents.parquet
  ↓ (load)
  Documents DataFrame
  ↓ (canonicalize)
  Text Segments (in-memory)
  ↓ (assign concepts)
  Concept Instances (in-memory)
  ↓ (save)
  concept_instances.parquet
```

## Analysis Queries

With `document_id` in concept_instances, you can easily:

```python
# Load both
documents = pd.read_parquet('ingested_data/documents.parquet')
instances = pd.read_parquet('ingested_data/concept_instances.parquet')

# Join for analysis
analysis = instances.merge(documents, on='document_id', how='left')

# Count documents per concept
doc_counts = instances.groupby('concept_id')['document_id'].nunique()

# Count segments per document
seg_counts = instances.groupby('document_id').size()

# Filter high-confidence instances
high_confidence = instances[instances['confidence'] > 0.5]
```

## Future Schemas

### Representation Schema (Section 3.4)

```python
{
    'concept_instance_id': str,
    'embedding': np.ndarray,     # Vector embedding
    'keywords': List[str],       # Extracted keywords
    'frame_summary': str,        # Optional LLM summary
    'metadata': Dict[str, Any]
}
```

### Comparison Result Schema (Section 3.5)

```python
{
    'concept_id': str,
    'sources': List[str],
    'metric_type': str,          # 'similarity', 'cluster', 'drift', etc.
    'values': Dict[str, float],  # Metric values
    'timestamp': datetime
}
```
