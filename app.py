"""Streamlit web UI for the Tunisian 6th-grade math exam generator."""

import os
import sys
from pathlib import Path

# Ensure the exam_generator directory is on the Python path
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(APP_DIR / ".env")

from graph.graph import build_graph

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="مولّد الفروض - السنة السادسة",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# RTL support via CSS
st.markdown("""
<style>
    body, .stMarkdown, .stText, .stTextArea textarea,
    [data-testid="stSidebar"], .stRadio label,
    .stAlert, .element-container {
        direction: rtl;
        text-align: right;
        font-family: 'Amiri', 'Traditional Arabic', 'Noto Naskh Arabic', serif;
    }
    .stRadio > div { direction: rtl; }
    .exam-preview {
        background: #fafafa;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 20px;
        direction: rtl;
        text-align: right;
        font-family: 'Amiri', serif;
        font-size: 15px;
        line-height: 2;
        white-space: pre-wrap;
        max-height: 600px;
        overflow-y: auto;
    }
    .correction-preview {
        background: #f0f7f0;
        border: 1px solid #b5d8b5;
        border-radius: 8px;
        padding: 20px;
        direction: rtl;
        text-align: right;
        font-family: 'Amiri', serif;
        font-size: 15px;
        line-height: 2;
        white-space: pre-wrap;
        max-height: 600px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎓 مولّد الفروض")
    st.subheader("السنة السادسة ابتدائي")
    st.divider()

    trimester = st.radio(
        "اختر الثلاثي:",
        options=[1, 2, 3],
        format_func=lambda x: f"الثلاثي {x}",
        index=0,
        horizontal=True,
    )

    st.divider()

    st.markdown("**الفروض المرجعية:** 2 نموذج لكلّ ثلاثي (مدمجة)")


# ─── Main area ────────────────────────────────────────────────────────────────
st.title("✨ مولّد فروض المراقبة في الرياضيات")
st.markdown(f"**الثلاثي المختار: {trimester}**")
st.divider()

# Step labels for progress
STEP_LABELS = [
    "تحليل الفروض المرجعية",
    "تحميل المنهج",
    "توليد الفرض",
    "التحقق من الأرقام",
    "بناء جدول المعايير",
    "إنشاء التصحيح",
    "تصدير الملفات",
]

STEP_NODE_MAP = {
    "analyze": 0,
    "curriculum": 1,
    "generate": 2,
    "validate": 3,
    "grading": 4,
    "correct": 5,
    "export": 6,
}

if st.button("✨ توليد الفرض", type="primary", use_container_width=True):
    graph = build_graph()

    # Progress tracking
    progress_bar = st.progress(0)
    status_container = st.empty()
    step_display = st.container()

    completed_steps = []
    total_steps = len(STEP_LABELS)

    initial_state = {
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

    final_state = None

    try:
        for event in graph.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                step_idx = STEP_NODE_MAP.get(node_name, -1)
                if step_idx >= 0:
                    completed_steps.append(step_idx)
                    progress = (step_idx + 1) / total_steps
                    progress_bar.progress(progress)

                    with step_display:
                        for i, label in enumerate(STEP_LABELS):
                            if i in completed_steps:
                                st.write(f"✅ {label}")
                            elif i == step_idx + 1:
                                st.write(f"⏳ {label}...")

                # Keep track of the latest state
                if node_output:
                    if final_state is None:
                        final_state = dict(initial_state)
                    final_state.update(node_output)

        progress_bar.progress(1.0)
        
        # Save to session_state so it persists across interactions (like downloading)
        if final_state:
            st.session_state.final_state = final_state
            
    except Exception as e:
        st.error(f"حدث خطأ: {str(e)}")
        st.exception(e)

# Display results if available in session_state
if "final_state" in st.session_state and st.session_state.final_state:
    final_state = st.session_state.final_state
    st.divider()

    # Validation warnings
    validation_errors = final_state.get("validation_errors", [])
    if validation_errors:
        with st.expander("⚠️ تعديلات تلقائية", expanded=False):
            for err in validation_errors:
                st.warning(err)

    # Preview columns
    col_exam, col_correction = st.columns(2)

    with col_exam:
        st.subheader("📄 معاينة الفرض")
        exam_text = final_state.get("exam_text", "")
        st.markdown(
            f'<div class="exam-preview">{exam_text}</div>',
            unsafe_allow_html=True,
        )

    with col_correction:
        st.subheader("📝 معاينة التصحيح")
        correction = final_state.get("correction", {})
        correction_text = correction.get("text", "") if isinstance(correction, dict) else str(correction)
        st.markdown(
            f'<div class="correction-preview">{correction_text}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Download buttons
    col_dl1, col_dl2 = st.columns(2)

    exam_pdf_path = final_state.get("exam_pdf_path", "")
    correction_pdf_path = final_state.get("correction_pdf_path", "")

    with col_dl1:
        if exam_pdf_path and os.path.exists(exam_pdf_path):
            with open(exam_pdf_path, "rb") as f:
                st.download_button(
                    label="📄 تحميل الفرض (PDF)",
                    data=f.read(),
                    file_name=f"exam_T{trimester}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.error("لم يتم إنشاء ملف الفرض")

    with col_dl2:
        if correction_pdf_path and os.path.exists(correction_pdf_path):
            with open(correction_pdf_path, "rb") as f:
                st.download_button(
                    label="📝 تحميل التصحيح (PDF)",
                    data=f.read(),
                    file_name=f"correction_T{trimester}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.error("لم يتم إنشاء ملف التصحيح")

    # Grading table display
    if isinstance(correction, dict) and correction.get("grading_table"):
        st.divider()
        st.subheader("📊 جدول التنقيط")
        grading_data = correction["grading_table"]
        import pandas as pd
        df = pd.DataFrame(grading_data)
        df.columns = ["التمرين", "التعليمة", "النقاط"]
        total_pts = df["النقاط"].sum()
        total_row = pd.DataFrame([{"التمرين": "المجموع", "التعليمة": "", "النقاط": total_pts}])
        df = pd.concat([df, total_row], ignore_index=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

   
