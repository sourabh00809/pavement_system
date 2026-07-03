"""File upload endpoints."""
from __future__ import annotations
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

router = APIRouter()

UPLOAD_DIR = Path(tempfile.gettempdir()) / "pavement_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class UploadPathsRequest(BaseModel):
    files: list[dict] = []  # [{"path": "...", "type": "VER"}, ...]


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file provided")
    ext = Path(file.filename).suffix.lower()
    if ext not in (".xls", ".xlsx", ".csv"):
        raise HTTPException(400, f"Unsupported file type: {ext}. Use .xls, .xlsx, or .csv")
    dest = UPLOAD_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)
    return {"filename": file.filename, "size": len(content), "path": str(dest)}


@router.post("/upload/paths")
async def save_upload_paths(req: UploadPathsRequest):
    from src.api.routes_visualization import set_uploaded_files
    set_uploaded_files(req.files)
    return {"status": "ok", "n_files": len(req.files)}


@router.get("/upload/paths")
async def get_upload_paths():
    from src.api.routes_visualization import get_upload_status
    return get_upload_status()
