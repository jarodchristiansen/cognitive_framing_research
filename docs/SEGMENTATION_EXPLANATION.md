# Text Segmentation: Why and How

## Why We Segment Text

### The Problem

News articles often discuss **multiple topics** in a single piece. For example:

- An article about a new mayor might have:
  - Paragraph 1: Introduction to the mayor
  - Paragraph 2: Discussion of their economic policies (relevant to inequality)
  - Paragraph 3: Their stance on crime (not relevant)
  - Paragraph 4: More about economic inequality (relevant)
  - Paragraph 5: Conclusion

If we assign concepts at the **document level**, we'd have to decide: "Is this entire article about inequality?" The answer might be "partially" or "not really" - but we'd miss the relevant parts!

### The Solution: Segment-Level Assignment

By segmenting articles into paragraphs/chunks, we can:

1. **Capture partial relevance**: One paragraph might be highly relevant even if the article overall isn't
2. **More precise matching**: We match concepts to specific text segments, not entire articles
3. **Handle topic drift**: Articles often shift topics - segmentation lets us capture each topic separately

## How Segmentation Works

### Current Implementation

- **Segments by paragraphs**: Splits on double newlines (`\n\n`)
- **Minimum length**: 100 characters (filters out very short segments)
- **Maximum length**: 2000 characters (splits very long paragraphs)
- **Output**: Each segment gets its own `TextSegment` with:
  - Unique ID
  - Reference to parent document
  - Position in document
  - The text itself

### Example

A 2000-word article might become:

- Segment 0: Introduction (200 words)
- Segment 1: Economic policy discussion (400 words) ← Might match inequality concept
- Segment 2: Crime statistics (300 words)
- Segment 3: More economic discussion (350 words) ← Might also match inequality concept
- Segment 4: Conclusion (150 words)

## Why Same Article Appears Multiple Times

**This is expected and correct!**

If an article has multiple segments that discuss your concept, you'll get multiple concept instances. This is a **feature**, not a bug.

### Example from Your Results

Looking at your output:

- "13 questions for politics in 2026" appears **twice** (assignments #2 and #3)
- "US oil giants silent on Trump claim..." appears **twice** (assignments #5 and #8)
- "Mamdani pledges 'new era'..." appears **twice** (assignments #1 and #10)

This means:

- These articles have **multiple paragraphs** that discuss inequality-related topics
- Each relevant paragraph gets its own concept instance
- This gives you **more granular data** about how the concept appears

## How This Integrates Into Your Workflow

### Current Flow

1. **Ingestion**: Articles stored as complete documents
2. **Canonicalization**: Documents → Text Segments (paragraphs)
3. **Concept Assignment**: Segments → Concept Instances
4. **Analysis**: Concept Instances → Comparisons

### Benefits for Your Analysis

1. **Precision**: You can see exactly which parts of articles discuss inequality
2. **Context**: Each segment has its own embedding, so you can compare how different parts discuss the same concept
3. **Flexibility**: You can aggregate back to document level if needed, or keep segment-level granularity

### Example Use Cases

**Segment-Level Analysis:**

- "How do different paragraphs in the same article frame inequality differently?"
- "Which segments have the highest confidence scores?"

**Document-Level Analysis:**

- "How many articles discuss inequality?" (count unique documents)
- "Which sources cover inequality most?" (group by source)

## Architecture Alignment

This follows the architecture (section 3.2):

- **Canonicalization** is "light, mechanical" - no semantics
- **Segmentation** happens early, before concept assignment
- **Concept assignment** works on segments, not documents
- This allows **regeneration** - you can re-run assignment without re-ingesting

## When You Might Want Document-Level Instead

If you find that:

- Too many false positives from partial matches
- You want broader context (full article, not just paragraphs)
- Your concepts are very specific and need full article context

You could:

1. Adjust segmentation (larger chunks, or no segmentation)
2. Add a post-processing step to aggregate segments back to documents
3. Use document-level assignment (modify the code to work on full documents)

But for most cases, **segment-level is better** because it's more precise and flexible.

## Next Steps

Your current results show:

- 11 concept instances from multiple segments
- Some articles contributing multiple instances (expected!)
- Confidence scores ranging from 0.157 to 0.260

**Recommended actions:**

1. **Review the segments manually** - are they actually about inequality?
2. **Check if multiple segments from same article make sense** - do they discuss different aspects?
3. **Consider aggregation** - if you want document-level counts, you can group by document_id

The segmentation is working as designed! It's giving you more granular, precise matches.
