# Sample Size Considerations

## Current Status

- **52 documents** ingested (from your test run)
- **~2 days** of articles from NPR, Guardian, BBC-News
- **185 text segments** created from canonicalization

## Is 50 Documents Enough?

**Short answer: It depends on your goal, but it's a good starting point.**

### For Initial Concept Validation: ✅ YES

- 50 documents is **sufficient** for:
  - Testing concept assignment logic
  - Validating that your concept definition works
  - Understanding what kind of content you're capturing
  - Refining inclusion/exclusion criteria
  - Tuning confidence thresholds

### For Meaningful Analysis: ⚠️ PROBABLY NOT

- 50 documents (2 days) is **likely insufficient** for:
  - Cross-source comparison (need more sources and time)
  - Temporal drift analysis (need weeks/months of data)
  - Pattern discovery (need more examples)
  - Statistical significance

## Recommended Approach

### Phase 1: Validation (Current - 50-100 docs)

**Goal**: Make sure the system works

- ✅ Test concept assignment
- ✅ Validate assignments manually
- ✅ Refine concept definitions
- ✅ Tune parameters

### Phase 2: Expansion (100-500 docs)

**Goal**: Build a meaningful corpus for your concept

- Expand to **2-4 weeks** of articles
- Target sources that cover your concept
- Use concept assignment to filter during ingestion (future optimization)

### Phase 3: Analysis (500+ docs)

**Goal**: Generate insights

- Cross-source comparison
- Temporal analysis
- Pattern discovery

## Strategy for Your Income/Wealth Inequality Concept

Since you're targeting a specific concept, you have two options:

### Option A: Broad Collection, Filter Later

- Collect general news (as you're doing now)
- Use concept assignment to filter relevant segments
- **Pros**: Simple, captures context
- **Cons**: More data to process, many irrelevant articles

### Option B: Targeted Collection (Future Enhancement)

- Pre-filter during ingestion using keywords
- Only fetch articles likely to be relevant
- **Pros**: More efficient, focused corpus
- **Cons**: Might miss edge cases, requires keyword tuning

## Recommendation

**For now (Phase 1):**

1. ✅ Keep your current 50-document corpus
2. ✅ Run concept assignment and validate results
3. ✅ Refine concept definition based on what you find
4. ✅ Once validated, expand to 2-4 weeks of data

**Next steps:**

- After validation, expand ingestion to get 200-500 documents
- Focus on sources that regularly cover economic topics
- Consider adding more sources (AP News, NYT, etc.)

## The Architecture Advantage

Remember: The architecture is designed for this iterative approach:

- **Raw content is immutable** - you can always re-run assignment
- **Representations are regeneratable** - change concepts without re-ingesting
- **Comparisons are iterative** - start small, expand as needed

So starting with 50 documents is exactly the right approach! Validate your concept definition first, then expand.
