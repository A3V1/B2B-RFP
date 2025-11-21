"""
Response Builder Agent: Generates the final proposal response.
Creates technical and commercial response sections.
"""
import json
from typing import Dict, Any
from .llm import get_response_llm, HumanMessage, SystemMessage
from .state import RFPState


RESPONSE_SYSTEM_PROMPT = """You are an expert technical writer for B2B cable manufacturing proposals.

Generate a professional RFP response based on the analysis provided.

Create three sections:

1. **Proposal Summary** (2-3 paragraphs):
   - Brief company introduction (assume we are a leading cable manufacturer)
   - Overview of our capability to meet the requirements
   - Key strengths and differentiators

2. **Technical Response** (structured):
   - Compliance matrix showing requirement vs our offering
   - Technical specifications of proposed products
   - Quality certifications and standards compliance
   - Delivery capability

3. **Commercial Response** (structured):
   - Pricing summary (use matched component prices)
   - Payment terms (standard: 30% advance, 70% on delivery)
   - Validity period (standard: 90 days)
   - Warranty terms (standard: 12 months from delivery)

Return JSON:
{
    "proposal_summary": "Professional summary text...",
    "technical_response": "Detailed technical response...",
    "commercial_response": "Commercial terms and pricing...",
    "total_estimated_value": 1250000,
    "currency": "INR"
}

Use professional language suitable for government/corporate tenders.
Format responses with clear headings and bullet points (markdown).
"""


def response_agent(state: RFPState) -> Dict[str, Any]:
    """
    Generate the final proposal response.

    Args:
        state: Current workflow state with all analysis complete

    Returns:
        Updated state with proposal content
    """
    requirement_matches = state.get("requirement_matches", [])
    requirements = state.get("requirements", [])
    project_summary = state.get("project_summary", "")
    overall_score = state.get("overall_score", 0)
    recommendations = state.get("recommendations", [])
    scoring_breakdown = state.get("scoring_breakdown", {})

    # Calculate total estimated value
    total_value = 0
    line_items = []

    for rm in requirement_matches:
        if rm.get("best_match"):
            specs = next(
                (r.get("specifications", {}) for r in requirements if r["id"] == rm["requirement_id"]),
                {}
            )
            quantity = specs.get("quantity", 1000)  # Default 1000 meters
            unit_price = rm["best_match"].get("price_per_meter", 0)
            line_total = quantity * unit_price
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

    # Prepare context for LLM
    context = {
        "project_summary": project_summary,
        "overall_match_score": overall_score,
        "recommendations": recommendations,
        "scoring_breakdown": scoring_breakdown,
        "line_items": line_items,
        "total_estimated_value": total_value,
        "matched_count": len([li for li in line_items if li["unit_price"] > 0]),
        "total_requirements": len(requirements)
    }

    llm = get_response_llm()

    messages = [
        SystemMessage(content=RESPONSE_SYSTEM_PROMPT),
        HumanMessage(content=f"Generate proposal response for:\n\n{json.dumps(context, indent=2)}")
    ]

    try:
        response = llm.invoke(messages)
        response_text = response.content

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        parsed = json.loads(response_text.strip())

        return {
            "proposal_summary": parsed.get("proposal_summary", ""),
            "technical_response": parsed.get("technical_response", ""),
            "commercial_response": parsed.get("commercial_response", ""),
            "current_agent": "response",
            "errors": []
        }

    except Exception as e:
        # Fallback response
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
