# Maintenance Guide

Quick reference for maintaining and extending the system.

## Data Schema Updates

### ✅ Added `document_id` to Concept Instances

**What changed**:

- `concept_instances.parquet` now includes `document_id` column
- Enables easy joins with `documents.parquet` for analysis
- Updated `save_results()` function to include document_id

**Usage**:

```python
import pandas as pd

# Load both
documents = pd.read_parquet('ingested_data/documents.parquet')
instances = pd.read_parquet('ingested_data/concept_instances.parquet')

# Join for analysis
analysis = instances.merge(documents, on='document_id', how='left')

# Count unique documents per concept
doc_counts = instances.groupby('concept_id')['document_id'].nunique()
```

## Understanding the Scoring System

### Three Types of Scores

1. **Keyword Score** (0.0 - 1.0)

   - Explicit word/phrase matching
   - Fast, precise
   - Based on seed terms in concept definition
   - See `_keyword_match_score()` method

2. **Embedding Score** (0.0 - 1.0)

   - Semantic similarity using neural embeddings
   - Slower, more flexible
   - Catches related concepts even without exact words
   - See `_embedding_similarity_score()` method

3. **Confidence Score** (0.0 - 1.0)
   - Combined score: `(keyword_weight * keyword_score) + (embedding_weight * embedding_score)`
   - Default: 40% keyword, 60% embedding
   - Used for threshold filtering
   - See `assign_concept()` method

### Score Interpretation

**High keyword, low embedding** (e.g., 0.65, 0.0):

- Text explicitly mentions terms but may not be deeply about the concept
- Action: Review manually, may need exclusion criteria

**Low keyword, high embedding** (e.g., 0.3, 0.6):

- Text is semantically related but doesn't use exact terms
- Action: Consider adding synonyms to seed terms

**Both high** (e.g., 0.5, 0.7):

- Strong match - likely a good assignment
- Action: Use as positive example

**Both low** (e.g., 0.1, 0.1):

- Weak match - correctly filtered out
- Action: None needed

## Key Code Locations

### Core Assignment Logic

- **File**: `concept_assignment/concept_assignment.py`
- **Class**: `ConceptAssigner`
- **Key Method**: `assign_concept()` - Main assignment function
  - Line 274-325: Complete assignment logic with detailed comments

### Scoring Methods

- **Keyword**: `_keyword_match_score()` - Line 121-203
- **Embedding**: `_embedding_similarity_score()` - Line 224-250
- **Combined**: Calculated in `assign_concept()` - Line 297-301

### Data Structures

- **ConceptInstance**: `concept_assignment/concept_assignment.py` - Line 48-63
- **TextSegment**: `canonicalization/canonicalization.py` - Line 20-30
- **Concept**: `concepts/concept_definitions.py` - Line 19-46

## Common Maintenance Tasks

### Adjusting Assignment Threshold

**File**: `concept_assignment/test_concept_assignment.py`  
**Line**: ~79

```python
assigner = ConceptAssigner(
    min_confidence=0.15,  # ← Adjust this
    use_embeddings=True
)
```

- **Lower** (e.g., 0.1): More assignments, higher recall, lower precision
- **Higher** (e.g., 0.3): Fewer assignments, lower recall, higher precision

### Adjusting Score Weights

**File**: `concept_assignment/test_concept_assignment.py`  
**Line**: ~79

```python
assigner = ConceptAssigner(
    keyword_weight=0.4,   # ← Adjust keyword importance
    embedding_weight=0.6,  # ← Adjust embedding importance
    min_confidence=0.15
)
```

- **More keyword weight**: Prefer explicit mentions
- **More embedding weight**: Prefer semantic similarity

### Adding a New Concept

**File**: `concepts/concept_definitions.py`  
**Line**: ~50 (in CONCEPTS dictionary)

```python
'new_concept_id': Concept(
    id='new_concept_id',
    name='Concept Name',
    description='...',
    inclusion_criteria=[...],
    exclusion_criteria=[...],
    seed_terms=[...]
)
```

Then update test script to include it:
**File**: `concept_assignment/test_concept_assignment.py`  
**Line**: ~187

```python
concept_ids = ['income_wealth_inequality', 'new_concept_id']
```

## Documentation Files

All documentation is in the project root:

1. **DOCUMENTATION_INDEX.md** - Master index of all docs
2. **SYSTEM_FLOW.md** - End-to-end data flow
3. **DATA_SCHEMAS.md** - Data structure reference
4. **SCORING_SYSTEM_EXPLAINED.md** - Detailed scoring explanation
5. **SEGMENTATION_EXPLANATION.md** - Why we segment text
6. **SAMPLE_SIZE_NOTES.md** - Corpus size guidance

## Testing and Validation

### Run Assignment Test

```bash
py concept_assignment/test_concept_assignment.py
```

### Check Results

```python
import pandas as pd

# Load results
instances = pd.read_parquet('ingested_data/concept_instances.parquet')
documents = pd.read_parquet('ingested_data/documents.parquet')

# Join for analysis
df = instances.merge(documents, on='document_id', how='left')

# Review assignments
print(df[['title', 'confidence', 'keyword_score', 'embedding_score']].head(10))
```

## Troubleshooting

### No Assignments

- Check if documents contain seed terms
- Lower `min_confidence` threshold
- Add more seed terms to concept definition
- Check if embeddings are working (should see "hybrid" method)

### Too Many False Positives

- Raise `min_confidence` threshold
- Increase `keyword_weight` (prefer explicit matches)
- Add exclusion criteria to concept definition

### Too Many False Negatives

- Lower `min_confidence` threshold
- Increase `embedding_weight` (catch semantic matches)
- Add synonyms to seed terms

### Import Errors

- Ensure running from project root or concept_assignment directory
- Check that `__init__.py` files exist in all package directories
- Verify sys.path manipulation in module files

## Code Comments

All key methods now have detailed docstrings explaining:

- What the method does
- Parameters and return values
- Examples
- How it fits into the overall flow

Key methods with comprehensive comments:

- `assign_concept()` - Main assignment logic
- `_keyword_match_score()` - Keyword matching
- `_embedding_similarity_score()` - Semantic similarity

## Next Steps

When ready to expand:

1. Review validation results
2. Adjust concept definitions based on findings
3. Expand corpus (more documents, more sources)
4. Build Representation Extraction layer (Section 3.4)
5. Build Comparative Analysis layer (Section 3.5)
