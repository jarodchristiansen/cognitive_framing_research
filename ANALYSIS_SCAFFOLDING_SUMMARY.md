# Analysis Scaffolding Summary

## What We Built

We've scaffolded the complete analysis pipeline following the architecture (sections 3.4, 3.5, 3.6) to work with your current small dataset before expanding ingestion.

## Architecture Alignment

### ✅ Representation Extraction (Section 3.4)

**File**: `representation/representation_extraction.py`

- Extracts embeddings for each concept instance
- Extracts keywords (top N words per segment)
- Regeneratable - can swap models/parameters
- Output: `Representation` objects

### ✅ Comparative Analysis (Section 3.5)

**File**: `analysis/comparative_analysis.py`

Three analyses implemented:

1. **Source-to-source similarity**: How similarly sources represent the concept
2. **Lexical patterns**: What words each source uses
3. **Coverage statistics**: How much each source covers the concept

Output: `ComparisonResult` objects

### ✅ Views/Outputs (Section 3.6)

**File**: `views/view_generator.py`

- Converts comparison results to tables
- Saves as CSV files
- Non-mutating (never modifies upstream data)
- Can be extended with charts/visualizations

## Files Created

```
representation/
  __init__.py
  representation_extraction.py

analysis/
  __init__.py
  comparative_analysis.py

views/
  __init__.py
  view_generator.py

run_analysis.py          # Main script to run all analyses
ANALYSIS_GUIDE.md        # Usage guide
```

## What This Enables

With your current 50-document dataset, you can now:

1. **See source differences**: How Guardian, NPR, BBC represent inequality differently
2. **Identify language patterns**: What words each source emphasizes
3. **Compare coverage**: Which sources discuss the concept more
4. **Validate approach**: Test the analysis pipeline before expanding

## Usage

```bash
# Run all analyses
python run_analysis.py
```

This will:

1. Load concept instances and documents
2. Extract representations (embeddings, keywords)
3. Perform comparative analysis
4. Generate CSV tables in `analysis_output/`

## Output Files

- `analysis_similarity_matrix.csv`: Source similarity scores
- `analysis_lexical_patterns.csv`: Top keywords per source
- `analysis_coverage.csv`: Coverage statistics per source

## Key Principles Maintained

✅ **Regeneratable**: Can re-run with different models/parameters  
✅ **Observational**: Shows patterns, doesn't make judgments  
✅ **Non-mutating**: Views never modify upstream data  
✅ **Transparent**: All calculations are explicit and inspectable

## Next Steps

### With Current Dataset

1. Run `python run_analysis.py`
2. Review the CSV outputs
3. Validate that the analysis makes sense
4. Adjust parameters if needed

### Before Expanding Ingestion

- ✅ Analysis pipeline is scaffolded
- ✅ Can test on small dataset
- ✅ Understand what insights you'll get
- ✅ Validate the approach works

### After Expanding Ingestion

- More robust similarity calculations
- Temporal drift analysis (with time-series data)
- Cluster formation (with more examples)
- Enhanced visualizations

## Architecture Compliance

This implementation follows the architecture exactly:

1. **Separate layers**: Each layer has single responsibility
2. **Clear contracts**: Input/output schemas defined
3. **Regeneratable**: Can re-run without re-ingesting
4. **Derived outputs**: Results computed, not stored as truth
5. **Non-judgmental**: Observational, not interpretive

## What's Missing (Future Enhancements)

- **Temporal drift**: Need more time-series data
- **Cluster formation**: Need more examples per source
- **LLM frame summaries**: Optional enhancement
- **Visualizations**: Charts, heatmaps (can add with matplotlib/plotly)
- **Interactive exploration**: Jupyter notebooks

But the **scaffolding is complete** - you can test the pipeline now and expand later!
