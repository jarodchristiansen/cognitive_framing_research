"""
Main script to run all analyses on the current dataset.

This script:
1. Loads concept instances and documents
2. Extracts representations (embeddings, keywords)
3. Performs comparative analysis
4. Generates views (tables, summaries)

Following the architecture layers:
- Representation Extraction (3.4)
- Comparative Analysis (3.5)
- Views/Outputs (3.6)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import logging
from typing import List

from canonicalization import TextCanonicalizer
from concept_assignment import (
    ConceptInstance,
    load_documents as load_docs_for_assignment,
    canonicalize_documents as canonicalize_docs_for_assignment
)
from representation import RepresentationExtractor
from analysis import ComparativeAnalyzer
from views import ViewGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data():
    """Load concept instances, documents, and recreate segments."""
    logger.info("Loading data...")
    
    # Load concept instances
    instances_path = Path("ingested_data/concept_instances.parquet")
    if not instances_path.exists():
        raise FileNotFoundError(f"Concept instances not found at {instances_path}. Run concept assignment first.")
    
    instances_df = pd.read_parquet(instances_path)
    logger.info(f"Loaded {len(instances_df)} concept instances")
    
    # Load documents
    documents_path = Path("ingested_data/documents.parquet")
    if not documents_path.exists():
        raise FileNotFoundError(f"Documents not found at {documents_path}. Run ingestion first.")
    
    documents_df = load_docs_for_assignment(documents_path)
    
    # Recreate text segments (canonicalization is regeneratable)
    all_segments = canonicalize_docs_for_assignment(documents_df)
    
    # Convert instances_df to ConceptInstance objects
    # Reconstruct from saved parquet data
    concept_instances = []
    
    for _, row in instances_df.iterrows():
        # Reconstruct ConceptInstance from saved data
        instance = ConceptInstance(
            concept_id=row['concept_id'],
            text_segment_id=row['text_segment_id'],
            confidence=float(row['confidence']),
            assignment_method=row['assignment_method'],
            metadata={
                'keyword_score': float(row['keyword_score']) if pd.notna(row.get('keyword_score')) else None,
                'embedding_score': float(row['embedding_score']) if pd.notna(row.get('embedding_score')) else None,
                'text_length': int(row['text_length']) if pd.notna(row.get('text_length')) else 0,
                'document_id': row.get('document_id')  # Important for analysis!
            }
        )
        concept_instances.append(instance)
    
    return concept_instances, all_segments, documents_df


def main():
    """Main analysis function."""
    print("=" * 80)
    print("COMPARATIVE ANALYSIS")
    print("=" * 80)
    
    try:
        # Load data
        concept_instances, text_segments, documents_df = load_data()
        
        if not concept_instances:
            print("No concept instances found. Run concept assignment first.")
            return
        
        # Get unique concept IDs
        concept_ids = list(set(inst.concept_id for inst in concept_instances))
        print(f"\nAnalyzing {len(concept_ids)} concept(s): {concept_ids}")
        
        # Step 1: Extract Representations (Section 3.4)
        print("\n" + "=" * 80)
        print("STEP 1: REPRESENTATION EXTRACTION")
        print("=" * 80)
        
        extractor = RepresentationExtractor(
            use_embeddings=True,
            extract_keywords=True
        )
        
        representations = extractor.extract_all_representations(concept_instances, text_segments)
        print(f"Extracted {len(representations)} representations")
        
        # Step 2: Comparative Analysis (Section 3.5)
        print("\n" + "=" * 80)
        print("STEP 2: COMPARATIVE ANALYSIS")
        print("=" * 80)
        
        analyzer = ComparativeAnalyzer()
        all_results = []
        
        for concept_id in concept_ids:
            # Filter instances for this concept
            concept_insts = [inst for inst in concept_instances if inst.concept_id == concept_id]
            concept_reps = [rep for rep in representations 
                          if any(inst.text_segment_id == rep.concept_instance_id for inst in concept_insts)]
            
            print(f"\nAnalyzing concept: {concept_id}")
            
            # Source-to-source similarity
            similarity_result = analyzer.calculate_source_similarity(
                concept_reps, concept_insts, documents_df, concept_id
            )
            if similarity_result:
                all_results.append(similarity_result)
                print(f"  ✓ Source similarity calculated")
            
            # Lexical patterns
            lexical_result = analyzer.analyze_lexical_patterns(
                concept_reps, concept_insts, documents_df, concept_id
            )
            if lexical_result:
                all_results.append(lexical_result)
                print(f"  ✓ Lexical patterns analyzed")
            
            # Coverage statistics
            coverage_result = analyzer.analyze_coverage(
                concept_insts, documents_df, concept_id
            )
            if coverage_result:
                all_results.append(coverage_result)
                print(f"  ✓ Coverage statistics calculated")
        
        # Step 3: Generate Views (Section 3.6)
        print("\n" + "=" * 80)
        print("STEP 3: GENERATING VIEWS")
        print("=" * 80)
        
        view_gen = ViewGenerator()
        view_gen.save_tables(all_results)
        
        # Print summary
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        
        for result in all_results:
            print(f"\n{result.metric_type.upper()}:")
            if result.metric_type == 'source_similarity':
                for key, value in result.values.items():
                    print(f"  {key}: {value:.3f}")
            elif result.metric_type == 'coverage':
                for source, data in result.values.items():
                    print(f"  {source}: {data['document_count']} docs, {data['segment_count']} segments")
            elif result.metric_type == 'lexical_patterns':
                for source, data in result.values.items():
                    top_kw = ', '.join(data['top_keywords'][:5])
                    print(f"  {source}: {top_kw}")
        
        print(f"\nAll results saved to: {view_gen.output_dir}/")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

