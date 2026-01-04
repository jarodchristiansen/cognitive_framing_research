"""
Simple test script for ingestion functionality.
Run this to verify the ingestion pipeline works correctly.
"""

import logging
from ingestion import DocumentIngester, SOURCES

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_guardian_api():
    """Test ingesting from Guardian API (free, no key needed)."""
    print("Testing Guardian API ingestion...")
    
    ingester = DocumentIngester()
    
    # Test with just Guardian
    test_source = {"Guardian": SOURCES["Guardian"]}
    
    df = ingester.ingest_all_sources(test_source)
    
    if not df.empty:
        print(f"\n✓ Success! Ingested {len(df)} documents from Guardian")
        print(f"\nSample document:")
        sample = df.iloc[0]
        print(f"  Title: {sample['title'][:80]}...")
        print(f"  URL: {sample['url']}")
        print(f"  Text length: {len(sample['raw_text'])} characters")
        print(f"\nDocuments saved to: {ingester.documents_path}")
        return True
    else:
        print("\n✗ No documents were ingested from Guardian")
        return False

def test_rss_feed():
    """Test ingesting from an RSS feed (BBC)."""
    print("Testing RSS feed ingestion (BBC)...")
    
    ingester = DocumentIngester()
    
    # Test with BBC RSS
    test_source = {"BBC_News": SOURCES["BBC_News"]}
    
    df = ingester.ingest_all_sources(test_source)
    
    if not df.empty:
        print(f"\n✓ Success! Ingested {len(df)} documents from BBC RSS")
        print(f"\nSample document:")
        sample = df.iloc[0]
        print(f"  Title: {sample['title'][:80]}...")
        print(f"  URL: {sample['url']}")
        print(f"  Text length: {len(sample['raw_text'])} characters")
        return True
    else:
        print("\n✗ No documents were ingested from BBC RSS")
        return False

def test_all_sources():
    """Test ingesting from all configured sources."""
    print("Testing all configured sources...")
    
    ingester = DocumentIngester()
    df = ingester.ingest_all_sources()
    
    if not df.empty:
        print(f"\n✓ Success! Ingested {len(df)} total documents")
        print(f"\nBreakdown by source:")
        source_counts = df['source_id'].value_counts()
        for source, count in source_counts.items():
            print(f"  {source}: {count} documents")
        return True
    else:
        print("\n✗ No documents were ingested")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Ingestion Test Suite")
    print("=" * 60)
    
    # Test 1: Guardian API (most reliable, free)
    print("\n[Test 1] Guardian API")
    print("-" * 60)
    test_guardian_api()
    
    # Test 2: RSS Feed
    print("\n[Test 2] RSS Feed (BBC)")
    print("-" * 60)
    test_rss_feed()
    
    # Test 3: All sources
    print("\n[Test 3] All Sources")
    print("-" * 60)
    test_all_sources()
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)
    print("\nNote: If some sources fail, that's normal.")
    print("Guardian API should always work (it's free and reliable).")
