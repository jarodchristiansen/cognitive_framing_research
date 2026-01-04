# Documentation Index

Complete guide to understanding and maintaining the Cognitive Representation Mapping System.

## Core Documentation

### 1. [README.md](README.md)

**Purpose**: Project overview, philosophy, and principles  
**Read this first** to understand what the system is and isn't.

### 2. [architecture.md](architecture.md)

**Purpose**: System architecture and design decisions  
**Key sections**:

- Section 3.3: Concept Assignment (highest-risk layer)
- Section 4: Known pain points and mitigations
- Section 6: Expected iteration loop

### 3. [SYSTEM_FLOW.md](SYSTEM_FLOW.md)

**Purpose**: End-to-end data flow explanation  
**Covers**: How data moves from ingestion → canonicalization → assignment → analysis

### 4. [DATA_SCHEMAS.md](DATA_SCHEMAS.md)

**Purpose**: Complete data structure reference  
**Covers**: Document, TextSegment, ConceptInstance, Concept schemas and relationships

### 5. [SCORING_SYSTEM_EXPLAINED.md](SCORING_SYSTEM_EXPLAINED.md)

**Purpose**: Understanding the scoring system  
**Covers**: Keyword scores, embedding scores, confidence scores, and how they combine

## Component-Specific Documentation

### 6. [SEGMENTATION_EXPLANATION.md](SEGMENTATION_EXPLANATION.md)

**Purpose**: Why we segment text and how it works  
**Covers**: Topic leakage, paragraph-level assignment, multiple instances per document

### 7. [SAMPLE_SIZE_NOTES.md](SAMPLE_SIZE_NOTES.md)

**Purpose**: Guidance on corpus size  
**Covers**: When 50 documents is enough, when to expand, recommended approach

### 8. [concepts/CONCEPT_ASSIGNMENT_GUIDE.md](concepts/CONCEPT_ASSIGNMENT_GUIDE.md)

**Purpose**: How to use the concept assignment system  
**Covers**: Running tests, adjusting parameters, adding concepts

## Code Files (with inline documentation)

### Ingestion Layer

- `ingestion/ingestion.py`: Fetches articles from sources, stores in parquet
- `ingestion/test_ingestion.py`: Tests ingestion functionality

### Canonicalization Layer

- `canonicalization/canonicalization.py`: Text normalization and segmentation
  - `TextCanonicalizer`: Main class for segmentation
  - `TextSegment`: Data structure for segments

### Concept Assignment Layer

- `concept_assignment/concept_assignment.py`: Core assignment logic
  - `ConceptAssigner`: Main assignment class
  - `ConceptInstance`: Assignment result structure
  - Key methods:
    - `assign_concept()`: Assigns one segment to one concept
    - `_keyword_match_score()`: Calculates keyword matching
    - `_embedding_similarity_score()`: Calculates semantic similarity
- `concept_assignment/test_concept_assignment.py`: Test and usage script

### Concept Definitions

- `concepts/concept_definitions.py`: Concept definitions
  - `Concept`: Concept data structure
  - `CONCEPTS`: Dictionary of all defined concepts

## Key Concepts to Understand

### 1. Layered Architecture

- **Raw content** (immutable) → **Representations** (regeneratable) → **Comparisons** (iterative) → **Views** (ephemeral)
- Each layer can be regenerated without affecting previous layers

### 2. Segmentation

- Documents split into paragraphs for precise matching
- One document → many segments → potentially many concept instances
- See [SEGMENTATION_EXPLANATION.md](SEGMENTATION_EXPLANATION.md)

### 3. Hybrid Scoring

- **Keyword score**: Explicit word matching (fast, precise)
- **Embedding score**: Semantic similarity (slower, flexible)
- **Confidence score**: Weighted combination (40% keyword, 60% embedding)
- See [SCORING_SYSTEM_EXPLAINED.md](SCORING_SYSTEM_EXPLAINED.md)

### 4. Probabilistic Assignment

- Assignments have confidence scores (0-1)
- Threshold-based inclusion (default: 0.15)
- Can be tuned and re-run without re-ingesting

## Common Tasks

### Adding a New Concept

1. Edit `concepts/concept_definitions.py`
2. Add new `Concept` to `CONCEPTS` dictionary
3. Define: id, name, description, inclusion/exclusion criteria, seed terms
4. Run `concept_assignment/test_concept_assignment.py` with new concept_id

### Adjusting Assignment Parameters

1. Edit `concept_assignment/test_concept_assignment.py`
2. Modify `ConceptAssigner` initialization:
   - `min_confidence`: Threshold (lower = more assignments)
   - `keyword_weight`: Weight for keyword matching (0-1)
   - `embedding_weight`: Weight for embeddings (0-1)
3. Re-run assignment

### Understanding Results

1. Check `ingested_data/concept_instances.parquet`
2. Review confidence scores, keyword scores, embedding scores
3. Join with `documents.parquet` using `document_id` for full context
4. See [SCORING_SYSTEM_EXPLAINED.md](SCORING_SYSTEM_EXPLAINED.md) for score interpretation

### Expanding Corpus

1. Run `ingestion/ingestion.py` to fetch more articles
2. Re-run concept assignment (no need to re-ingest)
3. See [SAMPLE_SIZE_NOTES.md](SAMPLE_SIZE_NOTES.md) for guidance

## Troubleshooting

### No Assignments Found

- Check: Do documents contain seed terms? (run diagnostic scripts)
- Solution: Lower threshold, add more seed terms, or expand corpus

### Too Many False Positives

- Check: Are keyword scores high but embedding scores low?
- Solution: Raise threshold, increase embedding_weight, add exclusion criteria

### Too Many False Negatives

- Check: Are embedding scores high but keyword scores low?
- Solution: Lower threshold, add synonyms to seed terms, increase embedding_weight

### Import Errors

- Check: Project root in sys.path? Run from project root?
- Solution: See import path setup in each module

## Next Steps (Future Layers)

### Representation Extraction (Section 3.4)

- Generate embeddings for concept instances
- Extract keywords and features
- Optional LLM-assisted frame summaries

### Comparative Analysis (Section 3.5)

- Source-to-source similarity
- Cluster formation
- Temporal drift analysis
- Frame overlap

### Views/Outputs (Section 3.6)

- Tables and charts
- Semantic distance matrices
- Interactive dashboards

## Maintenance Checklist

When maintaining or extending the system:

- [ ] Understand the layered architecture
- [ ] Know where each data structure is defined
- [ ] Understand the scoring system
- [ ] Know how to add/modify concepts
- [ ] Know how to adjust parameters
- [ ] Understand segmentation and why it's used
- [ ] Know how to regenerate layers without re-ingesting
- [ ] Understand the data schemas and relationships

## Quick Reference

**Data Files**:

- `ingested_data/documents.parquet`: Raw articles
- `ingested_data/concept_instances.parquet`: Concept assignments

**Key Classes**:

- `DocumentIngester`: Ingests articles
- `TextCanonicalizer`: Segments documents
- `ConceptAssigner`: Assigns concepts
- `Concept`: Concept definition
- `ConceptInstance`: Assignment result

**Key Parameters**:

- `min_confidence`: Assignment threshold (default: 0.15)
- `keyword_weight`: Keyword score weight (default: 0.4)
- `embedding_weight`: Embedding score weight (default: 0.6)

**Key Methods**:

- `assign_concept()`: Core assignment logic
- `_keyword_match_score()`: Keyword matching
- `_embedding_similarity_score()`: Semantic similarity
