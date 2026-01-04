1. Core Architectural Philosophy

Before components, a principle:

Separate “what the text is” from “how we interpret it.”

If you blur these early, you will constantly reprocess everything when assumptions change.

So the system is layered as:

Raw content (immutable)

Representations (regeneratable)

Comparisons (iterative)

Views (ephemeral)

This separation is the backbone of the project.

2. High-Level System Layers
   [ Sources ]
   ↓
   [ Ingestion & Canonicalization ]
   ↓
   [ Concept Assignment ]
   ↓
   [ Representation Extraction ]
   ↓
   [ Comparative Analysis ]
   ↓
   [ Views / Outputs ]

Each layer has a single responsibility and a clear contract.

3. Layer-by-Layer Breakdown (High → Mid Level)
   3.1 Source & Ingestion Layer

Responsibility:
Get text into the system without interpretation.

Key idea:
Ingestion should be dumb, repeatable, and reversible.

Inputs

RSS feeds

Manually added URLs

Public transcripts

Saved documents

Output: Document

Minimal schema:

Document {
id
source_id
title
author
published_at
raw_text
url
ingestion_metadata
}

Important:

Do not infer topics here

Do not clean aggressively

Do not summarize

Raw text is sacred.

3.2 Canonicalization (Light, Mechanical)

Responsibility:
Normalize text for downstream processing.

Examples:

Remove boilerplate

Normalize whitespace

Segment into paragraphs or chunks

Output: TextSegment

TextSegment {
id
document_id
text
position
}

No semantics yet. This stage is intentionally boring.

3.3 Concept Definition & Assignment (This Is Where Iteration Happens)

This is the highest-risk and highest-value layer.

Concept Object
Concept {
id
name
description
inclusion_criteria
exclusion_criteria
seed_terms
}

Concepts are:

Few (start with 2–5)

Explicit

Human-defined

Assignment Strategy (MVP)

Hybrid approach:

Keyword + embedding similarity

Human validation loop

Threshold-based inclusion

Output: ConceptInstance

ConceptInstance {
concept_id
text_segment_id
confidence
}

Important constraint:
Concept assignment is probabilistic and revisable.

You will change this logic later. That’s expected.

3.4 Representation Extraction Layer

Responsibility:
Extract how a concept is represented, not what it means.

For each ConceptInstance, compute:

Embeddings

Lexical features

Optional LLM-assisted frame summaries

Schema:

Representation {
concept_instance_id
embedding
keywords
frame_summary (optional)
metadata
}

Key rule:

Everything here is regeneratable.

This allows you to:

Swap models

Tune parameters

Re-run analyses without re-ingesting data

3.5 Comparative Analysis Layer

This is where insight starts.

Analyses include:

Source-to-source similarity

Cluster formation

Temporal drift

Frame overlap

Output objects are derived, not stored as truth.

Example:

ComparisonResult {
concept_id
sources
metric_type
values
}

This layer is where experimentation lives.

3.6 Views / Output Layer

These are:

Tables

Charts

Matrices

Interactive dashboards (later)

They should:

Read from comparison outputs

Never mutate upstream data

Views are disposable.

4. Where Data Ingestion Will Be Problematic (And How We Handle It)

You’re right to anticipate this. Here are the known pain points:

4.1 Topic Leakage

Articles drift across concepts.

Mitigation:

Segment text early

Assign at paragraph-level

Accept partial coverage

4.2 Source Heterogeneity

Different writing styles break naïve assumptions.

Mitigation:

Treat source as metadata, not signal

Avoid per-source normalization early

4.3 Over-Inclusion

Early keyword filters will be sloppy.

Mitigation:

Log false positives

Adjust thresholds

Treat concept assignment as a tuning exercise

4.4 Representational Noise

Some texts won’t “say anything.”

Mitigation:

Minimum length filters

Confidence thresholds

Manual spot checks early

5. Why This Architecture Is Colab-Friendly

Batch-oriented

Regeneratable layers

Clear checkpoints

Easy to serialize intermediate artifacts (parquet, pickle)

You can:

Work one notebook per layer

Re-run only what changes

Version concepts separately from code

6. Expected Iteration Loop (This Is Normal)

A healthy loop looks like:

Ingest small corpus

Define 1–2 concepts

Assign concept instances

Inspect samples manually

Adjust inclusion logic

Re-run representations

Compare sources

Discover a flaw

Refine concept definition

Repeat

This is research, not pipeline engineering—and that’s good.
