"""File upload endpoints."""
from __future__ import annotations
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()

UPLOAD_DIR = Path(tempfile.gettempdir()) / "pavement_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
