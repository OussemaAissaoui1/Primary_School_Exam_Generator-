"""Node 1: Load and provide real reference exam examples from extracted data.

Loads actual extracted exam data from the data/extracted/ folder to provide
authentic Tunisian 6th-grade math exam examples for the LLM generator.
This gives the LLM real reference material to learn patterns and style from.
"""

import random
from .data_loader import get_reference_exams, get_exam_statistics


# ══════════════════════════════════════════════════════════════════════════════
# LangGraph node – Load real extracted exam data as reference
# ══════════════════════════════════════════════════════════════════════════════

def analyzer_node(state: dict) -> dict:
    """LangGraph node: Load real reference exams from extracted data.
    
    Loads actual exam files from data/extracted/ folder and provides them
    as reference examples for the LLM generator. This ensures the generator
    learns from authentic Tunisian 6th-grade math exams.
    
    Args:
        state: Dict containing at least 'trimester' key.
        
    Returns:
        Dict with 'reference_exams' and 'patterns' keys.
    """
    trimester = state["trimester"]

    # Load real reference exams for this trimester
    # Get 3-5 exams: majority from target trimester, some from others for variety
    matching = get_reference_exams(
        trimester=trimester,
        count=4,  # Request 4 total exams
        include_other=True  # Include 1 from another trimester
    )
    
    if not matching:
        # Fallback: if no data found, provide empty structure
        print(f"WARNING: No reference exams found for trimester {trimester}")
        return {
            "reference_exams": [],
            "patterns": {
                "avg_exercises": 3,
                "avg_instructions": 8,
                "avg_total_points": 20,
                "num_reference_exams": 0,
            },
        }

    # Calculate patterns from the loaded exams
    patterns = get_exam_statistics(matching)

    print(f"Loaded {len(matching)} reference exams for trimester {trimester}")
    print(f"Patterns: {patterns}")

    return {
        "reference_exams": matching,
        "patterns": patterns,
    }
