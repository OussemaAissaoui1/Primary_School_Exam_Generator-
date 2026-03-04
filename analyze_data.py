"""Analyze extracted exam data quality and structure."""

import json
import os
from pathlib import Path
import re

def analyze_extracted_data():
    """Load and analyze all extracted JSON files."""
    data_dir = Path('data/extracted')
    all_exams = []
    
    for trimester_dir in ['t1', 't2', 't3']:
        trim_path = data_dir / trimester_dir
        if trim_path.exists():
            for json_file in sorted(trim_path.glob('*.json')):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Analyze text content
                    full_text = data.get('full_text', '')
                    
                    # Count exercise markers in text
                    exercise_markers = len(re.findall(r'تمرين\s*\d+', full_text))
                    
                    # Count instruction markers
                    instruction_markers = len(re.findall(r'التعليمة\s*\d+-\d+', full_text))
                    
                    # Count point markers like "(7 ن)" or "7 ـﻌﻡ"
                    point_markers = len(re.findall(r'\([\d.]+\s*ن\)|[\d.]+\s*ـﻌﻡ', full_text))
                    
                    all_exams.append({
                        'file': json_file.name,
                        'trimester': data.get('trimester'),
                        'text_length': len(full_text),
                        'exercise_markers': exercise_markers,
                        'instruction_markers': instruction_markers,
                        'point_markers': point_markers,
                        'has_exercises': len(data.get('exercises', [])) > 0,
                        'data': data
                    })
    
    # Print summary
    print(f'Total exams: {len(all_exams)}')
    print(f'By trimester: T1={sum(1 for e in all_exams if e["trimester"]==1)}, '
          f'T2={sum(1 for e in all_exams if e["trimester"]==2)}, '
          f'T3={sum(1 for e in all_exams if e["trimester"]==3)}')
    print(f'Avg text length: {sum(e["text_length"] for e in all_exams) / len(all_exams):.0f} chars')
    print(f'With exercises parsed: {sum(1 for e in all_exams if e["has_exercises"])}')
    print(f'Avg exercise markers: {sum(e["exercise_markers"] for e in all_exams) / len(all_exams):.1f}')
    print(f'Avg instruction markers: {sum(e["instruction_markers"] for e in all_exams) / len(all_exams):.1f}')
    print(f'Avg point markers: {sum(e["point_markers"] for e in all_exams) / len(all_exams):.1f}')
    
    # Show sample files
    print('\nSample exams by trimester:')
    for t in [1, 2, 3]:
        t_exams = [e for e in all_exams if e['trimester'] == t]
        print(f'\nTrimester {t}: {len(t_exams)} exams')
        if t_exams:
            sample = t_exams[0]
            print(f'  Sample: {sample["file"]}')
            print(f'    Text length: {sample["text_length"]} chars')
            print(f'    Exercise markers: {sample["exercise_markers"]}')
            print(f'    Instruction markers: {sample["instruction_markers"]}')
            print(f'    Point markers: {sample["point_markers"]}')
    
    return all_exams

if __name__ == '__main__':
    analyze_extracted_data()
