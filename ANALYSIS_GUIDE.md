# Analysis Guide

This guide explains the analysis layers we've scaffolded and how to use them.

## Overview

We've implemented three analysis layers following the architecture:

1. **Representation Extraction** (Section 3.4)
2. **Comparative Analysis** (Section 3.5)
3. **Views/Outputs** (Section 3.6)

## Architecture Alignment

These layers follow the architecture principles:

- **Regeneratable**: Can re-run with different models/parameters
- **Derived, not stored as truth**: Results are computed, not cached as final
- **Non-mutating**: Views never modify upstream data
- **Observational**: Show patterns, don't make judgments

## What We Built

### 1. Representation Extraction (`representation/`)

**Purpose**: Extract how a concept is represented (not what it means)

**What it does**:

- Generates embeddings for each concept instance
- Extracts keywords (top N most frequent words)
- Can be extended with LLM frame summaries

**Key Features**:

- Uses same embedding model as concept assignment
- Regeneratable - can swap models or parameters
- Extracts lexical features (keywords)

**Output**: `Representation` objects with:

- `concept_instance_id`: Links to concept instance
- `embedding`: Vector representation (384-dim for all-MiniLM-L6-v2)
- `keywords`: Top N keywords from the text
- `metadata`: Additional info (length, confidence, etc.)

### 2. Comparative Analysis (`analysis/`)

**Purpose**: Compare how different sources represent the same concept

**Analyses Implemented**:

#### a) Source-to-Source Similarity

- Calculates average embedding per source
- Computes pairwise cosine similarity
- Shows how similarly sources represent the concept

#### b) Lexical Patterns

- Extracts top keywords per source
- Shows what words each source uses
- Reveals language differences

#### c) Coverage Statistics

- Documents per source discussing the concept
- Segments per source
- Average confidence scores per source

**Output**: `ComparisonResult` objects with:

- `concept_id`: Which concept
- `sources`: Which sources compared
- `metric_type`: Type of analysis
- `values`: Results (similarity matrix, keyword lists, etc.)

### 3. Views/Outputs (`views/`)

**Purpose**: Generate human-readable outputs from analysis

**What it does**:

- Converts comparison results to tables
- Saves as CSV files
- Can be extended with charts/visualizations

**Outputs Generated**:

- `analysis_similarity_matrix.csv`: Source similarity matrix
- `analysis_lexical_patterns.csv`: Top keywords per source
- `analysis_coverage.csv`: Coverage statistics per source

## Usage

### Running Analysis

```bash
python run_analysis.py
```

This will:

1. Load concept instances and documents
2. Extract representations (embeddings, keywords)
3. Perform comparative analysis
4. Generate and save views

### What You'll Get

**Similarity Matrix**:
Shows how similar sources are in representing the concept (0-1 scale)

**Lexical Patterns**:
Shows top keywords each source uses when discussing the concept

**Coverage Statistics**:
Shows how much each source covers the concept (documents, segments, confidence)

## Example Outputs

### Similarity Matrix

```
source          Guardian    NPR    BBC_News
Guardian        1.000       0.75   0.68
NPR             0.75        1.000  0.72
BBC_News        0.68        0.72   1.000
```

### Lexical Patterns

```
source      rank  keyword        count
Guardian    1     inequality     15
Guardian    2     wealth         12
NPR         1     economic       8
NPR         2     gap            6
```

### Coverage Statistics

```
source      documents  segments  avg_confidence
Guardian    5          8          0.245
NPR         3          5          0.218
BBC_News    2          3          0.195
```

## What This Reveals

### Source Similarity

- **High similarity** (0.8+): Sources represent concept similarly
- **Low similarity** (0.5-): Sources emphasize different aspects
- **Very low** (<0.5): Sources discuss different things entirely

### Lexical Patterns

- **Common keywords**: Shared language across sources
- **Unique keywords**: Source-specific framing
- **Keyword frequency**: What each source emphasizes

### Coverage

- **Document count**: How many articles discuss the concept
- **Segment count**: How many segments match
- **Confidence**: How confident assignments are per source

## Limitations with Small Dataset

With only 50 documents:

- **Similarity**: May be noisy (few examples per source)
- **Lexical patterns**: Limited vocabulary diversity
- **Coverage**: May have sources with very few examples

**This is expected!** The analysis is scaffolded and will improve with more data.

## Next Steps

### With More Data

- **Temporal drift**: How representations change over time
- **Cluster formation**: Group similar representations
- **Frame overlap**: Identify common frames across sources

### Enhancements

- **Visualizations**: Charts, heatmaps, network graphs
- **Interactive exploration**: Jupyter notebooks
- **LLM frame summaries**: Optional summaries of how concept is framed

## Architecture Notes

### Regeneratable Layers

All analysis can be re-run:

- Change embedding model → re-run representation extraction
- Adjust analysis parameters → re-run comparative analysis
- Change visualization style → re-run views

**Without re-ingesting or re-assigning concepts!**

### Non-Judgmental

All analyses are **observational**:

- Show patterns, don't label sources
- Present data, don't interpret
- Surface structure, don't assert meaning

This aligns with the README principle: "Show structures; do not assert conclusions."
