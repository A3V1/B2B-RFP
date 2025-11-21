from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.v1 import routes
from app.config import settings
from app.db.base import init_db, get_engine

app = FastAPI(title="RFP Automation MVP")

app.include_router(routes.router, prefix="/api/v1")

# Mount static files directory
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
def startup():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    init_db()

@app.get("/")
def home():
    """Serve the HTML upload interface"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "dashboard.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"status": "ok", "message": "API is running. Visit /docs for API documentation."}
