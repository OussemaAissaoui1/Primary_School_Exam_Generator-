"""LangGraph shared state definition for the exam generation pipeline."""

from typing import TypedDict, Optional


class ExamState(TypedDict):
    trimester: int
    reference_exams: list[dict]       # parsed from PDFs
    patterns: dict                    # structure patterns per trimester
    curriculum: dict                  # chapters + skills for trimester
    exam_text: str                    # raw generated exam in Arabic
    exam_structured: dict             # parsed exercises + points
    grading_schema: dict              # criteria → instructions + score levels
    correction: dict                  # solutions + grading table
    validation_passed: bool
    validation_errors: list[str]
    exam_pdf_path: str
    correction_pdf_path: str
    error: Optional[str]
