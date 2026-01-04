# Concept Assignment Guide

This guide explains how to use the concept assignment system we've built.

## Overview

We've implemented the **Concept Assignment Layer** (Architecture section 3.3), which is the "highest-risk and highest-value layer" of the system.

## What We Built

### 1. Concept Definition (`concepts/concept_definitions.py`)

Defined the first concept: **Income and Wealth Inequality**

- **ID**: `income_wealth_inequality`
- **Description**: Discussions of income and wealth inequality, including disparities in earnings, assets, economic opportunity, and distribution of resources
- **Inclusion Criteria**: 8 explicit criteria for what should be included
- **Exclusion Criteria**: 5 explicit criteria for what should be excluded
- **Seed Terms**: 30+ relevant terms for keyword matching

### 2. Canonicalization Layer (`canonicalization.py`)

Light, mechanical text normalization:

- Normalizes whitespace
- Segments documents into paragraphs/chunks
- Outputs `TextSegment` objects ready for concept assignment

### 3. Concept Assignment Layer (`concept_assignment.py`)

Hybrid assignment strategy:

- **Keyword matching**: Fast, explicit matching against seed terms
- **Embedding similarity**: Semantic similarity using sentence-transformers
- **Combined scoring**: Weighted combination of both methods
- **Threshold-based inclusion**: Only includes segments above confidence threshold

### 4. Test Script (`test_concept_assignment.py`)

Runs the full pipeline:

1. Loads documents from `ingested_data/documents.parquet`
2. Canonicalizes into text segments
3. Assigns concepts
4. Displays results for manual validation
5. Saves results to `ingested_data/concept_instances.parquet`

## Usage

### First Time Setup

1. Install dependencies (if not already installed):

```bash
pip install sentence-transformers torch
```

Note: The system will work without sentence-transformers (keyword-only mode), but embeddings improve accuracy.

### Running Concept Assignment

```bash
python test_concept_assignment.py
```

This will:

- Process all documents in `ingested_data/documents.parquet`
- Assign the income/wealth inequality concept to relevant segments
- Display top 10 assignments with confidence scores
- Save all assignments to `ingested_data/concept_instances.parquet`

### Understanding Results

The output shows:

- **Confidence score**: Combined keyword + embedding score (0-1)
- **Assignment method**: `keyword`, `embedding`, or `hybrid`
- **Source**: Which news source the segment came from
- **Text preview**: First 300 characters of the segment
- **Individual scores**: Keyword and embedding scores separately

### Adjusting Parameters

You can modify assignment behavior in `test_concept_assignment.py`:

```python
assigner = ConceptAssigner(
    min_confidence=0.4,      # Lower = more assignments (more false positives)
    keyword_weight=0.4,       # Weight for keyword matching
    embedding_weight=0.6,      # Weight for embedding similarity
    use_embeddings=True        # Set to False for keyword-only
)
```

## Next Steps (Architecture Iteration Loop)

1. **Review Results**: Manually inspect the displayed assignments
2. **Validate Samples**: Check if assignments are correct
3. **Adjust Concept Definition**: Refine inclusion/exclusion criteria or seed terms
4. **Tune Parameters**: Adjust confidence thresholds and weights
5. **Re-run**: Iterate until assignments are satisfactory

## Adding New Concepts

To add a new concept, edit `concepts/concept_definitions.py`:

```python
'new_concept_id': Concept(
    id='new_concept_id',
    name='Concept Name',
    description='Detailed description...',
    inclusion_criteria=[...],
    exclusion_criteria=[...],
    seed_terms=[...]
)
```

Then update `test_concept_assignment.py` to include it:

```python
concept_ids = ['income_wealth_inequality', 'new_concept_id']
```

## Architecture Alignment

This implementation follows the architecture principles:

✅ **Separate layers**: Ingestion → Canonicalization → Assignment → (next: Representation)  
✅ **Regeneratable**: Can re-run assignment without re-ingesting  
✅ **Probabilistic**: Confidence scores, not binary decisions  
✅ **Revisable**: Easy to adjust concepts and parameters  
✅ **Human-in-the-loop**: Manual validation expected

## Troubleshooting

**No assignments found?**

- Lower `min_confidence` threshold
- Check if documents contain relevant content
- Review concept seed terms

**Too many false positives?**

- Raise `min_confidence` threshold
- Add more exclusion criteria
- Refine seed terms

**Embeddings not working?**

- Install: `pip install sentence-transformers torch`
- System will fall back to keyword-only mode automatically

## Files Created

- `concepts/__init__.py` - Concept module initialization
- `concepts/concept_definitions.py` - Concept definitions
- `canonicalization.py` - Text segmentation layer
- `concept_assignment.py` - Concept assignment logic
- `test_concept_assignment.py` - Test/usage script
- `ingested_data/concept_instances.parquet` - Output (created when run)
