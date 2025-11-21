"""
Matcher Agent: Matches extracted requirements to components in the database.
Uses both database queries and LLM for intelligent matching.
"""
import json
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from .llm import get_analyzer_llm, HumanMessage, SystemMessage
from .state import RFPState, ComponentMatch, RequirementMatch

load_dotenv()


def get_db_session():
    """Get database session."""
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def query_components_for_requirement(session, specs: dict) -> List[dict]:
    """
    Query database for components matching the given specifications.
    Uses flexible matching - starts strict, loosens if no results.
    """
    from app.db.models import Component

    # Build query based on available specs
    filters = []

    # Voltage matching (exact or close)
    if specs.get("voltage_kv"):
        voltage = specs["voltage_kv"]
        filters.append(Component.voltage_kv == voltage)

    # Conductor type (exact match)
    if specs.get("conductor"):
        conductor = specs["conductor"]
        filters.append(Component.conductor.ilike(f"%{conductor}%"))

    # Cores (exact match)
    if specs.get("cores"):
        cores = specs["cores"]
        filters.append(Component.cores == cores)

    # Cross section (exact or close)
    if specs.get("cross_section_mm2"):
        cs = specs["cross_section_mm2"]
        filters.append(Component.cross_section_mm2 == cs)

    # Insulation type
    if specs.get("insulation"):
        insulation = specs["insulation"]
        filters.append(Component.insulation.ilike(f"%{insulation}%"))

    # Armour type
    if specs.get("armour"):
        armour = specs["armour"]
        filters.append(Component.armour.ilike(f"%{armour}%"))

    # Try with all filters first
    if filters:
        query = session.query(Component).filter(and_(*filters))
        results = query.limit(10).all()

        if results:
            return [component_to_dict(c) for c in results]

        # If no results, try with fewer filters (relaxed matching)
        # Priority: voltage > cross_section > conductor > insulation
        priority_filters = []
        if specs.get("voltage_kv"):
            priority_filters.append(Component.voltage_kv == specs["voltage_kv"])
        if specs.get("cross_section_mm2"):
            priority_filters.append(Component.cross_section_mm2 == specs["cross_section_mm2"])

        if priority_filters:
            query = session.query(Component).filter(and_(*priority_filters))
            results = query.limit(10).all()
            if results:
                return [component_to_dict(c) for c in results]

    # Fallback: get some components from same category
    if specs.get("voltage_kv"):
        if specs["voltage_kv"] <= 1.1:
            category = "LT Cable"
        elif specs["voltage_kv"] <= 33:
            category = "HT Cable"
        else:
            category = "EHV Cable"

        query = session.query(Component).filter(Component.category == category)
        results = query.limit(5).all()
        return [component_to_dict(c) for c in results]

    return []


def component_to_dict(component) -> dict:
    """Convert Component model to dictionary."""
    return {
        "component_id": component.id,
        "sku": component.sku,
        "name": component.name,
        "category": component.category,
        "voltage_kv": component.voltage_kv,
        "conductor": component.conductor,
        "cores": component.cores,
        "cross_section_mm2": component.cross_section_mm2,
        "insulation": component.insulation,
        "armour": component.armour,
        "standard": component.standard,
        "price_per_meter": component.price_per_meter or 0,
        "in_stock": component.in_stock,
        "lead_time_days": component.lead_time_days or 0
    }


MATCHER_SYSTEM_PROMPT = """You are an expert at matching cable/wire requirements to available products.

Given a requirement and a list of candidate components from the database, score each component's match.

Consider these factors for scoring (0-100):
1. **Voltage Rating** (25 points): Must match or exceed requirement
2. **Cross Section** (25 points): Exact match preferred
3. **Conductor Type** (15 points): Copper vs Aluminum must match
4. **Insulation Type** (15 points): XLPE, PVC, etc. should match
5. **Cores** (10 points): Must match configuration
6. **Armour Type** (10 points): SWA, AWA, Unarmoured

Return JSON:
{
    "scored_matches": [
        {
            "component_id": 123,
            "score": 85,
            "matched_specs": {
                "voltage_kv": true,
                "cross_section_mm2": true,
                "conductor": true,
                "insulation": false,
                "cores": true,
                "armour": true
            },
            "notes": "Good match, insulation differs (PVC vs XLPE)"
        }
    ],
    "best_match_id": 123,
    "coverage_score": 85
}

If no components match well, return empty scored_matches with coverage_score: 0.
"""


def score_matches_with_llm(requirement: dict, candidates: List[dict]) -> dict:
    """Use LLM to intelligently score component matches."""
    if not candidates:
        return {
            "scored_matches": [],
            "best_match_id": None,
            "coverage_score": 0
        }

    llm = get_analyzer_llm()

    req_text = f"""
Requirement: {requirement['description']}
Specifications: {json.dumps(requirement['specifications'], indent=2)}

Candidate Components:
{json.dumps(candidates, indent=2)}
"""

    messages = [
        SystemMessage(content=MATCHER_SYSTEM_PROMPT),
        HumanMessage(content=req_text)
    ]

    try:
        response = llm.invoke(messages)
        response_text = response.content

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return json.loads(response_text.strip())

    except Exception as e:
        # Fallback: simple matching without LLM
        return simple_score_matches(requirement, candidates)


def simple_score_matches(requirement: dict, candidates: List[dict]) -> dict:
    """Fallback simple scoring without LLM."""
    specs = requirement.get("specifications", {})
    scored = []

    for comp in candidates:
        score = 0
        matched = {}

        # Voltage (25 pts)
        if specs.get("voltage_kv") and comp.get("voltage_kv"):
            if comp["voltage_kv"] >= specs["voltage_kv"]:
                score += 25
                matched["voltage_kv"] = True
            else:
                matched["voltage_kv"] = False

        # Cross section (25 pts)
        if specs.get("cross_section_mm2") and comp.get("cross_section_mm2"):
            if comp["cross_section_mm2"] == specs["cross_section_mm2"]:
                score += 25
                matched["cross_section_mm2"] = True
            else:
                matched["cross_section_mm2"] = False

        # Conductor (15 pts)
        if specs.get("conductor") and comp.get("conductor"):
            if specs["conductor"].lower() in comp["conductor"].lower():
                score += 15
                matched["conductor"] = True
            else:
                matched["conductor"] = False

        # Insulation (15 pts)
        if specs.get("insulation") and comp.get("insulation"):
            if specs["insulation"].lower() in comp["insulation"].lower():
                score += 15
                matched["insulation"] = True
            else:
                matched["insulation"] = False

        # Cores (10 pts)
        if specs.get("cores") and comp.get("cores"):
            if specs["cores"] == comp["cores"]:
                score += 10
                matched["cores"] = True
            else:
                matched["cores"] = False

        # Armour (10 pts)
        if specs.get("armour") and comp.get("armour"):
            if specs["armour"].lower() in comp["armour"].lower():
                score += 10
                matched["armour"] = True
            else:
                matched["armour"] = False

        scored.append({
            "component_id": comp["component_id"],
            "score": score,
            "matched_specs": matched,
            "notes": ""
        })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    best_match_id = scored[0]["component_id"] if scored else None
    coverage_score = scored[0]["score"] if scored else 0

    return {
        "scored_matches": scored[:5],  # Top 5
        "best_match_id": best_match_id,
        "coverage_score": coverage_score
    }


def matcher_agent(state: RFPState) -> Dict[str, Any]:
    """
    Match requirements to components in the database.

    Args:
        state: Current workflow state with requirements

    Returns:
        Updated state with matched components
    """
    requirements = state.get("requirements", [])

    if not requirements:
        return {
            "requirement_matches": [],
            "current_agent": "matcher",
            "errors": ["Matcher Agent: No requirements to match"]
        }

    session = get_db_session()
    requirement_matches = []
    errors = []

    try:
        for req in requirements:
            specs = req.get("specifications", {})

            # Query database for candidates
            candidates = query_components_for_requirement(session, specs)

            # Score matches
            if candidates:
                match_result = score_matches_with_llm(req, candidates)

                # Build ComponentMatch objects
                matches = []
                for scored in match_result.get("scored_matches", []):
                    # Find the component in candidates
                    comp = next(
                        (c for c in candidates if c["component_id"] == scored["component_id"]),
                        None
                    )
                    if comp:
                        matches.append({
                            "component_id": comp["component_id"],
                            "sku": comp["sku"],
                            "name": comp["name"],
                            "category": comp["category"],
                            "score": scored["score"],
                            "matched_specs": scored["matched_specs"],
                            "price_per_meter": comp["price_per_meter"],
                            "in_stock": comp["in_stock"],
                            "lead_time_days": comp["lead_time_days"]
                        })

                best_match = matches[0] if matches else None

                requirement_matches.append({
                    "requirement_id": req["id"],
                    "requirement_description": req["description"],
                    "matches": matches,
                    "best_match": best_match,
                    "coverage_score": match_result.get("coverage_score", 0)
                })
            else:
                requirement_matches.append({
                    "requirement_id": req["id"],
                    "requirement_description": req["description"],
                    "matches": [],
                    "best_match": None,
                    "coverage_score": 0
                })

    except Exception as e:
        errors.append(f"Matcher Agent: {str(e)}")
    finally:
        session.close()

    return {
        "requirement_matches": requirement_matches,
        "current_agent": "matcher",
        "errors": errors
    }
