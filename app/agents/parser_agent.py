"""
Parser Agent: Extracts and structures sections from RFP documents.
First agent in the pipeline - takes raw RFP text and identifies key sections.
"""
import json
from typing import Dict, Any
from .llm import get_parser_llm, HumanMessage, SystemMessage
from .state import RFPState


PARSER_SYSTEM_PROMPT = """You are an expert RFP document parser specializing in electrical cable and wire procurement documents.

Your job is to analyze the RFP text and extract structured sections.

Look for these common sections in RFPs:
1. **Scope of Work** - What needs to be supplied/done
2. **Technical Specifications** - Detailed requirements for cables/wires (voltage, conductor, insulation, etc.)
3. **Quantity Schedule** - Items and quantities required
4. **Delivery Terms** - Timeline, location, schedule
5. **Commercial Terms** - Payment terms, pricing format, validity
6. **Compliance/Standards** - Required certifications, standards (IS, IEC, BS)
7. **Testing Requirements** - Required tests (routine, type, acceptance)
8. **Documentation** - Required documents, certificates
9. **Warranty/Guarantee** - Terms and duration
10. **Eligibility/Qualification** - Vendor requirements

For each section found, extract:
- Section name
- Full content of that section
- Page number if mentioned

Return your response as a JSON object with this structure:
{
    "sections": [
        {
            "name": "Section Name",
            "content": "Full section content...",
            "page_number": null
        }
    ],
    "document_type": "RFP/Tender/EOI/etc",
    "issuing_authority": "Organization name if found"
}

Be thorough - extract ALL relevant sections even if they have different names than listed above.
If a section is not found, don't include it.
"""


def parser_agent(state: RFPState) -> Dict[str, Any]:
    """
    Parse RFP document into structured sections.

    Args:
        state: Current workflow state with rfp_text

    Returns:
        Updated state with parsed sections
    """
    llm = get_parser_llm()

    messages = [
        SystemMessage(content=PARSER_SYSTEM_PROMPT),
        HumanMessage(content=f"Parse the following RFP document:\n\n{state['rfp_text']}")
    ]

    try:
        response = llm.invoke(messages)
        response_text = response.content

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        parsed = json.loads(response_text.strip())

        sections = []
        for section in parsed.get("sections", []):
            sections.append({
                "name": section.get("name", "Unknown"),
                "content": section.get("content", ""),
                "page_number": section.get("page_number")
            })

        return {
            "sections": sections,
            "current_agent": "parser",
            "errors": []
        }

    except json.JSONDecodeError as e:
        return {
            "sections": [],
            "current_agent": "parser",
            "errors": [f"Parser Agent: Failed to parse LLM response as JSON: {str(e)}"]
        }
    except Exception as e:
        return {
            "sections": [],
            "current_agent": "parser",
            "errors": [f"Parser Agent: {str(e)}"]
        }
