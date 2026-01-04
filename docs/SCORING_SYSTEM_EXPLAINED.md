# Scoring System Explained

This document explains how the concept assignment scoring system works, including keyword scores, embedding scores, and confidence scores.

## Overview

The system uses a **hybrid scoring approach** that combines:

1. **Keyword Matching** (explicit, fast)
2. **Embedding Similarity** (semantic, flexible)
3. **Combined Confidence Score** (weighted combination)

## 1. Keyword Score

### Purpose

Fast, explicit matching against seed terms. Answers: "Does this text contain the words/phrases we're looking for?"

### How It Works

1. **Normalize text**: Lowercase, remove punctuation
2. **Check for matches**:
   - Exact phrase matches: "income inequality" in text → match
   - Multi-word terms: All words appear (e.g., "income" and "gap" → partial match)
   - Single-word terms: Word appears in text → match
3. **Count matches**: How many seed terms matched?
4. **Calculate score**: Logarithmic scale based on match count

### Scoring Formula

```python
if matches == 0:
    score = 0.0
elif matches == 0.5:  # Single word match
    score = 0.15
elif matches == 1:
    score = 0.3
elif matches == 2:
    score = 0.5
elif matches == 3:
    score = 0.65
elif matches >= 4:
    score = 0.8 + min(0.2, (matches - 4) * 0.05)
```

### Example

**Text**: "The wealth gap between rich and poor has grown significantly."

**Seed terms checked**:

- "wealth gap" → ✅ Match (exact phrase)
- "income inequality" → ❌ No match
- "wealth" → ✅ Match (single word)
- "gap" → ✅ Match (single word)

**Result**: 1 exact phrase + 2 individual words = ~2 matches → **keyword_score = 0.5**

### Characteristics

- **Range**: 0.0 to 1.0
- **Fast**: No model inference needed
- **Explicit**: Based on exact word matches
- **Can miss**: Synonyms or related concepts not in seed terms

## 2. Embedding Score

### Purpose

Semantic similarity using neural embeddings. Answers: "Is this text semantically similar to our concept, even if it doesn't use exact words?"

### How It Works

1. **Create concept embedding**:

   - Combine concept description + inclusion criteria + seed terms
   - Encode into a vector using sentence-transformers model
   - Cache this embedding (computed once per concept)

2. **Create text embedding**:

   - Encode the text segment into a vector
   - Uses same model (all-MiniLM-L6-v2 by default)

3. **Calculate similarity**:
   - Cosine similarity between concept embedding and text embedding
   - Returns value between -1 and 1 (typically 0 to 1 for text)

### Scoring Formula

```python
# Cosine similarity
similarity = dot(concept_embedding, text_embedding) / (
    norm(concept_embedding) * norm(text_embedding)
)

# Normalize to 0-1 range
embedding_score = max(0.0, similarity)
```

### Example

**Concept**: "Income and Wealth Inequality"  
**Text**: "The economic divide between affluent and impoverished communities continues to widen."

**Process**:

1. Concept embedding: [0.2, -0.1, 0.5, ...] (384 dimensions)
2. Text embedding: [0.18, -0.12, 0.48, ...] (384 dimensions)
3. Cosine similarity: 0.82
4. **embedding_score = 0.82**

### Characteristics

- **Range**: 0.0 to 1.0 (typically 0.0 to 0.9 for text)
- **Slower**: Requires model inference
- **Semantic**: Understands meaning, not just words
- **Can catch**: Related concepts, synonyms, paraphrases

## 3. Confidence Score (Combined)

### Purpose

Final score that determines if a segment should be assigned to a concept. Combines keyword and embedding scores with weights.

### How It Works

```python
if embeddings_available:
    confidence = (keyword_weight * keyword_score) + (embedding_weight * embedding_score)
    method = 'hybrid'
else:
    confidence = keyword_score
    method = 'keyword'
```

### Default Weights

- **keyword_weight**: 0.4 (40%)
- **embedding_weight**: 0.6 (60%)
- **min_confidence**: 0.15 (threshold for assignment)

### Example

**Text segment**:

- keyword_score = 0.5
- embedding_score = 0.3

**Calculation**:

```
confidence = (0.4 * 0.5) + (0.6 * 0.3)
           = 0.2 + 0.18
           = 0.38
```

**Result**: confidence = 0.38 > 0.15 threshold → **ASSIGNED** ✅

### Why This Combination?

1. **Keyword score** catches explicit mentions (high precision)
2. **Embedding score** catches semantic similarity (high recall)
3. **Combined** balances both strengths

### Characteristics

- **Range**: 0.0 to 1.0
- **Determines assignment**: Must exceed `min_confidence` threshold
- **Tunable**: Adjust weights based on your needs

## Understanding Your Results

### Example from Your Output

```
[1] Confidence: 0.260 (hybrid)
    Keyword score: 0.650
    Embedding score: 0.000
```

**What this means**:

- High keyword match (0.65) - text contains many seed terms
- Low embedding match (0.0) - semantically not very similar
- Combined: 0.4 _ 0.65 + 0.6 _ 0.0 = 0.26
- **Interpretation**: Text explicitly mentions inequality terms, but may not be deeply about the concept

```
[2] Confidence: 0.229 (hybrid)
    Keyword score: 0.300
    Embedding score: 0.182
```

**What this means**:

- Moderate keyword match (0.30) - some seed terms found
- Moderate embedding match (0.182) - some semantic similarity
- Combined: 0.4 _ 0.30 + 0.6 _ 0.182 = 0.229
- **Interpretation**: Balanced match - both explicit and semantic signals

## Tuning the System

### Adjust Keyword Weight

- **Higher keyword_weight** (e.g., 0.7): Prefer explicit mentions
- **Lower keyword_weight** (e.g., 0.2): Prefer semantic similarity

### Adjust Embedding Weight

- **Higher embedding_weight** (e.g., 0.8): More flexible, catches related concepts
- **Lower embedding_weight** (e.g., 0.3): More strict, requires explicit terms

### Adjust Threshold

- **Higher min_confidence** (e.g., 0.4): Fewer assignments, higher precision
- **Lower min_confidence** (e.g., 0.1): More assignments, higher recall

### When to Adjust

**Too many false positives?**

- Raise `min_confidence`
- Increase `keyword_weight` (prefer explicit matches)
- Add more exclusion criteria

**Too many false negatives?**

- Lower `min_confidence`
- Increase `embedding_weight` (catch semantic matches)
- Add more seed terms

## Common Patterns

### High Keyword, Low Embedding

- Text explicitly mentions terms but isn't really about the concept
- **Action**: Review manually, may need exclusion criteria

### Low Keyword, High Embedding

- Text is semantically related but doesn't use exact terms
- **Action**: Consider adding synonyms to seed terms

### Both High

- Strong match - likely a good assignment
- **Action**: Use as positive example

### Both Low

- Weak match - correctly filtered out
- **Action**: None needed

## Technical Details

### Embedding Model

- **Model**: all-MiniLM-L6-v2
- **Dimensions**: 384
- **Speed**: ~15-20 segments/second on CPU
- **Quality**: Good balance of speed and accuracy

### Keyword Matching

- **Case-insensitive**: All matching is lowercase
- **Punctuation-agnostic**: Punctuation removed before matching
- **Partial matching**: Individual words from multi-word terms count

### Performance

- **Keyword matching**: ~1000 segments/second
- **Embedding**: ~15-20 segments/second
- **Combined**: Limited by embedding speed

## Summary

- **Keyword Score**: Explicit word matching (0-1)
- **Embedding Score**: Semantic similarity (0-1)
- **Confidence Score**: Weighted combination (0-1)
- **Assignment**: If confidence > threshold → assigned

The system is designed to be **tunable** - adjust weights and thresholds based on your validation results.
