"""
Analyzer Agent: Extracts specific requirements from parsed RFP sections.
Identifies technical specs, quantities, and constraints for cable/wire products.
"""
import json
from typing import Dict, Any
from .llm import get_analyzer_llm, HumanMessage, SystemMessage
from .state import RFPState
from .json_utils import extract_json_from_response
from .logger import (
    log_agent_start, log_agent_end, log_step, log_info,
    log_success, log_error, log_warning, log_llm_call, log_llm_response,
    log_summary_table, log_section_divider
)


ANALYZER_SYSTEM_PROMPT = """You are a technical analyst specializing in electrical cables and wires procurement.

Your job is to extract SPECIFIC, ACTIONABLE requirements from RFP sections.

For each requirement, identify:
1. **Category**: technical, commercial, compliance, delivery
2. **Priority**: mandatory (must have), preferred (should have), optional (nice to have)
3. **Specifications**: Extract specific values for cables/wires:
   - voltage_kv: Voltage rating (e.g., 1.1, 11, 33 kV)
   - conductor: Copper or Aluminum
   - cores: Number of cores (1C, 2C, 3C, 4C, 3.5C)
   - cross_section_mm2: Cross-sectional area (e.g., 25, 50, 95, 120 mm²)
   - insulation: PVC, XLPE, EPR, etc.
   - armour: Unarmoured, SWA, AWA
   - standard: IS:1554, IS:7098, IEC, BS
   - fire_rating: FR, FRLS, FRLSH
   - application: Indoor, Outdoor, Underground
   - quantity: Number of meters/units required
   - quantity_unit: meters, km, coils, drums

Return a JSON object:
{
    "requirements": [
        {
            "id": "REQ-001",
            "description": "Supply of 3.5C x 95 sq.mm XLPE Aluminium cable",
            "category": "technical",
            "priority": "mandatory",
            "specifications": {
                "voltage_kv": 1.1,
                "conductor": "Aluminum",
                "cores": "3.5C",
                "cross_section_mm2": 95,
                "insulation": "XLPE",
                "armour": "SWA",
                "quantity": 5000,
                "quantity_unit": "meters"
            }
        }
    ],
    "project_summary": "Brief summary of the project/tender",
    "budget_info": "Any budget/price constraints mentioned",
    "timeline_info": "Delivery timeline requirements"
}

Extract ALL line items from quantity schedules. Be precise with specifications.
Use null for specifications not mentioned in the document.
"""


def analyzer_agent(state: RFPState) -> Dict[str, Any]:
    """
    Analyze parsed sections to extract specific requirements.

    Args:
        state: Current workflow state with parsed sections

    Returns:
        Updated state with extracted requirements
    """
    log_agent_start("Analyzer")

    sections = state.get("sections", [])
    log_info("Input sections", len(sections))

    # Combine sections for analysis
    sections_text = "\n\n".join([
        f"=== {s['name']} ===\n{s['content']}"
        for s in sections
    ])

    if not sections_text:
        log_warning("No sections to analyze")
        log_agent_end("Analyzer", success=False)
        return {
            "requirements": [],
            "project_summary": "",
            "budget_info": None,
            "timeline_info": None,
            "current_agent": "analyzer",
            "errors": ["Analyzer Agent: No sections to analyze"]
        }

    log_step("Initializing LLM...")
    llm = get_analyzer_llm()

    messages = [
        SystemMessage(content=ANALYZER_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze these RFP sections and extract requirements:\n\n{sections_text}")
    ]

    log_llm_call(llm.model, "Extract requirements from sections...")

    try:
        response = llm.invoke(messages)
        response_text = response.content
        log_llm_response(response_text)

        log_step("Parsing JSON response...")
        parsed = extract_json_from_response(response_text)

        requirements = []
        for i, req in enumerate(parsed.get("requirements", [])):
            requirements.append({
                "id": req.get("id", f"REQ-{i+1:03d}"),
                "description": req.get("description", ""),
                "category": req.get("category", "technical"),
                "priority": req.get("priority", "mandatory"),
                "specifications": req.get("specifications", {})
            })

        log_success(f"Extracted {len(requirements)} requirements")

        # Display requirements table
        if requirements:
            log_summary_table(
                ["ID", "Category", "Priority", "Description"],
                [[r["id"], r["category"], r["priority"], r["description"][:40] + "..."] for r in requirements]
            )

        log_section_divider("Project Info")
        log_info("Project Summary", parsed.get("project_summary", "N/A")[:100])
        log_info("Budget Info", parsed.get("budget_info", "N/A"))
        log_info("Timeline Info", parsed.get("timeline_info", "N/A"))

        log_agent_end("Analyzer", success=True)

        return {
            "requirements": requirements,
            "project_summary": parsed.get("project_summary", ""),
            "budget_info": parsed.get("budget_info"),
            "timeline_info": parsed.get("timeline_info"),
            "current_agent": "analyzer",
            "errors": []
        }

    except json.JSONDecodeError as e:
        log_error(f"JSON Parse Error: {str(e)}")
        log_agent_end("Analyzer", success=False)
        return {
            "requirements": [],
            "project_summary": "",
            "budget_info": None,
            "timeline_info": None,
            "current_agent": "analyzer",
            "errors": [f"Analyzer Agent: Failed to parse LLM response: {str(e)}"]
        }
    except Exception as e:
        log_error(f"Error: {str(e)}")
        log_agent_end("Analyzer", success=False)
        return {
            "requirements": [],
            "project_summary": "",
            "budget_info": None,
            "timeline_info": None,
            "current_agent": "analyzer",
            "errors": [f"Analyzer Agent: {str(e)}"]
        }
