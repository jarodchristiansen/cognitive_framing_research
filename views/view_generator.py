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

import sys
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

# Add project root to path
if __file__:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from analysis import ComparisonResult


class ViewGenerator:
    """
    Generates views (tables, charts, matrices) from comparison results.
    
    Views are disposable and never mutate upstream data.
    """
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize view generator.
        
        Args:
            output_dir: Directory to save view outputs (optional)
        """
        if output_dir is None:
            output_dir = Path("analysis_output")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_similarity_table(self, result: ComparisonResult) -> pd.DataFrame:
        """
        Generate similarity matrix as a table.
        
        Args:
            result: ComparisonResult with source_similarity metric
            
        Returns:
            DataFrame with similarity matrix
        """
        if result.metric_type != 'source_similarity':
            raise ValueError(f"Expected source_similarity, got {result.metric_type}")
        
        # Create matrix
        sources = result.sources
        matrix_data = []
        
        for source1 in sources:
            row = {'source': source1}
            for source2 in sources:
                if source1 == source2:
                    row[source2] = 1.0
                else:
                    key1 = f"{source1} vs {source2}"
                    key2 = f"{source2} vs {source1}"
                    similarity = result.values.get(key1) or result.values.get(key2) or 0.0
                    row[source2] = similarity
            matrix_data.append(row)
        
        df = pd.DataFrame(matrix_data)
        df.set_index('source', inplace=True)
        
        return df
    
    def generate_lexical_table(self, result: ComparisonResult) -> pd.DataFrame:
        """
        Generate lexical patterns table.
        
        Shows top keywords per source.
        """
        if result.metric_type != 'lexical_patterns':
            raise ValueError(f"Expected lexical_patterns, got {result.metric_type}")
        
        # Create table with top keywords per source
        rows = []
        for source_id, data in result.values.items():
            keywords = data.get('top_keywords', [])
            counts = data.get('keyword_counts', {})
            
            for i, keyword in enumerate(keywords[:10], 1):
                rows.append({
                    'source': source_id,
                    'rank': i,
                    'keyword': keyword,
                    'count': counts.get(keyword, 0)
                })
        
        df = pd.DataFrame(rows)
        return df
    
    def generate_coverage_table(self, result: ComparisonResult) -> pd.DataFrame:
        """
        Generate coverage statistics table.
        """
        if result.metric_type != 'coverage':
            raise ValueError(f"Expected coverage, got {result.metric_type}")
        
        rows = []
        for source_id, data in result.values.items():
            rows.append({
                'source': source_id,
                'documents': data['document_count'],
                'segments': data['segment_count'],
                'avg_confidence': f"{data['avg_confidence']:.3f}",
                'min_confidence': f"{data['min_confidence']:.3f}",
                'max_confidence': f"{data['max_confidence']:.3f}"
            })
        
        df = pd.DataFrame(rows)
        return df
    
    def save_tables(self, results: List[ComparisonResult], prefix: str = "analysis"):
        """
        Save all comparison results as tables.
        
        Args:
            results: List of ComparisonResult objects
            prefix: Prefix for output files
        """
        for result in results:
            if result.metric_type == 'source_similarity':
                df = self.generate_similarity_table(result)
                output_path = self.output_dir / f"{prefix}_similarity_matrix.csv"
                df.to_csv(output_path)
                print(f"Saved similarity matrix to {output_path}")
            
            elif result.metric_type == 'lexical_patterns':
                df = self.generate_lexical_table(result)
                output_path = self.output_dir / f"{prefix}_lexical_patterns.csv"
                df.to_csv(output_path)
                print(f"Saved lexical patterns to {output_path}")
            
            elif result.metric_type == 'coverage':
                df = self.generate_coverage_table(result)
                output_path = self.output_dir / f"{prefix}_coverage.csv"
                df.to_csv(output_path)
                print(f"Saved coverage statistics to {output_path}")

