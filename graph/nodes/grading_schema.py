"""Node: Build Tunisian criteria-based grading schema (جدول إسناد الأعداد)."""

import re
from dotenv import load_dotenv
from graph.nodes.llm_utils import get_llm, invoke_with_retry
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# Fixed weights extracted from reference exams — sum to 20
CRITERIA_WEIGHTS = {
    "معـ1": {"max": 4.5, "min": 3.0, "partial": 1.5, "zero": 0},
    "معـ2": {"max": 4.5, "min": 3.0, "partial": 1.5, "zero": 0},
    "معـ3": {"max": 3.0, "min": 2.0, "partial": 1.0, "zero": 0},
    "معـ4": {"max": 3.0, "min": 2.0, "partial": 1.0, "zero": 0},
    "معـ5": {"max": 5.0, "min": 3.0, "partial": 2.0, "zero": 0},
}
# max total = 4.5+4.5+3+3+5 = 20 ✓

SYSTEM_PROMPT = """أنت خبير في بناء شبكات تقييم لفروض المراقبة التونسية للسنة السادسة ابتدائي.
مهمتك توزيع التعليمات على المعايير الخمسة (معـ1 إلى معـ5) وفق النظام التونسي الرسمي.

قواعد التوزيع:
- معـ1 و معـ2: تعليمات من صنف الفهم والتطبيق المباشر (أسهل)
- معـ3 و معـ4: تعليمات من صنف التطبيق في وضعيات مألوفة
- معـ5: التعليمة الأكثر تركيبًا وصعوبةً

قاعدة الثلثين: عدد التعليمات لكل معيار يجب أن يكون من مضاعفات 3 (1، 2، أو 3 تعليمات لكل معيار).

أجب بصيغة JSON فقط، بدون أي نص إضافي، مثال:
{{
  "معـ1": {{"instructions": ["التعليمة 1-1", "التعليمة 1-2"], "criterion_label": "التواصل"}},
  "معـ2": {{"instructions": ["التعليمة 2-1"], "criterion_label": "توظيف المعارف"}},
  "معـ3": {{"instructions": ["التعليمة 2-2"], "criterion_label": "حل مسائل"}},
  "معـ4": {{"instructions": ["التعليمة 3-1"], "criterion_label": "الإبداع"}},
  "معـ5": {{"instructions": ["التعليمة 3-2", "التعليمة 3-3"], "criterion_label": "التركيب"}}
}}
"""

HUMAN_TEMPLATE = """هذا نص الفرض:

{exam_text}

قم بتوزيع التعليمات على المعايير الخمسة (معـ1 إلى معـ5).
تذكر: معـ5 يجب أن يحتوي على أصعب التعليمات.
أجب بـ JSON فقط.
"""


def _parse_instructions_from_exam(exam_text: str) -> list[str]:
    """Extract all instruction labels from exam text."""
    instructions = []
    # Pattern: التعليمة X-Y or التعليمة N
    for m in re.finditer(r'التعليمة\s*(\d+(?:-\d+)?)', exam_text):
        label = f"التعليمة {m.group(1)}"
        if label not in instructions:
            instructions.append(label)
    return instructions


def _assign_instructions_to_criteria(instructions: list[str]) -> dict:
    """Fallback: distribute instructions evenly across criteria."""
    criteria_keys = ["معـ1", "معـ2", "معـ3", "معـ4", "معـ5"]
    n = len(instructions)

    if n == 0:
        return {k: {"instructions": []} for k in criteria_keys}

    # Distribute: معـ5 gets the last instruction(s), rest split among معـ1–معـ4
    # Try to make each criterion have at least 1 instruction (multiple of 1)
    assignment = {k: {"instructions": []} for k in criteria_keys}

    if n >= 5:
        per = n // 5
        remainder = n % 5
        idx = 0
        for i, key in enumerate(criteria_keys):
            count = per + (1 if i < remainder else 0)
            assignment[key]["instructions"] = instructions[idx: idx + count]
            idx += count
    else:
        # Fewer instructions than criteria: assign one per criterion, prioritising معـ1 first
        for i, instr in enumerate(instructions):
            assignment[criteria_keys[i]]["instructions"].append(instr)

    return assignment


def _enforce_two_thirds_rule(assignment: dict) -> dict:
    """Ensure each criterion has a count that is a multiple of 1 (≥1).
    If a criterion has 0 instructions, borrow or note it."""
    # The ⅔ rule means the count should be 1, 2, or 3 (multiples of 1 from the set)
    # In practice we just ensure no criterion is empty if possible
    empties = [k for k, v in assignment.items() if len(v["instructions"]) == 0]
    non_empties = [k for k, v in assignment.items() if len(v["instructions"]) > 1]

    for empty_key in empties:
        if non_empties:
            donor = non_empties[0]
            instr_list = assignment[donor]["instructions"]
            # Move the last instruction to the empty slot
            assignment[empty_key]["instructions"].append(instr_list.pop())
            if len(instr_list) <= 1:
                non_empties.pop(0)

    return assignment


def grading_schema_node(state: dict) -> dict:
    """LangGraph node: assign instructions to criteria and build score schema."""
    exam_text = state.get("exam_text", "")
    instructions = _parse_instructions_from_exam(exam_text)

    # Try LLM assignment first
    try:
        llm = get_llm(temperature=0.0, max_tokens=2048)
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_TEMPLATE),
        ])
        chain = prompt | llm
        response = invoke_with_retry(chain, {"exam_text": exam_text})
        content = response.content.strip()

        # Extract JSON from response
        import json
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            llm_assignment = json.loads(json_match.group(0))
            # Validate structure
            if all(k in llm_assignment for k in ["معـ1", "معـ2", "معـ3", "معـ4", "معـ5"]):
                assignment = llm_assignment
            else:
                assignment = _assign_instructions_to_criteria(instructions)
        else:
            assignment = _assign_instructions_to_criteria(instructions)
    except Exception:
        assignment = _assign_instructions_to_criteria(instructions)

    # Enforce two-thirds rule
    assignment = _enforce_two_thirds_rule(assignment)

    # Build full schema with score levels
    grading_schema = {}
    for criterion, weights in CRITERIA_WEIGHTS.items():
        instr_list = assignment.get(criterion, {}).get("instructions", [])
        label = assignment.get(criterion, {}).get("criterion_label", "")
        grading_schema[criterion] = {
            "instructions": instr_list,
            "criterion_label": label,
            "scores": {
                "انعدام التملك": weights["zero"],
                "دون التملك الأدنى": weights["partial"],
                "التملك الأدنى": weights["min"],
                "التملك الأقصى": weights["max"],
            },
            "max_score": weights["max"],
        }

    # Build instruction→criterion reverse map (used by exporter)
    instr_to_criterion = {}
    for criterion, data in grading_schema.items():
        for instr in data["instructions"]:
            instr_to_criterion[instr] = criterion

    return {
        "grading_schema": {
            "criteria": grading_schema,
            "instr_to_criterion": instr_to_criterion,
            "total_max": sum(v["max_score"] for v in grading_schema.values()),
        }
    }
