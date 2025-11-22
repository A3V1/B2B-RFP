"""
Matcher Agent: Matches extracted requirements to OEM products in the database.
Uses both database queries and LLM for intelligent matching.

Updated for new schema with OEMProduct and JSON specifications.
"""
import json
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker, joinedload
import os
from dotenv import load_dotenv

from .llm import get_analyzer_llm, HumanMessage, SystemMessage
from .state import RFPState, ComponentMatch, RequirementMatch
from .json_utils import extract_json_from_response
from .logger import (
    log_agent_start, log_agent_end, log_step, log_info,
    log_success, log_error, log_warning, log_llm_call, log_llm_response,
    log_summary_table, log_section_divider
)

load_dotenv()


def get_db_session():
    """Get database session."""
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def query_oem_products_for_requirement(session, specs: dict) -> List[dict]:
    """
    Query database for OEM products matching the given specifications.
    Uses flexible matching with JSON specifications.
    """
    from app.db.models import OEMProduct, ProductPricing

    # Start with all products, filtered by category if we can determine it
    query = session.query(OEMProduct).options(
        joinedload(OEMProduct.manufacturer),
        joinedload(OEMProduct.pricing)
    )

    # Determine category from voltage
    if specs.get("voltage_kv"):
        voltage = specs["voltage_kv"]
        if voltage <= 1.1:
            query = query.filter(OEMProduct.product_category == "LT Cable")
        elif voltage <= 33:
            query = query.filter(OEMProduct.product_category == "HT Cable")
        else:
            query = query.filter(OEMProduct.product_category == "EHV Cable")

    # Get all matching products
    products = query.all()

    # Filter and score based on JSON specifications
    matching_products = []
    for product in products:
        product_specs = product.specifications or {}

        # Calculate a basic match score for filtering
        match_score = 0
        total_checks = 0

        # Check voltage
        if specs.get("voltage_kv") and product_specs.get("voltage_kv"):
            total_checks += 1
            if product_specs["voltage_kv"] >= specs["voltage_kv"]:
                match_score += 1

        # Check conductor
        if specs.get("conductor") and product_specs.get("conductor"):
            total_checks += 1
            if specs["conductor"].lower() in product_specs["conductor"].lower():
                match_score += 1

        # Check cores
        if specs.get("cores") and product_specs.get("cores"):
            total_checks += 1
            if specs["cores"] == product_specs["cores"]:
                match_score += 1

        # Check cross section
        if specs.get("cross_section_mm2") and product_specs.get("cross_section_mm2"):
            total_checks += 1
            if product_specs["cross_section_mm2"] == specs["cross_section_mm2"]:
                match_score += 1

        # Check insulation
        if specs.get("insulation") and product_specs.get("insulation"):
            total_checks += 1
            if specs["insulation"].lower() in product_specs["insulation"].lower():
                match_score += 1

        # Include product if it has any matches or if we have few products
        if total_checks == 0 or match_score > 0:
            matching_products.append({
                "product": product,
                "preliminary_score": match_score / max(total_checks, 1) * 100
            })

    # Sort by preliminary score and return top candidates
    matching_products.sort(key=lambda x: x["preliminary_score"], reverse=True)

    return [oem_product_to_dict(p["product"]) for p in matching_products[:10]]


def oem_product_to_dict(product) -> dict:
    """Convert OEMProduct model to dictionary."""
    specs = product.specifications or {}
    pricing = product.pricing

    return {
        "product_id": product.id,
        "sku": product.sku,
        "name": product.product_name,
        "category": product.product_category,
        "manufacturer": product.manufacturer.name if product.manufacturer else "Unknown",
        # Flatten specifications for compatibility
        "voltage_kv": specs.get("voltage_kv"),
        "conductor": specs.get("conductor"),
        "cores": specs.get("cores"),
        "cross_section_mm2": specs.get("cross_section_mm2"),
        "insulation": specs.get("insulation"),
        "armour": specs.get("armour"),
        "sheath": specs.get("sheath"),
        "standard": specs.get("standard"),
        "application": specs.get("application"),
        # Full specifications JSON
        "specifications": specs,
        # Pricing
        "price_per_meter": pricing.unit_price if pricing else 0,
        "price_per": pricing.price_per if pricing else "meter",
        "in_stock": True,  # Default for now
        "lead_time_days": 7  # Default for now
    }


MATCHER_SYSTEM_PROMPT = """You are an expert at matching cable/wire requirements to available OEM products.

Given a requirement and a list of candidate OEM products from the database, score each product's match.

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
            "product_id": 123,
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

If no products match well, return empty scored_matches with coverage_score: 0.
"""


def score_matches_with_llm(requirement: dict, candidates: List[dict]) -> dict:
    """Use LLM to intelligently score product matches."""
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

Candidate OEM Products:
{json.dumps(candidates, indent=2)}
"""

    messages = [
        SystemMessage(content=MATCHER_SYSTEM_PROMPT),
        HumanMessage(content=req_text)
    ]

    try:
        response = llm.invoke(messages)
        response_text = response.content
        return extract_json_from_response(response_text)

    except Exception as e:
        # Fallback: simple matching without LLM
        print(f"[Matcher Agent] LLM scoring failed: {e}, using fallback")
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
            "product_id": comp["product_id"],
            "score": score,
            "matched_specs": matched,
            "notes": ""
        })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    best_match_id = scored[0]["product_id"] if scored else None
    coverage_score = scored[0]["score"] if scored else 0

    return {
        "scored_matches": scored[:5],  # Top 5
        "best_match_id": best_match_id,
        "coverage_score": coverage_score
    }


def matcher_agent(state: RFPState) -> Dict[str, Any]:
    """
    Match requirements to OEM products in the database.

    Args:
        state: Current workflow state with requirements

    Returns:
        Updated state with matched products
    """
    log_agent_start("Matcher")

    requirements = state.get("requirements", [])
    log_info("Requirements to match", len(requirements))

    if not requirements:
        log_warning("No requirements to match")
        log_agent_end("Matcher", success=False)
        return {
            "requirement_matches": [],
            "current_agent": "matcher",
            "errors": ["Matcher Agent: No requirements to match"]
        }

    log_step("Connecting to database...")
    session = get_db_session()
    requirement_matches = []
    errors = []

    try:
        for i, req in enumerate(requirements):
            log_section_divider(f"Requirement {i+1}/{len(requirements)}: {req['id']}")
            log_info("Description", req['description'][:60] + "...")

            specs = req.get("specifications", {})
            log_info("Specifications", json.dumps(specs, default=str)[:100])

            # Query database for candidate OEM products
            log_step("Querying database for candidates...")
            candidates = query_oem_products_for_requirement(session, specs)
            log_info("Candidates found", len(candidates))

            # Score matches
            if candidates:
                log_step("Scoring matches with LLM...")
                log_llm_call("LLM", f"Score {len(candidates)} candidates")
                match_result = score_matches_with_llm(req, candidates)

                # Build match objects
                matches = []
                for scored in match_result.get("scored_matches", []):
                    # Find the product in candidates
                    comp = next(
                        (c for c in candidates if c["product_id"] == scored["product_id"]),
                        None
                    )
                    if comp:
                        matches.append({
                            "product_id": comp["product_id"],
                            "sku": comp["sku"],
                            "name": comp["name"],
                            "category": comp["category"],
                            "manufacturer": comp["manufacturer"],
                            "score": scored["score"],
                            "matched_specs": scored["matched_specs"],
                            "price_per_meter": comp["price_per_meter"],
                            "in_stock": comp["in_stock"],
                            "lead_time_days": comp["lead_time_days"]
                        })

                best_match = matches[0] if matches else None
                coverage = match_result.get("coverage_score", 0)

                if best_match:
                    log_success(f"Best match: {best_match['name']} (Score: {best_match['score']})")
                else:
                    log_warning("No suitable match found")

                requirement_matches.append({
                    "requirement_id": req["id"],
                    "requirement_description": req["description"],
                    "matches": matches,
                    "best_match": best_match,
                    "coverage_score": coverage
                })
            else:
                log_warning("No candidates in database")
                requirement_matches.append({
                    "requirement_id": req["id"],
                    "requirement_description": req["description"],
                    "matches": [],
                    "best_match": None,
                    "coverage_score": 0
                })

    except Exception as e:
        log_error(f"Error: {str(e)}")
        errors.append(f"Matcher Agent: {str(e)}")
    finally:
        session.close()

    # Summary
    log_section_divider("Matching Summary")
    matched_count = sum(1 for rm in requirement_matches if rm.get("best_match"))
    log_success(f"Matched {matched_count}/{len(requirements)} requirements")

    if requirement_matches:
        log_summary_table(
            ["Req ID", "Best Match", "Score", "Price/m"],
            [
                [
                    rm["requirement_id"],
                    rm["best_match"]["name"][:25] if rm.get("best_match") else "No match",
                    rm["best_match"]["score"] if rm.get("best_match") else 0,
                    f"₹{rm['best_match']['price_per_meter']:.2f}" if rm.get("best_match") else "-"
                ]
                for rm in requirement_matches
            ]
        )

    log_agent_end("Matcher", success=len(errors) == 0)

    return {
        "requirement_matches": requirement_matches,
        "current_agent": "matcher",
        "errors": errors
    }
