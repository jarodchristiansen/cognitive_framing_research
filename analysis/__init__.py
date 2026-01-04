"""
Comparative Analysis Layer (Section 3.5)

This is where insight starts.

Analyses include:
- Source-to-source similarity
- Cluster formation
- Temporal drift
- Frame overlap

Output objects are derived, not stored as truth.
"""

from .comparative_analysis import ComparativeAnalyzer, ComparisonResult

__all__ = ['ComparativeAnalyzer', 'ComparisonResult']

