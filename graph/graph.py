"""LangGraph StateGraph builder and compiler for the exam generation pipeline."""

from langgraph.graph import StateGraph, END
from graph.state import ExamState
from graph.nodes.analyzer import analyzer_node
from graph.nodes.curriculum import curriculum_node
from graph.nodes.generator import generator_node
from graph.nodes.validator import validator_node
from graph.nodes.grading_schema import grading_schema_node
from graph.nodes.correction import correction_node
from graph.nodes.exporter import exporter_node


def build_graph():
    """Build and compile the exam generation LangGraph pipeline."""
    g = StateGraph(ExamState)

    g.add_node("analyze",       analyzer_node)
    g.add_node("curriculum",    curriculum_node)
    g.add_node("generate",      generator_node)
    g.add_node("validate",      validator_node)
    g.add_node("grading",       grading_schema_node)
    g.add_node("correct",       correction_node)
    g.add_node("export",        exporter_node)

    g.set_entry_point("analyze")
    g.add_edge("analyze",    "curriculum")
    g.add_edge("curriculum", "generate")
    g.add_edge("generate",   "validate")
    g.add_edge("validate",   "grading")
    g.add_edge("grading",    "correct")
    g.add_edge("correct",    "export")
    g.add_edge("export",     END)

    return g.compile()
