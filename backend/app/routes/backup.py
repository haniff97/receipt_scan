"""Backup and restore for receipts + transactions + images.

Backup = a zip containing the SQLite DB and the uploads/ folder.
Restore = replace the current DB and uploads from a zip.
"""

import io
import os
import shutil
import zipfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from ..database import IS_SQLITE, engine, get_db, SessionLocal

router = APIRouter()

UPLOAD_DIR = os.environ.get(
    "UPLOAD_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"),
)


def _db_path():
    """The on-disk path of the SQLite DB (backup is SQLite-only)."""
    return engine.url.database or "receipts.db"


@router.get("/backup")
def backup():
    """Download a zip of the database + uploaded receipt images."""
    if not IS_SQLITE:
        raise HTTPException(status_code=400, detail="Backup is only available with the SQLite database.")
    db_path = _db_path()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, arcname="receipts.db")
        if os.path.isdir(UPLOAD_DIR):
            for root, _dirs, files in os.walk(UPLOAD_DIR):
                for f in files:
                    full = os.path.join(root, f)
                    zf.write(full, arcname=os.path.join("uploads", f))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=receipt_tracker_backup.zip"},
    )


@router.post("/backup/restore")
def restore(file: UploadFile = File(...)):
    """Replace the current DB + uploads from an uploaded backup zip."""
    if not IS_SQLITE:
        raise HTTPException(status_code=400, detail="Restore is only available with the SQLite database.")
    db_path = _db_path()
    data = file.file.read()
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            db_in_zip = zf.read("receipts.db") if "receipts.db" in names else None
            if db_in_zip is None:
                raise HTTPException(status_code=400, detail="Backup does not contain receipts.db")

            # Replace the database
            if os.path.exists(db_path):
                os.remove(db_path)
            with open(db_path, "wb") as f:
                f.write(db_in_zip)

            # Replace uploads
            if os.path.isdir(UPLOAD_DIR):
                shutil.rmtree(UPLOAD_DIR)
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            for name in names:
                if name.startswith("uploads/") and not name.endswith("/"):
                    target = os.path.join(UPLOAD_DIR, os.path.basename(name))
                    with open(target, "wb") as f:
                        f.write(zf.read(name))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid backup: {e}")

    return {"restored": True, "restart_required": True}
