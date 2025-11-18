from fastapi import FastAPI
import os

from app.api.v1 import routes
from app.config import settings
from app.db.base import init_db, get_engine

app = FastAPI(title="RFP Automation MVP")

app.include_router(routes.router, prefix="/api/v1")

@app.on_event("startup")
def startup():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    init_db()

@app.get("/")
def health():
    return {"status": "ok"}
