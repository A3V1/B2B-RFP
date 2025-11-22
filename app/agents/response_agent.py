"""
Response Builder Agent: Generates the final proposal response.
Creates technical and commercial response sections.
"""
import json
from typing import Dict, Any
from .llm import get_response_llm, HumanMessage, SystemMessage
from .state import RFPState
from .json_utils import extract_json_from_response, sanitize_for_json
from .logger import (
    log_agent_start, log_agent_end, log_step, log_info,
    log_success, log_error, log_warning, log_llm_call, log_llm_response,
    log_section_divider
)


RESPONSE_SYSTEM_PROMPT = """You are an expert technical writer for B2B cable manufacturing proposals.

Generate a professional RFP response based on the analysis provided.

Create three sections:

1. **Proposal Summary** (2-3 paragraphs):
   - Company introduction (ISO 9001:2015 certified cable manufacturer)
   - Capability overview with specific match percentage from the data
   - Key strengths: quality assurance, delivery capability, competitive pricing

2. **Technical Response** (use markdown formatting):
   - Compliance matrix as markdown table (| Req | Product | Status |)
   - Technical specifications of matched products
   - Quality certifications (IS/IEC standards, BIS, ISO 9001:2015)
   - Delivery capability with lead times
   - Note any gaps or deviations

3. **Commercial Response** (use markdown formatting):
   - Pricing schedule as markdown table with line items
   - Total estimated value from the data provided
   - Payment: 30% advance, 70% on delivery
   - Validity: 90 days
   - Warranty: 12 months from delivery

CRITICAL: Return ONLY a valid JSON object. No text before or after.
{
    "proposal_summary": "markdown text here",
    "technical_response": "markdown text with tables here",
    "commercial_response": "markdown text with pricing table here",
    "total_estimated_value": number,
    "currency": "INR"
}
"""


def response_agent(state: RFPState) -> Dict[str, Any]:
    """
    Generate the final proposal response.

    Args:
        state: Current workflow state with all analysis complete

    Returns:
        Updated state with proposal content
    """
    log_agent_start("Response")

    requirement_matches = state.get("requirement_matches", [])
    requirements = state.get("requirements", [])
    project_summary = state.get("project_summary", "")
    overall_score = state.get("overall_score", 0)
    recommendations = state.get("recommendations", [])
    scoring_breakdown = state.get("scoring_breakdown", {})

    log_info("Overall Score", f"{overall_score}%")
    log_info("Requirement matches", len(requirement_matches))

    # Calculate total estimated value
    log_step("Calculating pricing...")
    total_value = 0
    line_items = []

    for rm in requirement_matches:
        if rm.get("best_match"):
            specs = next(
                (r.get("specifications", {}) for r in requirements if r["id"] == rm["requirement_id"]),
                {}
            )
            # Ensure quantity and unit_price are valid numbers
            quantity = specs.get("quantity") if specs.get("quantity") else 1000  # Default 1000 meters
            unit_price = rm["best_match"].get("price_per_meter") or 0

            # Ensure both are numeric before multiplication
            try:
                quantity = float(quantity)
                unit_price = float(unit_price)
                line_total = quantity * unit_price
            except (TypeError, ValueError):
                quantity = 1000
                unit_price = 0
                line_total = 0

            total_value += line_total

            line_items.append({
                "requirement_id": rm["requirement_id"],
                "description": rm["requirement_description"],
                "product": rm["best_match"]["name"],
                "sku": rm["best_match"]["sku"],
                "quantity": quantity,
                "unit": specs.get("quantity_unit", "meters"),
                "unit_price": unit_price,
                "line_total": line_total,
                "in_stock": rm["best_match"]["in_stock"],
                "lead_time": rm["best_match"]["lead_time_days"]
            })

    log_info("Line items", len(line_items))
    log_info("Total estimated value", f"₹{total_value:,.2f}")

    # Prepare context for LLM - sanitize to remove control characters
    log_step("Preparing context for proposal generation...")
    context = sanitize_for_json({
        "project_summary": project_summary,
        "overall_match_score": overall_score,
        "recommendations": recommendations,
        "scoring_breakdown": scoring_breakdown,
        "line_items": line_items,
        "total_estimated_value": total_value,
        "matched_count": len([li for li in line_items if li["unit_price"] > 0]),
        "total_requirements": len(requirements)
    })

    log_step("Initializing LLM...")
    llm = get_response_llm()

    # Use compact JSON to reduce token usage
    context_json = json.dumps(context, ensure_ascii=True, separators=(',', ':'))

    messages = [
        SystemMessage(content=RESPONSE_SYSTEM_PROMPT),
        HumanMessage(content=f"Generate proposal response for this RFP analysis:\n{context_json}")
    ]

    log_llm_call(llm.model, "Generate proposal sections...")

    try:
        response = llm.invoke(messages)
        response_text = response.content
        log_llm_response(response_text)

        log_step("Parsing proposal response...")
        # Use robust JSON extraction
        parsed = extract_json_from_response(response_text)

        log_section_divider("Proposal Generated")
        log_success("Proposal Summary generated")
        log_info("Summary length", f"{len(parsed.get('proposal_summary', ''))} chars")
        log_success("Technical Response generated")
        log_info("Technical length", f"{len(parsed.get('technical_response', ''))} chars")
        log_success("Commercial Response generated")
        log_info("Commercial length", f"{len(parsed.get('commercial_response', ''))} chars")

        log_agent_end("Response", success=True)

        return {
            "proposal_summary": parsed.get("proposal_summary", ""),
            "technical_response": parsed.get("technical_response", ""),
            "commercial_response": parsed.get("commercial_response", ""),
            "current_agent": "response",
            "errors": []
        }

    except json.JSONDecodeError as e:
        # JSON parsing failed - use fallback
        log_error(f"JSON parse error: {e}")
        log_warning("Using fallback template...")

        log_agent_end("Response", success=False)

        return {
            "proposal_summary": generate_fallback_summary(context),
            "technical_response": generate_fallback_technical(line_items),
            "commercial_response": generate_fallback_commercial(line_items, total_value),
            "current_agent": "response",
            "errors": [f"Response Agent: JSON parse failed, using template"]
        }

    except Exception as e:
        # Other errors - use fallback
        log_error(f"Error: {e}")
        log_warning("Using fallback template...")

        log_agent_end("Response", success=False)

        return {
            "proposal_summary": generate_fallback_summary(context),
            "technical_response": generate_fallback_technical(line_items),
            "commercial_response": generate_fallback_commercial(line_items, total_value),
            "current_agent": "response",
            "errors": [f"Response Agent: LLM failed, using template: {str(e)}"]
        }


def generate_fallback_summary(context: dict) -> str:
    """Generate a basic proposal summary."""
    return f"""## Proposal Summary

We are pleased to submit our proposal in response to your tender for electrical cables and wires.

As a leading manufacturer of power and control cables, we have carefully reviewed your requirements
and are confident in our ability to meet your specifications. Our analysis shows a **{context['overall_match_score']:.0f}%**
match rate with your technical requirements.

We have matched **{context['matched_count']}** out of **{context['total_requirements']}** line items
from our standard product range. Our proposed solution includes high-quality cables manufactured
to IS/IEC standards with full test certifications.

We look forward to your favorable consideration of our proposal.
"""


def generate_fallback_technical(line_items: list) -> str:
    """Generate basic technical response."""
    lines = ["## Technical Response\n", "### Compliance Matrix\n"]
    lines.append("| Req ID | Description | Proposed Product | SKU | Compliance |")
    lines.append("|--------|-------------|-----------------|-----|------------|")

    for item in line_items:
        compliance = "✓ Full" if item["unit_price"] > 0 else "⚠ Partial"
        lines.append(f"| {item['requirement_id']} | {item['description'][:30]}... | {item['product']} | {item['sku']} | {compliance} |")

    lines.append("\n### Quality & Standards")
    lines.append("- All products manufactured as per IS/IEC standards")
    lines.append("- ISO 9001:2015 certified manufacturing facility")
    lines.append("- Full routine and type test certificates provided")

    return "\n".join(lines)


def generate_fallback_commercial(line_items: list, total_value: float) -> str:
    """Generate basic commercial response."""
    lines = ["## Commercial Response\n", "### Pricing Schedule\n"]
    lines.append("| Item | Product | Qty | Unit | Rate (INR) | Amount (INR) |")
    lines.append("|------|---------|-----|------|------------|--------------|")

    for i, item in enumerate(line_items, 1):
        lines.append(
            f"| {i} | {item['product'][:25]} | {item['quantity']:,} | {item['unit']} | "
            f"₹{item['unit_price']:,.2f} | ₹{item['line_total']:,.2f} |"
        )

    lines.append(f"\n**Total Estimated Value: ₹{total_value:,.2f}**")
    lines.append("\n### Terms & Conditions")
    lines.append("- **Payment Terms:** 30% advance with order, 70% against delivery")
    lines.append("- **Delivery:** As per schedule, ex-works")
    lines.append("- **Validity:** 90 days from date of submission")
    lines.append("- **Warranty:** 12 months from date of delivery")
    lines.append("- **Taxes:** GST extra as applicable")

    return "\n".join(lines)
