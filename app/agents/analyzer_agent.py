"""
Analyzer Agent: Extracts specific requirements from parsed RFP sections.
Identifies technical specs, quantities, and constraints for cable/wire products.
"""
import json
from typing import Dict, Any
from .llm import get_analyzer_llm, HumanMessage, SystemMessage
from .state import RFPState


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
    llm = get_analyzer_llm()

    # Combine sections for analysis
    sections_text = "\n\n".join([
        f"=== {s['name']} ===\n{s['content']}"
        for s in state.get("sections", [])
    ])

    if not sections_text:
        return {
            "requirements": [],
            "project_summary": "",
            "budget_info": None,
            "timeline_info": None,
            "current_agent": "analyzer",
            "errors": ["Analyzer Agent: No sections to analyze"]
        }

    messages = [
        SystemMessage(content=ANALYZER_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze these RFP sections and extract requirements:\n\n{sections_text}")
    ]

    try:
        response = llm.invoke(messages)
        response_text = response.content

        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        parsed = json.loads(response_text.strip())

        requirements = []
        for i, req in enumerate(parsed.get("requirements", [])):
            requirements.append({
                "id": req.get("id", f"REQ-{i+1:03d}"),
                "description": req.get("description", ""),
                "category": req.get("category", "technical"),
                "priority": req.get("priority", "mandatory"),
                "specifications": req.get("specifications", {})
            })

        return {
            "requirements": requirements,
            "project_summary": parsed.get("project_summary", ""),
            "budget_info": parsed.get("budget_info"),
            "timeline_info": parsed.get("timeline_info"),
            "current_agent": "analyzer",
            "errors": []
        }

    except json.JSONDecodeError as e:
        return {
            "requirements": [],
            "project_summary": "",
            "budget_info": None,
            "timeline_info": None,
            "current_agent": "analyzer",
            "errors": [f"Analyzer Agent: Failed to parse LLM response: {str(e)}"]
        }
    except Exception as e:
        return {
            "requirements": [],
            "project_summary": "",
            "budget_info": None,
            "timeline_info": None,
            "current_agent": "analyzer",
            "errors": [f"Analyzer Agent: {str(e)}"]
        }
