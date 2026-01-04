"""
Views / Output Layer (Section 3.6)

These are:
- Tables
- Charts
- Matrices
- Interactive dashboards (later)

They should:
- Read from comparison outputs
- Never mutate upstream data
- Views are disposable
"""

from .view_generator import ViewGenerator

__all__ = ['ViewGenerator']

