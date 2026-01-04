"""
Representation Extraction Layer (Section 3.4)

Responsibility: Extract how a concept is represented, not what it means.

For each ConceptInstance, compute:
- Embeddings
- Lexical features
- Optional LLM-assisted frame summaries

Key rule: Everything here is regeneratable.
This allows you to swap models, tune parameters, and re-run analyses
without re-ingesting data.
"""

import sys
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd
from collections import Counter

# Add project root to path
if __file__:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from concept_assignment import ConceptInstance
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
class Representation:
    """
    Representation schema from architecture (section 3.4).
    
    Represents how a concept is represented in a text segment.
    """
    concept_instance_id: str
    embedding: Optional[np.ndarray] = None  # Vector embedding
    keywords: List[str] = field(default_factory=list)  # Extracted keywords
    frame_summary: Optional[str] = None  # Optional LLM-assisted summary
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata


class RepresentationExtractor:
    """
    Extracts representations from concept instances.
    
    This layer is regeneratable - can re-run with different models/parameters
    without re-ingesting or re-assigning concepts.
    """
    
    def __init__(
        self,
        embedding_model_name: str = 'all-MiniLM-L6-v2',
        use_embeddings: bool = True,
        extract_keywords: bool = True,
        keyword_count: int = 10
    ):
        """
        Initialize representation extractor.
        
        Args:
            embedding_model_name: Name of sentence transformer model
            use_embeddings: Whether to generate embeddings
            extract_keywords: Whether to extract keywords
            keyword_count: Number of top keywords to extract
        """
        self.use_embeddings = use_embeddings and EMBEDDINGS_AVAILABLE
        self.extract_keywords = extract_keywords
        self.keyword_count = keyword_count
        
        # Initialize embedding model if available
        self.embedding_model = None
        if self.use_embeddings:
            try:
                logger.info(f"Loading embedding model: {embedding_model_name}")
                self.embedding_model = SentenceTransformer(embedding_model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}. Embeddings disabled.")
                self.use_embeddings = False
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for keyword extraction."""
        # Lowercase, remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return text
    
    def _extract_keywords(self, text: str, exclude_words: Optional[List[str]] = None) -> List[str]:
        """
        Extract top keywords from text.
        
        Simple frequency-based extraction. Can be enhanced with TF-IDF, etc.
        """
        if not self.extract_keywords:
            return []
        
        # Common stop words (basic list - can be expanded)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
            'we', 'our', 'you', 'your', 'he', 'she', 'his', 'her', 'said',
            'says', 'say', 'according', 'also', 'more', 'most', 'very', 'much'
        }
        
        if exclude_words:
            stop_words.update(word.lower() for word in exclude_words)
        
        # Normalize and tokenize
        normalized = self._normalize_text(text)
        words = normalized.split()
        
        # Filter stop words and short words
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        
        # Count frequencies
        word_counts = Counter(words)
        
        # Return top N keywords
        top_keywords = [word for word, count in word_counts.most_common(self.keyword_count)]
        
        return top_keywords
    
    def extract_representation(
        self,
        concept_instance: ConceptInstance,
        text_segment: TextSegment
    ) -> Representation:
        """
        Extract representation for a concept instance.
        
        Args:
            concept_instance: The concept instance to extract representation for
            text_segment: The text segment associated with the instance
            
        Returns:
            Representation object with embedding, keywords, etc.
        """
        text = text_segment.text
        
        # Extract embedding
        embedding = None
        if self.use_embeddings:
            try:
                embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            except Exception as e:
                logger.warning(f"Error generating embedding: {e}")
        
        # Extract keywords
        keywords = []
        if self.extract_keywords:
            keywords = self._extract_keywords(text)
        
        # Create representation
        # Note: concept_instance_id should uniquely identify the instance
        # We use text_segment_id since each instance maps to one segment
        representation = Representation(
            concept_instance_id=concept_instance.text_segment_id,  # Maps to segment that was assigned
            embedding=embedding,
            keywords=keywords,
            frame_summary=None,  # Optional - can add LLM summarization later
            metadata={
                'concept_id': concept_instance.concept_id,
                'text_length': len(text),
                'keyword_count': len(keywords),
                'has_embedding': embedding is not None,
                'confidence': concept_instance.confidence
            }
        )
        
        return representation
    
    def extract_all_representations(
        self,
        concept_instances: List[ConceptInstance],
        text_segments: List[TextSegment]
    ) -> List[Representation]:
        """
        Extract representations for all concept instances.
        
        Args:
            concept_instances: List of concept instances
            text_segments: List of text segments (for lookup)
            
        Returns:
            List of Representation objects
        """
        # Create segment lookup
        segment_lookup = {seg.id: seg for seg in text_segments}
        
        representations = []
        
        logger.info(f"Extracting representations for {len(concept_instances)} concept instances...")
        
        for instance in concept_instances:
            segment = segment_lookup.get(instance.text_segment_id)
            if not segment:
                logger.warning(f"Segment {instance.text_segment_id} not found, skipping")
                continue
            
            representation = self.extract_representation(instance, segment)
            representations.append(representation)
        
        logger.info(f"Extracted {len(representations)} representations")
        return representations

