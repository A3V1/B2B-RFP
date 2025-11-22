from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import os
from app.config import settings
from app.services.extractor import extract_text_from_file
from app.db import crud
from app.db.models import RFP

router = APIRouter()

# Store analysis results (in production, use Redis or database)
analysis_results: Dict[str, Any] = {}
analysis_status: Dict[str, str] = {}


@router.post("/upload")
async def upload_rfp(file: UploadFile = File(...)):
    """Upload an RFP document (PDF or DOCX)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Generate unique RFP number
    rfp_number = f"RFP-{uuid.uuid4().hex[:8].upper()}"
    safe_name = f"{rfp_number}{ext}"

    # Save file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(settings.UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(await file.read())

    # Create RFP record with new schema
    rfp = crud.create_rfp(
        rfp_number=rfp_number,
        title=file.filename,
        document_path=path
    )

    return {
        "rfp_id": rfp.id,
        "rfp_number": rfp.rfp_number,
        "filename": safe_name
    }


@router.post("/extract")
def extract(rfp_id: int):
    """Extract text from uploaded RFP document."""
    rec = crud.get_rfp_by_id(rfp_id)
    if not rec:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not rec.document_path:
        raise HTTPException(status_code=400, detail="No document associated with this RFP")

    try:
        text = extract_text_from_file(rec.document_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    crud.update_rfp_extracted_text(rfp_id, text)

    return {"rfp_id": rfp_id, "text": text}


def run_analysis_background(rfp_id: int, rfp_text: str):
    """Background task to run RFP analysis."""
    from app.agents import run_rfp_analysis
    import asyncio

    try:
        analysis_status[str(rfp_id)] = "processing"
        result = asyncio.run(run_rfp_analysis(str(rfp_id), rfp_text))
        analysis_results[str(rfp_id)] = result
        analysis_status[str(rfp_id)] = "completed"

        # Update RFP status in database
        crud.update_rfp_status(rfp_id, "completed")

    except Exception as e:
        analysis_status[str(rfp_id)] = "failed"
        analysis_results[str(rfp_id)] = {"error": str(e)}


@router.post("/analyze")
async def analyze_rfp(rfp_id: int, background_tasks: BackgroundTasks):
    """
    Start AI-powered RFP analysis using LangGraph agents.

    This runs asynchronously in the background. Use /analyze/status to check progress.
    """
    rec = crud.get_rfp_by_id(rfp_id)
    if not rec:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not rec.extracted_text:
        raise HTTPException(
            status_code=400,
            detail="RFP text not extracted. Call /extract first."
        )

    # Check if already processing
    if analysis_status.get(str(rfp_id)) == "processing":
        return {
            "rfp_id": rfp_id,
            "status": "processing",
            "message": "Analysis already in progress"
        }

    # Update RFP status
    crud.update_rfp_status(rfp_id, "processing")

    # Start background analysis
    background_tasks.add_task(run_analysis_background, rfp_id, rec.extracted_text)
    analysis_status[str(rfp_id)] = "queued"

    return {
        "rfp_id": rfp_id,
        "status": "queued",
        "message": "Analysis started. Use /analyze/status to check progress."
    }


@router.get("/analyze/status")
def get_analysis_status(rfp_id: int):
    """Check the status of an RFP analysis."""
    status = analysis_status.get(str(rfp_id), "not_found")

    if status == "not_found":
        # Check database for status
        rec = crud.get_rfp_by_id(rfp_id)
        if rec:
            return {"rfp_id": rfp_id, "status": rec.status}
        raise HTTPException(status_code=404, detail="No analysis found for this RFP")

    return {
        "rfp_id": rfp_id,
        "status": status
    }


@router.get("/analyze/result")
def get_analysis_result(rfp_id: int):
    """Get the full analysis results for an RFP."""
    if str(rfp_id) not in analysis_results:
        status = analysis_status.get(str(rfp_id), "not_found")
        if status == "not_found":
            raise HTTPException(status_code=404, detail="No analysis found for this RFP")
        elif status == "processing" or status == "queued":
            raise HTTPException(status_code=202, detail=f"Analysis still {status}")
        else:
            raise HTTPException(status_code=500, detail="Analysis failed")

    return analysis_results[str(rfp_id)]


@router.post("/analyze/sync")
def analyze_rfp_sync(rfp_id: int):
    """
    Run RFP analysis synchronously (blocking).

    Use this for testing or when you need immediate results.
    For production, prefer /analyze (async).
    """
    from app.agents import run_rfp_analysis
    import asyncio

    rec = crud.get_rfp_by_id(rfp_id)
    if not rec:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not rec.extracted_text:
        raise HTTPException(
            status_code=400,
            detail="RFP text not extracted. Call /extract first."
        )

    try:
        # Update status
        crud.update_rfp_status(rfp_id, "processing")

        result = asyncio.run(run_rfp_analysis(str(rfp_id), rec.extracted_text))
        analysis_results[str(rfp_id)] = result
        analysis_status[str(rfp_id)] = "completed"

        # Update status
        crud.update_rfp_status(rfp_id, "completed")

        return result
    except Exception as e:
        crud.update_rfp_status(rfp_id, "failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze/debug")
def analyze_rfp_debug(rfp_id: int):
    """
    Run RFP analysis with detailed debug output for each agent.

    Returns intermediate state after each agent runs, allowing you to:
    - See exactly what each agent produces
    - Identify which agent is failing
    - Inspect the data flowing between agents
    - Measure performance of each stage
    """
    from app.agents.state import RFPState
    from app.agents.parser_agent import parser_agent
    from app.agents.analyzer_agent import analyzer_agent
    from app.agents.matcher_agent import matcher_agent
    from app.agents.scorer_agent import scorer_agent
    from app.agents.response_agent import response_agent
    import time

    rec = crud.get_rfp_by_id(rfp_id)
    if not rec:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not rec.extracted_text:
        raise HTTPException(
            status_code=400,
            detail="RFP text not extracted. Call /extract first."
        )

    # Initialize state
    state: RFPState = {
        "rfp_id": str(rfp_id),
        "rfp_text": rec.extracted_text,
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

    debug_output = {
        "rfp_id": rfp_id,
        "input_text_length": len(rec.extracted_text),
        "input_text_preview": rec.extracted_text[:500] + "..." if len(rec.extracted_text) > 500 else rec.extracted_text,
        "stages": {}
    }

    agents = [
        ("parser", parser_agent),
        ("analyzer", analyzer_agent),
        ("matcher", matcher_agent),
        ("scorer", scorer_agent),
        ("response", response_agent)
    ]

    for agent_name, agent_func in agents:
        start_time = time.time()
        try:
            # Run agent
            result = agent_func(state)
            duration_ms = int((time.time() - start_time) * 1000)

            # Merge result into state
            state.update(result)

            # Capture debug info for this stage
            debug_output["stages"][agent_name] = {
                "status": "success",
                "duration_ms": duration_ms,
                "output": _sanitize_debug_output(agent_name, result),
                "errors": result.get("errors", [])
            }

            # Check if we should stop (based on conditional routing logic)
            if agent_name == "parser" and not state.get("sections"):
                debug_output["stages"][agent_name]["note"] = "No sections found - pipeline would stop here"
                break
            if agent_name == "analyzer" and not state.get("requirements"):
                debug_output["stages"][agent_name]["note"] = "No requirements found - matcher will be skipped"

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            debug_output["stages"][agent_name] = {
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(e),
                "error_type": type(e).__name__
            }
            break

    # Add summary
    debug_output["summary"] = {
        "total_stages_run": len(debug_output["stages"]),
        "successful_stages": sum(1 for s in debug_output["stages"].values() if s["status"] == "success"),
        "sections_found": len(state.get("sections", [])),
        "requirements_extracted": len(state.get("requirements", [])),
        "requirements_matched": len([rm for rm in state.get("requirement_matches", []) if rm.get("best_match")]),
        "overall_score": state.get("overall_score", 0),
        "all_errors": state.get("errors", [])
    }

    return debug_output


def _sanitize_debug_output(agent_name: str, result: dict) -> dict:
    """Sanitize and summarize agent output for debug display."""
    output = {}

    if agent_name == "parser":
        sections = result.get("sections", [])
        output["sections_count"] = len(sections)
        output["sections"] = [
            {
                "name": s.get("name"),
                "content_length": len(s.get("content", "")),
                "content_preview": s.get("content", "")[:200] + "..." if len(s.get("content", "")) > 200 else s.get("content", ""),
                "page_number": s.get("page_number")
            }
            for s in sections
        ]

    elif agent_name == "analyzer":
        requirements = result.get("requirements", [])
        output["requirements_count"] = len(requirements)
        output["requirements"] = [
            {
                "id": r.get("id"),
                "description": r.get("description"),
                "category": r.get("category"),
                "priority": r.get("priority"),
                "specifications": r.get("specifications", {})
            }
            for r in requirements
        ]
        output["project_summary"] = result.get("project_summary", "")
        output["budget_info"] = result.get("budget_info")
        output["timeline_info"] = result.get("timeline_info")

    elif agent_name == "matcher":
        matches = result.get("requirement_matches", [])
        output["matches_count"] = len(matches)
        output["requirement_matches"] = [
            {
                "requirement_id": m.get("requirement_id"),
                "requirement_description": m.get("requirement_description", "")[:100],
                "matches_found": len(m.get("matches", [])),
                "best_match": {
                    "sku": m.get("best_match", {}).get("sku"),
                    "name": m.get("best_match", {}).get("name"),
                    "score": m.get("best_match", {}).get("score"),
                    "price_per_meter": m.get("best_match", {}).get("price_per_meter"),
                    "in_stock": m.get("best_match", {}).get("in_stock")
                } if m.get("best_match") else None,
                "coverage_score": m.get("coverage_score")
            }
            for m in matches
        ]

    elif agent_name == "scorer":
        output["overall_score"] = result.get("overall_score", 0)
        output["scoring_breakdown"] = result.get("scoring_breakdown", {})
        output["recommendations"] = result.get("recommendations", [])

    elif agent_name == "response":
        output["proposal_summary_length"] = len(result.get("proposal_summary", ""))
        output["proposal_summary_preview"] = result.get("proposal_summary", "")[:300] + "..." if len(result.get("proposal_summary", "")) > 300 else result.get("proposal_summary", "")
        output["technical_response_length"] = len(result.get("technical_response", ""))
        output["commercial_response_length"] = len(result.get("commercial_response", ""))

    return output


# =============================================================================
# New API Endpoints for the Revised Schema
# =============================================================================

@router.get("/rfps")
def list_rfps():
    """List all RFPs."""
    rfps = crud.get_all_rfps()
    return [
        {
            "id": r.id,
            "rfp_number": r.rfp_number,
            "title": r.title,
            "status": r.status,
            "due_date": r.due_date,
            "created_at": r.created_at
        }
        for r in rfps
    ]


@router.get("/rfps/{rfp_id}")
def get_rfp(rfp_id: int):
    """Get RFP details with all related data."""
    data = crud.get_rfp_with_all_data(rfp_id)
    if not data:
        raise HTTPException(status_code=404, detail="RFP not found")
    return data


@router.delete("/rfps/{rfp_id}")
def delete_rfp(rfp_id: int):
    """Delete an RFP and all related data."""
    success = crud.delete_rfp(rfp_id)
    if not success:
        raise HTTPException(status_code=404, detail="RFP not found")
    return {"message": "RFP deleted successfully"}


@router.get("/oem-products")
def list_oem_products(category: Optional[str] = None, search: Optional[str] = None, in_stock_only: bool = False):
    """List OEM products with optional filtering."""
    if search:
        products = crud.search_oem_products(search)
    elif category:
        products = crud.get_oem_products_by_category(category)
    else:
        products = crud.get_all_oem_products()

    # Filter by stock availability if requested
    if in_stock_only:
        products = [p for p in products if p.in_stock]

    return [
        {
            "id": p.id,
            "sku": p.sku,
            "product_name": p.product_name,
            "product_category": p.product_category,
            "description": p.description,
            "manufacturer": p.manufacturer.name if p.manufacturer else None,
            "specifications": p.specifications,
            "keywords": p.keywords,
            "in_stock": p.in_stock,
            "lead_time_days": p.lead_time_days,
            "price": p.pricing.unit_price if p.pricing else None,
            "price_per_unit": p.pricing.price_per_unit if p.pricing else None,
            "price_per": p.pricing.price_per if p.pricing else None
        }
        for p in products
    ]


@router.get("/test-pricing")
def list_test_pricing():
    """List all test pricing entries."""
    tests = crud.get_all_test_pricing()
    return [
        {
            "id": t.id,
            "test_name": t.test_name,
            "test_category": t.test_category,
            "description": t.description,
            "price": t.price,
            "price_per": t.price_per,
            "standard_reference": t.standard_reference
        }
        for t in tests
    ]


@router.get("/manufacturers")
def list_manufacturers():
    """List all OEM manufacturers."""
    manufacturers = crud.get_all_manufacturers()
    return [
        {
            "id": m.id,
            "name": m.name,
            "website": m.website
        }
        for m in manufacturers
    ]
