"""Test the pipeline with real data from analyzer node."""

from graph.state import ExamState
from graph.nodes.analyzer import analyzer_node
from graph.nodes.curriculum import curriculum_node

def test_pipeline_with_real_data():
    """Test the analyzer and curriculum nodes with real extracted data."""
    
    for trimester in [1, 2, 3]:
        print(f"\n{'='*70}")
        print(f"Testing Pipeline for Trimester {trimester}")
        print(f"{'='*70}")
        
        # Initialize state
        state = {
            "trimester": trimester,
            "reference_exams": [],
            "patterns": {},
            "curriculum": {},
            "exam_text": "",
            "exam_structured": {},
            "grading_schema": {},
            "correction": {},
            "validation_passed": False,
            "validation_errors": [],
            "exam_pdf_path": "",
            "correction_pdf_path": "",
            "error": None,
        }
        
        # Step 1: Run Analyzer
        print("\nStep 1: Running Analyzer...")
        analyzer_result = analyzer_node(state)
        state.update(analyzer_result)
        
        print(f"✓ Analyzer completed")
        print(f"  - Loaded {len(state['reference_exams'])} reference exams")
        print(f"  - Patterns: {state['patterns']}")
        
        # Step 2: Run Curriculum
        print("\nStep 2: Running Curriculum...")
        curriculum_result = curriculum_node(state)
        state.update(curriculum_result)
        
        print(f"✓ Curriculum completed")
        print(f"  - Loaded chapters: {list(state['curriculum'].get('chapters', {}).keys())}")
        print(f"  - Skills count: {len(state['curriculum'].get('skills', []))}")
        
        # Verify reference exams have content
        if state['reference_exams']:
            sample = state['reference_exams'][0]
            has_text = len(sample.get('full_text', '')) > 0
            print(f"\n✓ Sample exam verification:")
            print(f"  - Source: {sample.get('source_file', 'unknown')}")
            print(f"  - Has full_text: {has_text}")
            print(f"  - Text length: {len(sample.get('full_text', ''))} chars")
            
            if has_text:
                print(f"\n✓ READY: Real extracted data is available for LLM generator!")
            else:
                print(f"\n✗ WARNING: Sample exam has no full_text!")
        else:
            print(f"\n✗ ERROR: No reference exams loaded!")
        
        print("")

if __name__ == '__main__':
    test_pipeline_with_real_data()
