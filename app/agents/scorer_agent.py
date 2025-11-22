"""
Scorer Agent: Evaluates overall match quality and generates recommendations.
Calculates coverage scores and identifies gaps.
"""
import json
from typing import Dict, Any, List
from .llm import get_analyzer_llm, HumanMessage, SystemMessage
from .state import RFPState
from .json_utils import extract_json_from_response
from .logger import (
    log_agent_start, log_agent_end, log_step, log_info,
    log_success, log_error, log_warning, log_llm_call, log_llm_response,
    log_summary_table, log_section_divider
)


SCORER_SYSTEM_PROMPT = """You are an expert at evaluating RFP response quality for electrical cable procurement.

Given the requirements and matched components, provide:
1. **Overall Score** (0-100): How well can we fulfill this RFP?
2. **Scoring Breakdown**: Score for each category
3. **Recommendations**: Actionable advice for the bid

Consider:
- **Technical Coverage**: Do our products meet the specs? (40%)
- **Price Competitiveness**: Are we likely competitive? (25%)
- **Availability**: Stock status and lead times (20%)
- **Compliance**: Standards and certifications (15%)

Return JSON:
{
    "overall_score": 75,
    "scoring_breakdown": {
        "technical_coverage": {
            "score": 80,
            "max": 40,
            "weighted_score": 32,
            "notes": "Strong match on voltage and conductor specs"
        },
        "price_competitiveness": {
            "score": 70,
            "max": 25,
            "weighted_score": 17.5,
            "notes": "Pricing appears market-competitive"
        },
        "availability": {
            "score": 85,
            "max": 20,
            "weighted_score": 17,
            "notes": "Most items in stock"
        },
        "compliance": {
            "score": 60,
            "max": 15,
            "weighted_score": 9,
            "notes": "Need to verify IS:7098 certification"
        }
    },
    "recommendations": [
        "PURSUE: Good overall match with 75% coverage",
        "GAP: Missing 3.5C x 185mm² cable - consider sourcing from partner",
        "ACTION: Verify IS:7098 Part 2 certification before submission",
        "RISK: Item 4 has 15-day lead time, delivery deadline is 10 days"
    ],
    "go_no_go": "GO",
    "confidence_level": "MEDIUM"
}
"""


def scorer_agent(state: RFPState) -> Dict[str, Any]:
    """
    Score the overall RFP match and generate recommendations.

    Args:
        state: Current workflow state with requirement matches

    Returns:
        Updated state with scores and recommendations
    """
    log_agent_start("Scorer")

    requirement_matches = state.get("requirement_matches", [])
    requirements = state.get("requirements", [])
    project_summary = state.get("project_summary", "")
    timeline_info = state.get("timeline_info", "")

    log_info("Requirement matches", len(requirement_matches))

    if not requirement_matches:
        log_warning("No matches to score")
        log_agent_end("Scorer", success=False)
        return {
            "overall_score": 0,
            "scoring_breakdown": {},
            "recommendations": ["No requirements were matched. Unable to evaluate."],
            "current_agent": "scorer",
            "errors": ["Scorer Agent: No matches to score"]
        }

    # Calculate basic stats
    log_step("Calculating statistics...")
    total_reqs = len(requirement_matches)
    matched_reqs = sum(1 for rm in requirement_matches if rm.get("best_match"))
    avg_coverage = sum(rm.get("coverage_score", 0) for rm in requirement_matches) / total_reqs if total_reqs > 0 else 0

    # Check availability
    in_stock_count = sum(
        1 for rm in requirement_matches
        if rm.get("best_match") and rm["best_match"].get("in_stock")
    )

    log_section_divider("Pre-Analysis Stats")
    log_info("Total requirements", total_reqs)
    log_info("Matched requirements", matched_reqs)
    log_info("Average coverage", f"{avg_coverage:.1f}%")
    log_info("In stock", f"{in_stock_count}/{matched_reqs}")

    # Prepare summary for LLM
    match_summary = {
        "total_requirements": total_reqs,
        "matched_requirements": matched_reqs,
        "average_coverage_score": round(avg_coverage, 1),
        "in_stock_ratio": f"{in_stock_count}/{matched_reqs}" if matched_reqs > 0 else "0/0",
        "project_summary": project_summary,
        "timeline": timeline_info,
        "requirement_details": []
    }

    for rm in requirement_matches:
        detail = {
            "requirement_id": rm["requirement_id"],
            "description": rm["requirement_description"],
            "coverage_score": rm["coverage_score"],
            "has_match": rm.get("best_match") is not None
        }
        if rm.get("best_match"):
            detail["best_match"] = {
                "name": rm["best_match"]["name"],
                "score": rm["best_match"]["score"],
                "in_stock": rm["best_match"]["in_stock"],
                "lead_time_days": rm["best_match"]["lead_time_days"],
                "price_per_meter": rm["best_match"]["price_per_meter"]
            }
        match_summary["requirement_details"].append(detail)

    log_step("Initializing LLM for scoring...")
    llm = get_analyzer_llm()

    messages = [
        SystemMessage(content=SCORER_SYSTEM_PROMPT),
        HumanMessage(content=f"Evaluate this RFP match:\n\n{json.dumps(match_summary, indent=2)}")
    ]

    log_llm_call(llm.model, "Generate scores and recommendations...")

    try:
        response = llm.invoke(messages)
        response_text = response.content
        log_llm_response(response_text)

        log_step("Parsing scoring results...")
        parsed = extract_json_from_response(response_text)

        overall_score = parsed.get("overall_score", avg_coverage)
        recommendations = parsed.get("recommendations", [])

        log_section_divider("Scoring Results")
        log_success(f"Overall Score: {overall_score}%")

        if recommendations:
            log_info("Recommendations", "")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"      {i}. {rec[:70]}...")

        log_agent_end("Scorer", success=True)

        return {
            "overall_score": overall_score,
            "scoring_breakdown": parsed.get("scoring_breakdown", {}),
            "recommendations": recommendations,
            "current_agent": "scorer",
            "errors": []
        }

    except Exception as e:
        log_error(f"LLM scoring failed: {e}")
        log_warning("Using fallback scoring...")

        log_agent_end("Scorer", success=False)

        # Fallback scoring
        return {
            "overall_score": avg_coverage,
            "scoring_breakdown": {
                "technical_coverage": {
                    "score": avg_coverage,
                    "max": 40,
                    "weighted_score": avg_coverage * 0.4,
                    "notes": f"Matched {matched_reqs}/{total_reqs} requirements"
                },
                "availability": {
                    "score": (in_stock_count / matched_reqs * 100) if matched_reqs > 0 else 0,
                    "max": 20,
                    "weighted_score": (in_stock_count / matched_reqs * 20) if matched_reqs > 0 else 0,
                    "notes": f"{in_stock_count} items in stock"
                }
            },
            "recommendations": [
                f"Match rate: {matched_reqs}/{total_reqs} requirements",
                f"Average coverage: {avg_coverage:.1f}%"
            ],
            "current_agent": "scorer",
            "errors": [f"Scorer Agent: LLM scoring failed, using fallback: {str(e)}"]
        }
