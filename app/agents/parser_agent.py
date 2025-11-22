"""
Parser Agent: Extracts and structures sections from RFP documents.
First agent in the pipeline - takes raw RFP text and identifies key sections.
"""
import json
from typing import Dict, Any
from .llm import get_parser_llm, HumanMessage, SystemMessage
from .state import RFPState
from .json_utils import extract_json_from_response
from .logger import (
    log_agent_start, log_agent_end, log_step, log_info,
    log_success, log_error, log_llm_call, log_llm_response,
    log_summary_table, log_data, log_warning
)


PARSER_SYSTEM_PROMPT = """You are an expert RFP document parser specializing in electrical cable and wire procurement documents.

Your job is to analyze the RFP text and extract structured sections.

Look for these common sections in RFPs:
1. Scope of Work - What needs to be supplied/done
2. Technical Specifications - Detailed requirements for cables/wires
3. Quantity Schedule - Items and quantities required
4. Delivery Terms - Timeline, location, schedule
5. Commercial Terms - Payment terms, pricing format, validity
6. Compliance/Standards - Required certifications, standards
7. Testing Requirements - Required tests
8. Documentation - Required documents, certificates
9. Warranty/Guarantee - Terms and duration
10. Eligibility/Qualification - Vendor requirements

IMPORTANT JSON FORMATTING RULES:
- Return ONLY valid JSON, no other text
- Use double quotes for all strings
- Escape special characters in content: use \\n for newlines, \\t for tabs
- Do not include actual line breaks inside string values
- Keep content concise - summarize long sections

Return JSON in this exact format:
{
    "sections": [
        {"name": "Section Name", "content": "Section content as single line...", "page_number": null}
    ],
    "document_type": "RFP",
    "issuing_authority": "Organization name"
}
"""


def parser_agent(state: RFPState) -> Dict[str, Any]:
    """
    Parse RFP document into structured sections.

    Args:
        state: Current workflow state with rfp_text

    Returns:
        Updated state with parsed sections
    """
    log_agent_start("Parser")

    rfp_text = state.get('rfp_text', '')
    log_info("Input RFP text length", f"{len(rfp_text)} characters")

    log_step("Initializing LLM...")
    llm = get_parser_llm()

    messages = [
        SystemMessage(content=PARSER_SYSTEM_PROMPT),
        HumanMessage(content=f"Parse the following RFP document:\n\n{rfp_text}")
    ]

    log_llm_call(llm.model, "Parse RFP document sections...")

    try:
        response = llm.invoke(messages)
        response_text = response.content
        log_llm_response(response_text)

        log_step("Parsing JSON response...")
        parsed = extract_json_from_response(response_text)

        sections = []
        for section in parsed.get("sections", []):
            sections.append({
                "name": section.get("name", "Unknown"),
                "content": section.get("content", ""),
                "page_number": section.get("page_number")
            })

        log_success(f"Extracted {len(sections)} sections")

        # Display sections table
        if sections:
            log_summary_table(
                ["#", "Section Name", "Content Length"],
                [[i+1, s["name"][:30], len(s["content"])] for i, s in enumerate(sections)]
            )

        log_agent_end("Parser", success=True)

        return {
            "sections": sections,
            "current_agent": "parser",
            "errors": []
        }

    except json.JSONDecodeError as e:
        log_error(f"JSON Parse Error: {str(e)}")
        log_warning("Raw LLM response (first 500 chars):")
        print(f"      {repr(response_text[:500])}")
        log_agent_end("Parser", success=False)
        return {
            "sections": [],
            "current_agent": "parser",
            "errors": [f"Parser Agent: Failed to parse LLM response as JSON: {str(e)}"]
        }
    except Exception as e:
        log_error(f"Error: {str(e)}")
        log_agent_end("Parser", success=False)
        return {
            "sections": [],
            "current_agent": "parser",
            "errors": [f"Parser Agent: {str(e)}"]
        }
