"""Node 4: Quality-check exam against Tunisian inspection grid + enforce numeric validity."""

import re
import json as _json
from dotenv import load_dotenv
from graph.nodes.llm_utils import get_llm, invoke_with_retry
from langchain_core.prompts import ChatPromptTemplate
from sympy import sympify, SympifyError

load_dotenv()

# ── Quality rules from the Tunisian inspection grid ──────────────────────────
EXAM_QUALITY_RULES = {
    "originality":     "السند يجب أن يصف وضعية من الحياة اليومية الواقعية، وليس مسألة رياضية مجردة",
    "clarity":         "كل تعليمة يجب أن تكون واضحة وغير قابلة للتأويل",
    "alignment":       "كل تعليمة يجب أن تنبثق منطقيًا من سندها",
    "language_level":  "اللغة العربية يجب أن تكون مناسبة لمستوى السنة السادسة ابتدائي",
    "75_percent_rule": "على الأقل 75% من التعليمات يجب أن يكون في متناول التلميذ المتوسط",
    "time_limit":      "يجب أن يكون الفرض قابلًا للإنجاز في 60 دقيقة",
    "three_exercises": "يجب أن يحتوي الفرض على 3 تمارين على الأقل",
}

AUDIT_SYSTEM_PROMPT = """أنت مفتش تربوي تونسي متخصص في مراجعة فروض المراقبة للسنة السادسة ابتدائي.
مهمتك مراجعة الفرض التالي وفق معايير الجودة المحددة.

لكل معيار، قيّم الفرض وحدد:
- "pass": المعيار محقق
- "fail": المعيار غير محقق مع وصف المشكلة
- "warning": المعيار محقق جزئيًا

أجب بصيغة JSON فقط:
{{
  "originality": {{"status": "pass|fail|warning", "note": "..."}},
  "clarity": {{"status": "pass|fail|warning", "note": "..."}},
  "alignment": {{"status": "pass|fail|warning", "note": "..."}},
  "language_level": {{"status": "pass|fail|warning", "note": "..."}},
  "75_percent_rule": {{"status": "pass|fail|warning", "note": "..."}},
  "time_limit": {{"status": "pass|fail|warning", "note": "..."}},
  "three_exercises": {{"status": "pass|fail|warning", "note": "..."}}
}}
"""

AUDIT_HUMAN = """راجع الفرض التالي:

{exam_text}

المعايير التي يجب التحقق منها:
{rules}

أجب بـ JSON فقط.
"""


def _extract_point_values(text: str) -> list[tuple[str, float]]:
    matches = re.finditer(r'\((\d+(?:[.,]\d+)?)\s*ن\)', text)
    return [(m.group(0), float(m.group(1).replace(',', '.'))) for m in matches]


def _extract_exercise_blocks(text: str) -> list[dict]:
    parts = re.split(r'(تمرين\s*\d+\s*\([^)]*\))', text)
    exercises, i = [], 1
    while i < len(parts):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        num_match = re.search(r'تمرين\s*(\d+)', header)
        ex_num = int(num_match.group(1)) if num_match else len(exercises) + 1
        hpt = re.search(r'\((\d+(?:[.,]\d+)?)\s*ن\)', header)
        header_points = float(hpt.group(1).replace(',', '.')) if hpt else 0
        instructions = []
        for im in re.finditer(r'(التعليمة\s*\d+(?:-\d+)?\s*\(\d+(?:[.,]\d+)?\s*ن\)\s*:[^\n]*)', body):
            pt = re.search(r'\((\d+(?:[.,]\d+)?)\s*ن\)', im.group(1))
            pt_val = float(pt.group(1).replace(',', '.')) if pt else 0
            instructions.append({"text": im.group(1), "points": pt_val})
        exercises.append({
            "number": ex_num, "header": header, "body": body,
            "header_points": header_points, "instructions": instructions,
            "instruction_points_sum": sum(x["points"] for x in instructions),
        })
        i += 2
    return exercises


def _try_eval_arithmetic(text: str) -> list[dict]:
    findings = []
    pattern = r'(\d+(?:[.,]\d+)?(?:\s*[+\-×÷x*/]\s*\d+(?:[.,]\d+)?)+)\s*=\s*(\d+(?:[.,]\d+)?)'
    for m in re.finditer(pattern, text):
        expr_raw, stated_str = m.group(1), m.group(2).replace(',', '.')
        expr = expr_raw.replace(',', '.').replace('×', '*').replace('÷', '/').replace('x', '*').strip()
        try:
            computed = float(sympify(expr))
            stated = float(stated_str)
            if abs(computed - stated) > 0.001:
                findings.append({"original_match": m.group(0), "expression": expr_raw,
                                  "stated": stated, "computed": computed})
        except (SympifyError, ValueError, TypeError):
            pass
    return findings


def _check_two_thirds_rule(exam_text: str) -> list[str]:
    issues = []
    ex_blocks = re.split(r'(?=تمرين\s*\d+)', exam_text)
    for block in ex_blocks:
        ex_match = re.search(r'تمرين\s*(\d+)', block)
        if not ex_match:
            continue
        ex_num = ex_match.group(1)
        instrs = re.findall(r'التعليمة\s*\d+', block)
        count = len(instrs)
        if count > 4:
            issues.append(f"⚠️ تمرين {ex_num} يحتوي على {count} تعليمات — قد يستغرق وقتًا أطول من المسموح")
    return issues


def _run_quality_audit(exam_text: str) -> list[str]:
    errors = []
    try:
        llm = get_llm(temperature=0.0, max_tokens=2048)
        prompt = ChatPromptTemplate.from_messages([
            ("system", AUDIT_SYSTEM_PROMPT),
            ("human", AUDIT_HUMAN),
        ])
        rules_text = "\n".join(f"- {k}: {v}" for k, v in EXAM_QUALITY_RULES.items())
        response = (prompt | llm).invoke({"exam_text": exam_text, "rules": rules_text})
        content = response.content.strip()
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            audit = _json.loads(json_match.group(0))
            for rule, result in audit.items():
                status = result.get("status", "pass")
                note = result.get("note", "")
                rule_ar = EXAM_QUALITY_RULES.get(rule, rule)
                if status == "fail":
                    errors.append(f"❌ {rule_ar}: {note}")
                elif status == "warning":
                    errors.append(f"⚠️ {rule_ar}: {note}")
    except Exception as e:
        errors.append(f"تعذّر إجراء مراجعة الجودة: {str(e)}")
    return errors


def validator_node(state: dict) -> dict:
    """LangGraph node: validate points sum, arithmetic, and quality rules."""
    exam_text = state["exam_text"]

    # Normalize "نقاط"/"نقطة" → "ن"
    exam_text = re.sub(r'\((\d+(?:[.,]\d+)?)\s*نقاط?\)', r'(\1 ن)', exam_text)
    exam_text = re.sub(r'\((\d+(?:[.,]\d+)?)\s*نقطة?\)', r'(\1 ن)', exam_text)
    errors: list[str] = []

    # 1. Points validation
    instr_points = re.findall(r'التعليمة\s*\d+(?:-\d+)?\s*\((\d+(?:[.,]\d+)?)\s*ن\)', exam_text)
    instr_values = [float(p.replace(',', '.')) for p in instr_points]
    ex_header_points = re.findall(r'تمرين\s*\d+\s*\((\d+(?:[.,]\d+)?)\s*ن\)', exam_text)
    ex_header_values = [float(p.replace(',', '.')) for p in ex_header_points]

    if instr_values:
        total = sum(instr_values)
        point_entries = _extract_point_values(exam_text)
    elif ex_header_values:
        total = sum(ex_header_values)
        point_entries = [(f"({v:g} ن)", v) for v in ex_header_values]
    else:
        point_entries = _extract_point_values(exam_text)
        total = sum(v for _, v in point_entries)

    if abs(total - 20.0) > 0.01:
        diff = 20.0 - total
        errors.append(f"مجموع النقاط = {total} بدل 20. الفرق = {diff}")
        if point_entries:
            last_match, last_val = point_entries[-1]
            new_val = last_val + diff
            if new_val > 0:
                old_pt_str = f"({last_val:g} ن)"
                new_pt_str = f"({new_val:g} ن)"
                idx = exam_text.rfind(old_pt_str)
                if idx >= 0:
                    exam_text = exam_text[:idx] + new_pt_str + exam_text[idx + len(old_pt_str):]
                    errors.append(f"تم تعديل آخر نقطة من {last_val} إلى {new_val}")

    # 2. Arithmetic validation
    for issue in _try_eval_arithmetic(exam_text):
        correct_val = issue['computed']
        correct_str = str(int(correct_val)) if correct_val == int(correct_val) else f"{correct_val:g}"
        errors.append(f"خطأ حسابي تم تصحيحه: {issue['expression']} = {correct_str}")
        exam_text = exam_text.replace(f"= {issue['stated']}", f"= {correct_str}", 1)

    # 3. Two-thirds rule
    errors.extend(_check_two_thirds_rule(exam_text))

    # 4. LLM quality audit
    errors.extend(_run_quality_audit(exam_text))

    exercises_final = _extract_exercise_blocks(exam_text)
    exam_structured = {
        "exercises": [
            {"number": ex["number"], "header": ex["header"], "body": ex["body"],
             "header_points": ex["header_points"], "instructions": ex["instructions"]}
            for ex in exercises_final
        ],
        "total_points": (
            sum(ins["points"] for ex in exercises_final for ins in ex["instructions"])
            or sum(v for _, v in _extract_point_values(exam_text))
        ),
    }

    critical_errors = [e for e in errors if e.startswith("❌")]
    return {
        "exam_text": exam_text,
        "exam_structured": exam_structured,
        "validation_passed": len(critical_errors) == 0,
        "validation_errors": errors,
    }
