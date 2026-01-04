"""
Concept Definitions

Each concept follows the architecture schema:
- id
- name
- description
- inclusion_criteria
- exclusion_criteria
- seed_terms

Concepts are human-defined, explicit, and scoped carefully for comparability.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class Concept:
    """
    Concept definition following architecture schema (section 3.3).
    
    Concepts are the primary unit of analysis - they represent how a topic
    is discussed across sources and time, not individual events or stories.
    """
    id: str
    name: str
    description: str
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]
    seed_terms: List[str]
    # Optional: additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert concept to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'inclusion_criteria': self.inclusion_criteria,
            'exclusion_criteria': self.exclusion_criteria,
            'seed_terms': self.seed_terms,
            'metadata': self.metadata
        }


# Define concepts
CONCEPTS: Dict[str, Concept] = {
    'income_wealth_inequality': Concept(
        id='income_wealth_inequality',
        name='Income and Wealth Inequality',
        description=(
            "Discussions of income and wealth inequality, including disparities "
            "in earnings, assets, economic opportunity, and distribution of resources. "
            "This concept focuses on how inequality is represented, measured, discussed, "
            "and framed across different sources and time periods."
        ),
        inclusion_criteria=[
            "Discusses income inequality, wage gaps, or earnings disparities",
            "Addresses wealth inequality, asset distribution, or wealth gaps",
            "Mentions economic inequality, economic disparity, or distribution of resources",
            "References measures of inequality (Gini coefficient, income quintiles, etc.)",
            "Discusses policies, trends, or analysis related to economic inequality",
            "Compares economic outcomes across different groups (by income, class, etc.)",
            "Discusses social mobility, economic opportunity, or access to resources",
            "Mentions the middle class, working class, or economic stratification"
        ],
        exclusion_criteria=[
            "Articles that only mention inequality in passing without substantive discussion",
            "Articles focused solely on specific policy proposals without inequality context",
            "Articles about inequality in non-economic contexts (e.g., health outcomes alone)",
            "Articles that mention 'inequality' but are actually about other topics",
            "Brief mentions without analysis or discussion of inequality patterns"
        ],
        seed_terms=[
            # Core terms (phrases)
            'income inequality',
            'wealth inequality',
            'economic inequality',
            'wage gap',
            'wealth gap',
            'income gap',
            'economic disparity',
            'wealth disparity',
            'income distribution',
            'wealth distribution',
            # Measurement terms
            'gini coefficient',
            'income quintile',
            'wealth quintile',
            'top 1%',
            'top 10%',
            'bottom 50%',
            'poverty line',
            'average income',
            'median income',
            'average wealth',
            'median wealth',
            # Related concepts
            'economic mobility',
            'social mobility',
            'class divide',
            'economic stratification',
            'wealth concentration',
            'economic opportunity',
            # Policy/context terms
            'tax inequality',
            'wealth tax',
            'minimum wage',
            'living wage',
            'economic justice',
            'economic fairness',
            # Single-word terms (for partial matching)
            'inequality',
            'wealth',
            'income',
            'wage',
            'gap',
            'disparity',
            'distribution',
            'gini',
            'poverty',
            'mobility',
            'stratification',
            'concentration',
            'opportunity',
            'tax reform',
        ],
        metadata={
            'created_at': '2025-01-27',
            'version': '1.0',
            'notes': 'Initial concept definition for income/wealth inequality'
        }
    )
}


def get_concept_by_id(concept_id: str) -> Concept:
    """Get a concept by its ID."""
    if concept_id not in CONCEPTS:
        raise ValueError(f"Concept '{concept_id}' not found. Available concepts: {list(CONCEPTS.keys())}")
    return CONCEPTS[concept_id]


def list_concepts() -> List[Concept]:
    """List all defined concepts."""
    return list(CONCEPTS.values())

