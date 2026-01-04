"""
Canonicalization Layer (Section 3.2)

Responsibility: Normalize text for downstream processing.
- Remove boilerplate
- Normalize whitespace
- Segment into paragraphs or chunks

Output: TextSegment

This stage is intentionally boring - no semantics yet.
"""

import re
import hashlib
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class TextSegment:
    """
    TextSegment schema from architecture (section 3.2).
    
    Represents a segment of text from a document, ready for concept assignment.
    """
    id: str
    document_id: str
    text: str
    position: int  # Position in document (0-indexed)
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TextCanonicalizer:
    """
    Light, mechanical text normalization and segmentation.
    
    No semantic processing - just structural normalization.
    """
    
    def __init__(self, min_segment_length: int = 100, max_segment_length: int = 2000):
        """
        Initialize canonicalizer.
        
        Args:
            min_segment_length: Minimum character length for a segment
            max_segment_length: Maximum character length for a segment
        """
        self.min_segment_length = min_segment_length
        self.max_segment_length = max_segment_length
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace - collapse multiple spaces, normalize line breaks."""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Normalize line breaks (keep single \n for paragraph breaks)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
    
    def segment_by_paragraphs(self, text: str, document_id: str) -> List[TextSegment]:
        """
        Segment text into paragraphs.
        
        This is the primary segmentation method - simple and effective.
        """
        # Normalize whitespace first
        text = self.normalize_whitespace(text)
        
        # Split by double newlines (paragraph breaks)
        paragraphs = text.split('\n\n')
        
        segments = []
        for idx, para in enumerate(paragraphs):
            para = para.strip()
            
            # Skip very short paragraphs
            if len(para) < self.min_segment_length:
                continue
            
            # If paragraph is too long, split by sentences
            if len(para) > self.max_segment_length:
                # Split into sentences and group into chunks
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = []
                current_length = 0
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    if current_length + len(sentence) > self.max_segment_length and current_chunk:
                        # Save current chunk
                        chunk_text = ' '.join(current_chunk)
                        if len(chunk_text) >= self.min_segment_length:
                            seg_id = self._generate_segment_id(document_id, idx, len(segments))
                            segments.append(TextSegment(
                                id=seg_id,
                                document_id=document_id,
                                text=chunk_text,
                                position=len(segments),
                                metadata={'segmentation_method': 'paragraph_split'}
                            ))
                        current_chunk = [sentence]
                        current_length = len(sentence)
                    else:
                        current_chunk.append(sentence)
                        current_length += len(sentence)
                
                # Add remaining chunk
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    if len(chunk_text) >= self.min_segment_length:
                        seg_id = self._generate_segment_id(document_id, idx, len(segments))
                        segments.append(TextSegment(
                            id=seg_id,
                            document_id=document_id,
                            text=chunk_text,
                            position=len(segments),
                            metadata={'segmentation_method': 'paragraph_split'}
                        ))
            else:
                # Paragraph is good size - use as-is
                seg_id = self._generate_segment_id(document_id, idx, len(segments))
                segments.append(TextSegment(
                    id=seg_id,
                    document_id=document_id,
                    text=para,
                    position=len(segments),
                    metadata={'segmentation_method': 'paragraph'}
                ))
        
        return segments
    
    def _generate_segment_id(self, document_id: str, paragraph_idx: int, segment_idx: int) -> str:
        """Generate deterministic segment ID."""
        key = f"{document_id}:para_{paragraph_idx}:seg_{segment_idx}".encode('utf-8')
        return hashlib.md5(key).hexdigest()
    
    def canonicalize_document(self, document_id: str, raw_text: str) -> List[TextSegment]:
        """
        Canonicalize a document into text segments.
        
        This is the main entry point for canonicalization.
        """
        return self.segment_by_paragraphs(raw_text, document_id)

