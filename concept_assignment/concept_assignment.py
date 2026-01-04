"""
Concept Assignment Layer (Section 3.3)

This is the highest-risk and highest-value layer.

Assignment Strategy (MVP):
- Hybrid approach: Keyword + embedding similarity
- Human validation loop
- Threshold-based inclusion

Output: ConceptInstance {
    concept_id
    text_segment_id
    confidence
}

Important: Concept assignment is probabilistic and revisable.
"""

import sys
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from pathlib import Path

# Add project root to path for imports (if not already there)
if __file__:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from concepts import Concept, get_concept_by_id, CONCEPTS
from canonicalization import TextSegment

# Try to import sentence-transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

logger = logging.getLogger(__name__)


@dataclass
class ConceptInstance:
    """
    ConceptInstance schema from architecture (section 3.3).
    
    Represents a text segment assigned to a concept with confidence score.
    """
    concept_id: str
    text_segment_id: str
    confidence: float
    assignment_method: str  # 'keyword', 'embedding', 'hybrid'
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ConceptAssigner:
    """
    Assigns text segments to concepts using hybrid keyword + embedding approach.
    
    This follows the architecture's MVP strategy:
    1. Keyword matching (fast, explicit)
    2. Embedding similarity (semantic, flexible)
    3. Combined confidence scoring
    4. Threshold-based inclusion
    """
    
    def __init__(
        self,
        embedding_model_name: str = 'all-MiniLM-L6-v2',
        keyword_weight: float = 0.4,
        embedding_weight: float = 0.6,
        min_confidence: float = 0.5,
        use_embeddings: bool = True
    ):
        """
        Initialize concept assigner.
        
        Args:
            embedding_model_name: Name of sentence transformer model
            keyword_weight: Weight for keyword matching (0-1)
            embedding_weight: Weight for embedding similarity (0-1)
            min_confidence: Minimum confidence threshold for assignment
            use_embeddings: Whether to use embeddings (requires sentence-transformers)
        """
        self.keyword_weight = keyword_weight
        self.embedding_weight = embedding_weight
        self.min_confidence = min_confidence
        self.use_embeddings = use_embeddings and EMBEDDINGS_AVAILABLE
        
        # Initialize embedding model if available
        self.embedding_model = None
        if self.use_embeddings:
            try:
                logger.info(f"Loading embedding model: {embedding_model_name}")
                self.embedding_model = SentenceTransformer(embedding_model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}. Falling back to keyword-only.")
                self.use_embeddings = False
        
        # Cache for concept embeddings
        self._concept_embeddings_cache: Dict[str, np.ndarray] = {}
    
    def _normalize_text_for_keywords(self, text: str) -> str:
        """Normalize text for keyword matching (lowercase, basic cleaning)."""
        text = text.lower()
        # Remove punctuation for matching
        text = re.sub(r'[^\w\s]', ' ', text)
        return text
    
    def _keyword_match_score(self, text: str, concept: Concept) -> float:
        """
        Calculate keyword matching score.
        
        This method checks if seed terms from the concept definition appear in the text.
        It uses a lenient scoring system that:
        1. Checks for exact phrase matches (e.g., "income inequality")
        2. Checks for partial matches (e.g., "income" and "gap" appear separately)
        3. Uses logarithmic scoring (1 match = 0.3, 2 = 0.5, 3 = 0.65, 4+ = 0.8+)
        
        Args:
            text: The text segment to check
            concept: The concept with seed terms to match against
            
        Returns:
            Score between 0.0 and 1.0 based on how many seed terms match
            
        Example:
            >>> concept.seed_terms = ["income inequality", "wealth gap", "inequality"]
            >>> text = "The income inequality has grown, and the wealth gap is widening."
            >>> score = assigner._keyword_match_score(text, concept)
            >>> # Matches: "income inequality" (exact), "wealth gap" (exact), "inequality" (word)
            >>> # Result: score ≈ 0.65 (3 matches)
        """
        normalized_text = self._normalize_text_for_keywords(text)
        words = set(normalized_text.split())
        
        # Count matches for seed terms (exact phrase matches)
        phrase_matches = 0
        # Count individual word matches (for partial relevance)
        word_matches = 0
        total_terms = len(concept.seed_terms)
        
        if total_terms == 0:
            return 0.0
        
        # Collect all unique words from seed terms for individual word matching
        all_seed_words = set()
        for term in concept.seed_terms:
            normalized_term = term.lower()
            # Check for exact phrase match first (handles multi-word terms)
            if normalized_term in normalized_text:
                phrase_matches += 1
            # Also check if all words in the term appear (for cases with punctuation/spacing)
            elif ' ' in normalized_term:
                term_words = normalized_term.split()
                # Check if all words appear (they don't need to be adjacent)
                if all(word in words for word in term_words):
                    phrase_matches += 1
                # Track individual words for partial matching
                all_seed_words.update(term_words)
            # For single-word terms, check if word appears
            else:
                if normalized_term in words:
                    phrase_matches += 1
                all_seed_words.add(normalized_term)
        
        # Count how many individual seed words appear in the text
        for word in all_seed_words:
            if word in words:
                word_matches += 1
        
        # Calculate scores: phrase matches are worth more than word matches
        # Use phrase matches as primary signal
        matches = phrase_matches
        
        # If we have word matches but no phrase matches, give partial credit
        # This handles cases where "income" and "gap" appear but not "income gap"
        if phrase_matches == 0 and word_matches > 0:
            # Give partial credit: 2+ word matches = 1 phrase match equivalent
            if word_matches >= 2:
                matches = 1
            elif word_matches == 1:
                matches = 0.5  # Half credit for single word match
        
        # More lenient scoring: use logarithmic scale instead of linear
        # This means: 1 match = 0.3, 2 matches = 0.5, 3 matches = 0.65, 4+ = 0.8+
        # Also account for partial matches (individual words)
        if matches == 0:
            return 0.0
        elif matches == 0.5:  # Single word match
            base_score = 0.15  # Lower score for single word
        elif matches == 1:
            base_score = 0.3
        elif matches == 2:
            base_score = 0.5
        elif matches == 3:
            base_score = 0.65
        elif matches >= 4:
            # For 4+ matches, use diminishing returns
            base_score = 0.8 + min(0.2, (matches - 4) * 0.05)
        
        # Additional boost if matches represent a significant portion of terms
        # (helps when we have many seed terms but few matches)
        match_ratio = matches / total_terms
        if match_ratio > 0.1:  # More than 10% of terms matched
            base_score = min(1.0, base_score + 0.1)
        
        return min(1.0, base_score)
    
    def _get_concept_embedding(self, concept: Concept) -> np.ndarray:
        """Get or compute embedding for a concept."""
        if concept.id in self._concept_embeddings_cache:
            return self._concept_embeddings_cache[concept.id]
        
        if not self.use_embeddings:
            raise ValueError("Embeddings not available")
        
        # Create a representative text for the concept
        # Combine description, inclusion criteria, and seed terms
        concept_text = f"{concept.description}. "
        concept_text += " ".join(concept.inclusion_criteria[:3])  # Use first 3 inclusion criteria
        concept_text += " " + " ".join(concept.seed_terms[:10])  # Use first 10 seed terms
        
        embedding = self.embedding_model.encode(concept_text, convert_to_numpy=True)
        self._concept_embeddings_cache[concept.id] = embedding
        
        return embedding
    
    def _embedding_similarity_score(self, text: str, concept: Concept) -> float:
        """
        Calculate embedding similarity score using neural embeddings.
        
        This method:
        1. Gets or creates a concept embedding (cached for performance)
        2. Creates an embedding for the text segment
        3. Calculates cosine similarity between them
        4. Returns normalized score (0-1)
        
        Embeddings capture semantic meaning, so this can match text that doesn't
        use exact seed terms but discusses related concepts.
        
        Args:
            text: The text segment to check
            concept: The concept to compare against
            
        Returns:
            Cosine similarity score between 0.0 and 1.0
            - 0.0: No semantic similarity
            - 0.5: Moderate similarity
            - 0.8+: High similarity
            
        Note:
            Requires sentence-transformers library. Falls back to 0.0 if not available.
            
        Example:
            >>> text = "The economic divide between rich and poor communities"
            >>> concept = get_concept_by_id("income_wealth_inequality")
            >>> score = assigner._embedding_similarity_score(text, concept)
            >>> # Even without exact terms, semantic similarity might be high
            >>> # Result: score ≈ 0.6-0.8 (semantically related)
        """
        if not self.use_embeddings:
            return 0.0
        
        try:
            # Get text embedding
            text_embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            
            # Get concept embedding
            concept_embedding = self._get_concept_embedding(concept)
            
            # Calculate cosine similarity
            similarity = np.dot(text_embedding, concept_embedding) / (
                np.linalg.norm(text_embedding) * np.linalg.norm(concept_embedding)
            )
            
            # Normalize to 0-1 range (cosine similarity is already -1 to 1, but typically 0-1)
            similarity = max(0.0, similarity)
            
            return float(similarity)
        except Exception as e:
            logger.warning(f"Error computing embedding similarity: {e}")
            return 0.0
    
    def _check_exclusion_criteria(self, text: str, concept: Concept) -> bool:
        """
        Check if text matches exclusion criteria.
        
        Returns True if text should be excluded.
        """
        normalized_text = self._normalize_text_for_keywords(text)
        
        # Simple check: if text mentions exclusion terms prominently, exclude
        # This is a basic implementation - can be refined
        exclusion_indicators = [
            'only mention',
            'in passing',
            'brief mention',
            'without substantive'
        ]
        
        # For now, we'll be lenient - exclusion is mainly for manual review
        # More sophisticated exclusion logic can be added later
        return False
    
    def assign_concept(
        self,
        text_segment: TextSegment,
        concept: Concept
    ) -> Optional[ConceptInstance]:
        """
        Assign a text segment to a concept.
        
        This is the core assignment function. It:
        1. Checks exclusion criteria
        2. Calculates keyword matching score
        3. Calculates embedding similarity score (if available)
        4. Combines scores with weights
        5. Checks if combined score meets threshold
        6. Returns ConceptInstance if above threshold, None otherwise
        
        Args:
            text_segment: The text segment to assign
            concept: The concept to assign to
            
        Returns:
            ConceptInstance if assignment meets threshold, None otherwise
            
        Example:
            >>> segment = TextSegment(id="seg1", document_id="doc1", text="...", position=0)
            >>> concept = get_concept_by_id("income_wealth_inequality")
            >>> assigner = ConceptAssigner(min_confidence=0.15)
            >>> instance = assigner.assign_concept(segment, concept)
            >>> if instance:
            ...     print(f"Assigned with confidence {instance.confidence}")
        """
        text = text_segment.text
        
        # Step 1: Check exclusion criteria first (quick filter)
        # This is a fast check to skip obviously irrelevant text
        if self._check_exclusion_criteria(text, concept):
            return None
        
        # Step 2: Calculate keyword matching score
        # This checks if seed terms appear in the text (explicit matching)
        # Returns score 0.0-1.0 based on how many terms match
        keyword_score = self._keyword_match_score(text, concept)
        
        # Step 3: Calculate embedding similarity score (if embeddings available)
        # This computes semantic similarity using neural embeddings
        # Returns score 0.0-1.0 based on cosine similarity
        embedding_score = self._embedding_similarity_score(text, concept) if self.use_embeddings else 0.0
        
        # Step 4: Combine scores with weights
        # Default: 40% keyword, 60% embedding
        # This balances explicit matching (keyword) with semantic matching (embedding)
        if self.use_embeddings:
            combined_score = (
                self.keyword_weight * keyword_score +
                self.embedding_weight * embedding_score
            )
            assignment_method = 'hybrid'  # Used both methods
        else:
            # If embeddings not available, use keyword score only
            combined_score = keyword_score
            assignment_method = 'keyword'  # Only keyword method used
        
        # Step 5: Check if combined score meets minimum threshold
        # Threshold determines how confident we need to be to assign
        # Lower threshold = more assignments (higher recall, lower precision)
        # Higher threshold = fewer assignments (lower recall, higher precision)
        if combined_score < self.min_confidence:
            return None  # Below threshold, don't assign
        
        # Step 6: Create and return ConceptInstance
        # Store all scores in metadata for analysis and debugging
        instance = ConceptInstance(
            concept_id=concept.id,
            text_segment_id=text_segment.id,
            confidence=combined_score,  # This is the final score used for threshold
            assignment_method=assignment_method,
            metadata={
                'keyword_score': keyword_score,  # Raw keyword score (0-1)
                'embedding_score': embedding_score if self.use_embeddings else None,  # Raw embedding score (0-1)
                'text_length': len(text),  # Length of segment for analysis
                'text_preview': text[:200] + '...' if len(text) > 200 else text  # Preview for manual review
            }
        )
        
        return instance
    
    def assign_all_concepts(
        self,
        text_segments: List[TextSegment],
        concept_ids: List[str]
    ) -> List[ConceptInstance]:
        """
        Assign multiple text segments to multiple concepts.
        
        Returns list of all ConceptInstances that meet threshold.
        """
        instances = []
        
        concepts = [get_concept_by_id(cid) for cid in concept_ids]
        
        for segment in text_segments:
            for concept in concepts:
                instance = self.assign_concept(segment, concept)
                if instance:
                    instances.append(instance)
        
        return instances


# ============================================================================
# Helper Functions for Running Concept Assignment
# ============================================================================

import pandas as pd
from canonicalization import TextCanonicalizer


def load_documents(documents_path: Path) -> pd.DataFrame:
    """Load documents from parquet file."""
    logger.info(f"Loading documents from {documents_path}")
    df = pd.read_parquet(documents_path)
    logger.info(f"Loaded {len(df)} documents")
    return df


def canonicalize_documents(df: pd.DataFrame) -> List[TextSegment]:
    """Canonicalize all documents into text segments."""
    logger.info("Canonicalizing documents into text segments...")
    canonicalizer = TextCanonicalizer()
    all_segments = []
    
    for idx, row in df.iterrows():
        segments = canonicalizer.canonicalize_document(
            document_id=row['id'],
            raw_text=row['raw_text']
        )
        all_segments.extend(segments)
    
    logger.info(f"Created {len(all_segments)} text segments from {len(df)} documents")
    return all_segments


def assign_concepts_to_segments(
    text_segments: List[TextSegment], 
    concept_ids: List[str],
    min_confidence: float = 0.15,
    use_embeddings: bool = True
) -> List[ConceptInstance]:
    """
    Assign concepts to text segments.
    
    Args:
        text_segments: List of text segments to assign concepts to
        concept_ids: List of concept IDs to assign
        min_confidence: Minimum confidence threshold for assignment
        use_embeddings: Whether to use embeddings (requires sentence-transformers)
        
    Returns:
        List of ConceptInstance objects that meet the threshold
    """
    logger.info(f"Assigning concepts: {concept_ids}")
    
    # Initialize assigner
    assigner = ConceptAssigner(
        min_confidence=min_confidence,
        use_embeddings=use_embeddings
    )
    
    # Assign concepts
    instances = assigner.assign_all_concepts(text_segments, concept_ids)
    
    logger.info(f"Assigned {len(instances)} concept instances")
    return instances


def display_assignment_results(
    instances: List[ConceptInstance],
    text_segments: List[TextSegment],
    documents_df: pd.DataFrame
):
    """Display assignment results for manual validation."""
    print("\n" + "=" * 80)
    print("CONCEPT ASSIGNMENT RESULTS")
    print("=" * 80)
    
    # Group by concept
    by_concept: Dict[str, List[ConceptInstance]] = {}
    for instance in instances:
        if instance.concept_id not in by_concept:
            by_concept[instance.concept_id] = []
        by_concept[instance.concept_id].append(instance)
    
    # Create segment lookup
    segment_lookup = {seg.id: seg for seg in text_segments}
    document_lookup = {row['id']: row for _, row in documents_df.iterrows()}
    
    for concept_id, concept_instances in by_concept.items():
        concept = get_concept_by_id(concept_id)
        print(f"\n{'=' * 80}")
        print(f"CONCEPT: {concept.name}")
        print(f"Total assignments: {len(concept_instances)}")
        print(f"{'=' * 80}")
        
        # Sort by confidence
        concept_instances.sort(key=lambda x: x.confidence, reverse=True)
        
        # Show top 10
        print(f"\nTop 10 assignments (by confidence):")
        print("-" * 80)
        
        for i, instance in enumerate(concept_instances[:10], 1):
            segment = segment_lookup[instance.text_segment_id]
            document = document_lookup[segment.document_id]
            
            print(f"\n[{i}] Confidence: {instance.confidence:.3f} ({instance.assignment_method})")
            print(f"    Source: {document['source_id']}")
            print(f"    Title: {document['title'][:70]}...")
            print(f"    Published: {document['published_at']}")
            print(f"    Text preview:")
            print(f"    {segment.text[:300]}...")
            if instance.metadata.get('keyword_score') is not None:
                print(f"    Keyword score: {instance.metadata['keyword_score']:.3f}")
            if instance.metadata.get('embedding_score') is not None:
                print(f"    Embedding score: {instance.metadata['embedding_score']:.3f}")
            print()
        
        # Summary statistics
        confidences = [inst.confidence for inst in concept_instances]
        print(f"\nSummary Statistics:")
        print(f"  Mean confidence: {sum(confidences) / len(confidences):.3f}")
        print(f"  Min confidence: {min(confidences):.3f}")
        print(f"  Max confidence: {max(confidences):.3f}")
        print(f"  Method breakdown:")
        method_counts = {}
        for inst in concept_instances:
            method_counts[inst.assignment_method] = method_counts.get(inst.assignment_method, 0) + 1
        for method, count in method_counts.items():
            print(f"    {method}: {count}")
        
        # Show document-level summary
        document_counts = {}
        for instance in concept_instances:
            segment = segment_lookup[instance.text_segment_id]
            doc_id = segment.document_id
            document_counts[doc_id] = document_counts.get(doc_id, 0) + 1
        
        multi_segment_docs = {doc_id: count for doc_id, count in document_counts.items() if count > 1}
        if multi_segment_docs:
            print(f"\n  Documents with multiple segments assigned: {len(multi_segment_docs)}")
            print(f"    (This is expected - articles are segmented into paragraphs,")
            print(f"     and multiple paragraphs from the same article can match the concept)")
            for doc_id, count in list(multi_segment_docs.items())[:3]:  # Show first 3
                doc = document_lookup[doc_id]
                print(f"    - '{doc['title'][:50]}...': {count} segments")


def save_concept_instances(
    instances: List[ConceptInstance], 
    text_segments: List[TextSegment],
    output_path: Path
):
    """
    Save concept instances to parquet file.
    
    Includes document_id for easier analysis and integration with documents.
    """
    logger.info(f"Saving results to {output_path}")
    
    # Create segment lookup to get document_id
    segment_lookup = {seg.id: seg for seg in text_segments}
    
    # Convert to DataFrame
    data = []
    for instance in instances:
        segment = segment_lookup.get(instance.text_segment_id)
        data.append({
            'concept_id': instance.concept_id,
            'text_segment_id': instance.text_segment_id,
            'document_id': segment.document_id if segment else None,  # Add document_id
            'confidence': instance.confidence,
            'assignment_method': instance.assignment_method,
            'keyword_score': instance.metadata.get('keyword_score'),
            'embedding_score': instance.metadata.get('embedding_score'),
            'text_length': instance.metadata.get('text_length'),
            'text_preview': instance.metadata.get('text_preview')
        })
    
    df = pd.DataFrame(data)
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved {len(df)} concept instances")


def run_concept_assignment(
    documents_path: Path,
    output_path: Path,
    concept_ids: Optional[List[str]] = None,
    use_all_concepts: bool = True,
    min_confidence: float = 0.15,
    display: bool = True
) -> List[ConceptInstance]:
    """
    Main function to run concept assignment pipeline.
    
    Args:
        documents_path: Path to documents.parquet
        output_path: Path to save concept_instances.parquet
        concept_ids: List of concept IDs to assign (if None and use_all_concepts=False, uses all)
        use_all_concepts: If True, assigns all defined concepts
        min_confidence: Minimum confidence threshold
        display: Whether to display results
        
    Returns:
        List of ConceptInstance objects
    """
    # Determine which concepts to use
    if use_all_concepts or concept_ids is None:
        concept_ids = [concept.id for concept in CONCEPTS.values()]
        print(f"Using all {len(concept_ids)} defined concepts")
    else:
        # Validate concept IDs
        valid_ids = [cid for cid in concept_ids if cid in CONCEPTS]
        if len(valid_ids) != len(concept_ids):
            invalid = set(concept_ids) - set(valid_ids)
            logger.warning(f"Invalid concept IDs: {invalid}")
        concept_ids = valid_ids
    
    if not concept_ids:
        raise ValueError("No valid concepts to assign")
    
    # Load documents
    df = load_documents(documents_path)
    
    # Canonicalize
    text_segments = canonicalize_documents(df)
    
    if not text_segments:
        raise ValueError("No text segments created. Check document content.")
    
    # Assign concepts
    instances = assign_concepts_to_segments(
        text_segments, 
        concept_ids,
        min_confidence=min_confidence
    )
    
    if not instances:
        logger.warning("No concept instances assigned.")
        return []
    
    # Display results if requested
    if display:
        display_assignment_results(instances, text_segments, df)
    
    # Save results
    save_concept_instances(instances, text_segments, output_path)
    
    return instances


# ============================================================================
# Command-line interface (if run directly)
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run concept assignment on ingested documents"
    )
    parser.add_argument(
        '--concept',
        action='append',
        dest='concept_ids',
        help='Concept ID(s) to assign (can specify multiple times)'
    )
    parser.add_argument(
        '--all-concepts',
        action='store_true',
        help='Assign all defined concepts (default)'
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.15,
        help='Minimum confidence threshold (default: 0.15)'
    )
    parser.add_argument(
        '--no-display',
        action='store_true',
        help='Skip displaying results'
    )
    
    args = parser.parse_args()
    
    # Set up paths
    project_root = Path(__file__).resolve().parent.parent
    documents_path = project_root / "ingested_data" / "documents.parquet"
    output_path = project_root / "ingested_data" / "concept_instances.parquet"
    
    # Run assignment
    run_concept_assignment(
        documents_path=documents_path,
        output_path=output_path,
        concept_ids=args.concept_ids,
        use_all_concepts=args.all_concepts,
        min_confidence=args.min_confidence,
        display=not args.no_display
    )

