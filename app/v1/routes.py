from fastapi import APIRouter, UploadFile, File, HTTPException
import uuid
import os
from app.config import settings
from app.services.extractor import extract_text_from_file
from app.db import crud

router = APIRouter()

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
