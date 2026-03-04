"""Test the updated analyzer node with real data."""

from graph.nodes.analyzer import analyzer_node

def test_analyzer():
    """Test analyzer node for each trimester."""
    for trimester in [1, 2, 3]:
        print(f"\n{'='*60}")
        print(f"Testing Analyzer for Trimester {trimester}")
        print(f"{'='*60}")
        
        state = {"trimester": trimester}
        result = analyzer_node(state)
        
        print(f"\nResult summary:")
        print(f"  Number of reference exams: {len(result['reference_exams'])}")
        print(f"  Patterns: {result['patterns']}")
        
        if result['reference_exams']:
            print(f"\nSample exam (first):")
            sample = result['reference_exams'][0]
            print(f"  Source: {sample['source_file']}")
            print(f"  Trimester: {sample['trimester']}")
            print(f"  Text length: {len(sample['full_text'])} chars")
            print(f"  Text preview (first 200 chars):")
            print(f"    {sample['full_text'][:200]}")
        else:
            print("  No exams loaded!")

if __name__ == '__main__':
    test_analyzer()
