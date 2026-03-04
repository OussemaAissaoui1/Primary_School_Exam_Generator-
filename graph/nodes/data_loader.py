"""Data loader utility for extracted exam JSON files."""

import json
import random
from pathlib import Path
from typing import List, Dict

_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "extracted"

def load_all_exams() -> Dict[int, List[Dict]]:
    """Load all extracted exam JSON files organized by trimester.
    
    Returns:
        Dict mapping trimester (1,2,3) to list of exam dictionaries.
        Each exam dict contains: source_file, trimester, full_text, etc.
    """
    exams_by_trimester = {1: [], 2: [], 3: []}
    
    for trimester in [1, 2, 3]:
        trimester_dir = _DATA_DIR / f"t{trimester}"
        if not trimester_dir.exists():
            continue
            
        for json_file in sorted(trimester_dir.glob("*.json")):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Ensure required fields exist
                if not data.get('full_text'):
                    continue
                    
                # Add metadata
                exam = {
                    'source_file': data.get('source_file', json_file.name),
                    'trimester': data.get('trimester', trimester),
                    'full_text': data.get('full_text', ''),
                    'num_exercises': data.get('num_exercises', 0),
                    'num_instructions': data.get('num_instructions', 0),
                    'total_points': data.get('total_points', 0),
                }
                
                exams_by_trimester[trimester].append(exam)
                
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load {json_file}: {e}")
                continue
    
    return exams_by_trimester


def get_reference_exams(trimester: int, count: int = 3, include_other: bool = True) -> List[Dict]:
    """Get reference exams for a specific trimester.
    
    Args:
        trimester: The trimester number (1, 2, or 3).
        count: Number of exams to return.
        include_other: If True, include one exam from another trimester for variety.
        
    Returns:
        List of exam dictionaries.
    """
    all_exams = load_all_exams()
    
    # Get exams for requested trimester
    trimester_exams = all_exams.get(trimester, [])
    
    if not trimester_exams:
        print(f"Warning: No exams found for trimester {trimester}")
        return []
    
    # Sample from this trimester
    available_count = min(count, len(trimester_exams))
    selected = random.sample(trimester_exams, available_count)
    
    # Optionally include one from another trimester
    if include_other and available_count < count:
        other_trimesters = [t for t in [1, 2, 3] if t != trimester]
        for other_t in other_trimesters:
            other_exams = all_exams.get(other_t, [])
            if other_exams:
                selected.append(random.choice(other_exams))
                break
    
    # Shuffle for variety
    random.shuffle(selected)
    
    return selected


def get_exam_statistics(exams: List[Dict]) -> Dict:
    """Calculate statistics from a list of exams.
    
    Args:
        exams: List of exam dictionaries.
        
    Returns:
        Dict with statistics (avg exercises, instructions, points, etc.).
    """
    if not exams:
        return {
            'avg_exercises': 3,
            'avg_instructions': 8,
            'avg_total_points': 20,
            'num_reference_exams': 0,
        }
    
    # Calculate averages (use defaults of 3, 8, 20 if data is missing)
    total_exercises = sum(e.get('num_exercises', 3) for e in exams)
    total_instructions = sum(e.get('num_instructions', 8) for e in exams)
    total_points = sum(e.get('total_points', 20) for e in exams)
    
    return {
        'avg_exercises': total_exercises / len(exams) if total_exercises > 0 else 3,
        'avg_instructions': total_instructions / len(exams) if total_instructions > 0 else 8,
        'avg_total_points': total_points / len(exams) if total_points > 0 else 20,
        'num_reference_exams': len(exams),
        'avg_text_length': sum(len(e.get('full_text', '')) for e in exams) / len(exams),
    }


if __name__ == '__main__':
    # Test the loader
    print("Testing data loader...")
    all_exams = load_all_exams()
    
    for trimester, exams in all_exams.items():
        print(f"\nTrimester {trimester}: {len(exams)} exams")
        if exams:
            stats = get_exam_statistics(exams)
            print(f"  Stats: {stats}")
            
    print("\n\nTesting reference exam selection...")
    for t in [1, 2, 3]:
        refs = get_reference_exams(t, count=3)
        print(f"Trimester {t}: Selected {len(refs)} reference exams")
