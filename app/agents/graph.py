"""
Main LangGraph workflow for RFP Analysis.
Orchestrates all agents in a sequential pipeline.
"""
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END

from .state import RFPState
from .parser_agent import parser_agent
from .analyzer_agent import analyzer_agent
from .matcher_agent import matcher_agent
from .scorer_agent import scorer_agent
from .response_agent import response_agent


def should_continue_after_parser(state: RFPState) -> str:
    """Decide whether to continue after parsing."""
    if state.get("sections") and len(state["sections"]) > 0:
        return "analyzer"
    return "end"


def should_continue_after_analyzer(state: RFPState) -> str:
    """Decide whether to continue after analysis."""
    if state.get("requirements") and len(state["requirements"]) > 0:
        return "matcher"
    return "scorer"  # Skip to scorer if no requirements (will report the issue)


def should_continue_after_matcher(state: RFPState) -> str:
    """Decide whether to continue after matching."""
    # Always continue to scorer
    return "scorer"


def should_continue_after_scorer(state: RFPState) -> str:
    """Decide whether to continue after scoring."""
    # Always continue to response builder
    return "response"


def create_rfp_analysis_graph() -> StateGraph:
    """
    Create the RFP analysis workflow graph.

    Pipeline:
    1. Parser -> Extract sections from RFP
    2. Analyzer -> Extract requirements from sections
    3. Matcher -> Match requirements to components
    4. Scorer -> Score overall match quality
    5. Response -> Generate proposal

    Returns:
        Compiled StateGraph
    """
    # Initialize the graph with state schema
    workflow = StateGraph(RFPState)

    # Add nodes (agents)
    workflow.add_node("parser", parser_agent)
    workflow.add_node("analyzer", analyzer_agent)
    workflow.add_node("matcher", matcher_agent)
    workflow.add_node("scorer", scorer_agent)
    workflow.add_node("response", response_agent)

    # Set entry point
    workflow.set_entry_point("parser")

    # Add edges with conditional routing
    workflow.add_conditional_edges(
        "parser",
        should_continue_after_parser,
        {
            "analyzer": "analyzer",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "analyzer",
        should_continue_after_analyzer,
        {
            "matcher": "matcher",
            "scorer": "scorer"
        }
    )

    workflow.add_edge("matcher", "scorer")
    workflow.add_edge("scorer", "response")
    workflow.add_edge("response", END)

    return workflow.compile()


# Create the compiled graph
rfp_analysis_graph = create_rfp_analysis_graph()


async def run_rfp_analysis(rfp_id: str, rfp_text: str) -> Dict[str, Any]:
    """
    Run the full RFP analysis pipeline.

    Args:
        rfp_id: Unique identifier for the RFP
        rfp_text: Full text content of the RFP document

    Returns:
        Complete analysis results
    """
    # Initialize state
    initial_state: RFPState = {
        "rfp_id": rfp_id,
        "rfp_text": rfp_text,
        "sections": [],
        "requirements": [],
        "project_summary": "",
        "budget_info": None,
        "timeline_info": None,
        "requirement_matches": [],
        "overall_score": 0,
        "scoring_breakdown": {},
        "recommendations": [],
        "proposal_summary": "",
        "technical_response": "",
        "commercial_response": "",
        "errors": [],
        "current_agent": ""
    }

    # Run the graph
    final_state = rfp_analysis_graph.invoke(initial_state)

    # Format results
    return {
        "rfp_id": rfp_id,
        "status": "completed" if not final_state.get("errors") else "completed_with_errors",
        "analysis": {
            "sections_found": len(final_state.get("sections", [])),
            "requirements_extracted": len(final_state.get("requirements", [])),
            "requirements_matched": len([
                rm for rm in final_state.get("requirement_matches", [])
                if rm.get("best_match")
            ]),
            "overall_score": final_state.get("overall_score", 0),
            "project_summary": final_state.get("project_summary", ""),
            "timeline": final_state.get("timeline_info"),
            "budget": final_state.get("budget_info")
        },
        "matches": final_state.get("requirement_matches", []),
        "scoring": {
            "overall_score": final_state.get("overall_score", 0),
            "breakdown": final_state.get("scoring_breakdown", {}),
            "recommendations": final_state.get("recommendations", [])
        },
        "proposal": {
            "summary": final_state.get("proposal_summary", ""),
            "technical": final_state.get("technical_response", ""),
            "commercial": final_state.get("commercial_response", "")
        },
        "errors": final_state.get("errors", [])
    }


def run_rfp_analysis_sync(rfp_id: str, rfp_text: str) -> Dict[str, Any]:
    """
    Synchronous version of run_rfp_analysis.
    """
    import asyncio
    return asyncio.run(run_rfp_analysis(rfp_id, rfp_text))
