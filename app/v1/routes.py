from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import os
from app.config import settings
from app.services.extractor import extract_text_from_file
from app.db import crud

router = APIRouter()

# Store analysis results (in production, use Redis or database)
analysis_results: Dict[str, Any] = {}
analysis_status: Dict[str, str] = {}


@router.post("/upload")
async def upload_rfp(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    rfp_id = str(uuid.uuid4())
    safe_name = f"{rfp_id}{ext}"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(settings.UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(await file.read())
    crud.create_rfp_record(rfp_id, safe_name, path)
    return {"rfp_id": rfp_id, "filename": safe_name}


@router.post("/extract")
def extract(rfp_id: str):
    rec = crud.get_rfp_by_id(rfp_id)
    if not rec:
        raise HTTPException(status_code=404, detail="RFP not found")
    try:
        text = extract_text_from_file(rec.filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")
    crud.update_rfp_text(rfp_id, text)
    return {"rfp_id": rfp_id, "text": text}


def run_analysis_background(rfp_id: str, rfp_text: str):
    """Background task to run RFP analysis."""
    from app.agents import run_rfp_analysis
    import asyncio

    try:
        analysis_status[rfp_id] = "processing"
        result = asyncio.run(run_rfp_analysis(rfp_id, rfp_text))
        analysis_results[rfp_id] = result
        analysis_status[rfp_id] = "completed"
    except Exception as e:
        analysis_status[rfp_id] = "failed"
        analysis_results[rfp_id] = {"error": str(e)}


@router.post("/analyze")
async def analyze_rfp(rfp_id: str, background_tasks: BackgroundTasks):
    """
    Start AI-powered RFP analysis using LangGraph agents.

    This runs asynchronously in the background. Use /analyze/status to check progress.
    """
    rec = crud.get_rfp_by_id(rfp_id)
    if not rec:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not rec.text:
        raise HTTPException(
            status_code=400,
            detail="RFP text not extracted. Call /extract first."
        )

    # Check if already processing
    if analysis_status.get(rfp_id) == "processing":
        return {
            "rfp_id": rfp_id,
            "status": "processing",
            "message": "Analysis already in progress"
        }

    # Start background analysis
    background_tasks.add_task(run_analysis_background, rfp_id, rec.text)
    analysis_status[rfp_id] = "queued"

    return {
        "rfp_id": rfp_id,
        "status": "queued",
        "message": "Analysis started. Use /analyze/status to check progress."
    }


@router.get("/analyze/status")
def get_analysis_status(rfp_id: str):
    """Check the status of an RFP analysis."""
    status = analysis_status.get(rfp_id, "not_found")

    if status == "not_found":
        raise HTTPException(status_code=404, detail="No analysis found for this RFP")

    return {
        "rfp_id": rfp_id,
        "status": status
    }


@router.get("/analyze/result")
def get_analysis_result(rfp_id: str):
    """Get the full analysis results for an RFP."""
    if rfp_id not in analysis_results:
        status = analysis_status.get(rfp_id, "not_found")
        if status == "not_found":
            raise HTTPException(status_code=404, detail="No analysis found for this RFP")
        elif status == "processing" or status == "queued":
            raise HTTPException(status_code=202, detail=f"Analysis still {status}")
        else:
            raise HTTPException(status_code=500, detail="Analysis failed")

    return analysis_results[rfp_id]


@router.post("/analyze/sync")
def analyze_rfp_sync(rfp_id: str):
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

    if not rec.text:
        raise HTTPException(
            status_code=400,
            detail="RFP text not extracted. Call /extract first."
        )

    try:
        result = asyncio.run(run_rfp_analysis(rfp_id, rec.text))
        analysis_results[rfp_id] = result
        analysis_status[rfp_id] = "completed"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
