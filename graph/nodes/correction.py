"""Node 5: Generate full correction / answer key using LLM + sympy verification."""

import re
from dotenv import load_dotenv
from graph.nodes.llm_utils import get_llm, invoke_with_retry
from langchain_core.prompts import ChatPromptTemplate
from sympy import sympify, SympifyError

load_dotenv()

SYSTEM_PROMPT = """أنت تكتب عناصر الإجابة الرسمية لفرض رياضيات تونسي للسنة السادسة ابتدائي.
لكل تعليمة يجب أن تكتب الحل بالتفصيل كالتالي:

1. خطوات الحل: اكتب كل عملية حسابية في سطر مستقل مع شرح ما تفعله
   مثال:
   - وزن السلع في الصندوق الواحد = الوزن الكلي - وزن الصندوق الفارغ
   - وزن السلع = 35 − 5 = 30 كغ
   - الوزن الجملي = 30 × 250 = 7500 كغ
2. الجواب النهائي: اكتب سطرا يبدأ بكلمة "الجواب:" متبوعا بالنتيجة النهائية
3. توزيع النقاط: اكتب سطرا يوضح التوزيع مثل:
   "1 ن للعملية الأولى + 1 ن للعملية الثانية + 0.5 ن للنتيجة"

قواعد:
- المجموع الكلي = 20 نقطة بالضبط
- حافظ على نفس ترقيم التمارين والتعليمات
- اكتب بالعربية الفصحى فقط
- لا تستعمل markdown (لا # ولا **)
- لكل تعليمة متعددة المراحل، فصّل كل مرحلة في سطر مستقل
"""

HUMAN_TEMPLATE = """هذا هو نص الفرض:

{exam_text}

اكتب عناصر الإجابة الكاملة والمفصلة مع توزيع النقاط. المجموع = 20 نقطة.
لا تستعمل markdown.
"""


def _verify_arithmetic_in_correction(text: str) -> str:
    """Silently fix any arithmetic errors in the correction text."""
    pattern = r'(\d+(?:[.,]\d+)?(?:\s*[+\-×÷x*/]\s*\d+(?:[.,]\d+)?)+)\s*=\s*(\d+(?:[.,]\d+)?)'
    
    def _fix_match(m):
        expr_raw = m.group(1)
        stated = m.group(2).replace(',', '.')
        expr = expr_raw.replace(',', '.').replace('×', '*').replace('÷', '/').replace('x', '*').strip()
        try:
            computed = float(sympify(expr))
            stated_f = float(stated)
            if abs(computed - stated_f) > 0.001:
                if computed == int(computed):
                    return f"{expr_raw} = {int(computed)}"
                else:
                    return f"{expr_raw} = {computed:g}"
        except (SympifyError, ValueError, TypeError):
            pass
        return m.group(0)
    
    return re.sub(pattern, _fix_match, text)


def _build_grading_table(exam_text: str, correction_text: str) -> list[dict]:
    """Build the grading table from the exam structure."""
    table = []
    # Parse exercise headers
    exercises = re.split(r'(تمرين\s*\d+)', exam_text)
    
    i = 1
    while i < len(exercises):
        header = exercises[i].strip()
        body = exercises[i + 1] if i + 1 < len(exercises) else ""
        
        ex_num_match = re.search(r'تمرين\s*(\d+)', header)
        ex_num = ex_num_match.group(1) if ex_num_match else str((i // 2) + 1)
        
        # Find all instructions with points in this block
        instr_matches = re.finditer(r'التعليمة\s*(\d+)\s*\((\d+(?:[.,]\d+)?)\s*ن\)', body)
        for instr_m in instr_matches:
            table.append({
                "exercise": f"تمرين {ex_num}",
                "instruction": f"التعليمة {instr_m.group(1)}",
                "points": float(instr_m.group(2).replace(',', '.')),
            })
        
        # If no instructions found, extract points from header
        if not any(t["exercise"] == f"تمرين {ex_num}" for t in table):
            pt_match = re.search(r'\((\d+(?:[.,]\d+)?)\s*ن\)', header + body)
            if pt_match:
                table.append({
                    "exercise": f"تمرين {ex_num}",
                    "instruction": "المجموع",
                    "points": float(pt_match.group(1).replace(',', '.')),
                })
        
        i += 2
    
    # If table is empty, try extracting all point annotations
    if not table:
        all_points = re.finditer(r'\((\d+(?:[.,]\d+)?)\s*ن\)', exam_text)
        for idx, pt_m in enumerate(all_points, 1):
            table.append({
                "exercise": f"سؤال {idx}",
                "instruction": "",
                "points": float(pt_m.group(1).replace(',', '.')),
            })
    
    return table


def correction_node(state: dict) -> dict:
    """LangGraph node: generate the full correction with grading table."""
    exam_text = state["exam_text"]

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_TEMPLATE),
    ])

    llm = get_llm(temperature=0.3, max_tokens=4096)

    chain = prompt | llm

    response = invoke_with_retry(chain, {"exam_text": exam_text})
    correction_text = response.content.strip()

    # Verify and fix arithmetic in correction
    correction_text = _verify_arithmetic_in_correction(correction_text)

    # Build grading table
    grading_table = _build_grading_table(exam_text, correction_text)

    return {
        "correction": {
            "text": correction_text,
            "grading_table": grading_table,
            "total_points": sum(entry["points"] for entry in grading_table),
        }
    }
