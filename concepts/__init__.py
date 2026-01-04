"""
Concept Definition Module

This module defines concepts for the Cognitive Representation Mapping System.
Concepts are explicitly defined with inclusion/exclusion criteria following
the architecture principles.
"""

from .concept_definitions import CONCEPTS, get_concept_by_id, Concept, list_concepts

__all__ = ['CONCEPTS', 'get_concept_by_id', 'Concept', 'list_concepts']

