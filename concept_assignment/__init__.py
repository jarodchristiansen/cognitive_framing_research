"""
Concept Assignment Module

Assigns text segments to concepts using hybrid keyword + embedding approach.
"""

from .concept_assignment import (
    ConceptAssigner,
    ConceptInstance,
    load_documents,
    canonicalize_documents,
    assign_concepts_to_segments,
    display_assignment_results,
    save_concept_instances,
    run_concept_assignment
)

__all__ = [
    'ConceptAssigner',
    'ConceptInstance',
    'load_documents',
    'canonicalize_documents',
    'assign_concepts_to_segments',
    'display_assignment_results',
    'save_concept_instances',
    'run_concept_assignment'
]

