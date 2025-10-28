# app/routes/screenshot.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, AnyHttpUrl
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
import os
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from app.utils.auth import get_current_user, User
from app.supabase_client import supabase_admin

router = APIRouter(prefix="/screenshots", tags=["Screenshots"])

# ----------------------- Helpers -----------------------

BUCKET = os.getenv("SCREEN_STORAGE_BUCKET", "screenshots")
# If your bucket is private, and you DON’T want public URLs, set this to "0" (or falsey)
SCREEN_STORAGE_PUBLIC = os.getenv("SCREEN_STORAGE_PUBLIC", "1")  # "1" = public

def _ensure_image(file_bytes: bytes) -> str:
    try:
        with Image.open(BytesIO(file_bytes)) as im:
            fmt = (im.format or "").upper()
    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail="File is not a recognized image.")
    if fmt == "PNG":
        return "png"
    if fmt == "JPEG":
        return "jpg"
    raise HTTPException(status_code=415, detail=f"Unsupported image type: {fmt or 'unknown'}")



def _public_or_signed_url(path: str) -> str:
    """
    Returns a public URL if the bucket is public.
    If private, you can switch to create_signed_url() here.
    """
    if SCREEN_STORAGE_PUBLIC and SCREEN_STORAGE_PUBLIC not in {"0", "false", "False"}:
        return supabase_admin.storage.from_(BUCKET).get_public_url(path)
    # Private bucket: create short-lived signed URL (adjust expiresIn seconds as needed)
    # NOTE: If signed URLs are not desired, you can store `path` only.
    signed = supabase_admin.storage.from_(BUCKET).create_signed_url(path, expires_in=3600)
    if isinstance(signed, dict) and signed.get("signedURL"):
        return signed["signedURL"]
    # fallback to path if API shape differs
    return path

# ----------------------- Models -----------------------

class ScreenshotIn(BaseModel):
    image_url: AnyHttpUrl
    captured_at: Optional[datetime] = Field(default=None, description="UTC timestamp")

# ----------------------- Endpoints -----------------------

@router.post("/upload")
async def upload_screenshot(
    image: UploadFile = File(...),
    captured_at: Optional[datetime] = None,
    user: User = Depends(get_current_user),
):
    """
    Accepts multipart/form-data:
      - image: file (png/jpg)
      - captured_at: optional ISO datetime
    Uploads to Storage (screenshots project), then inserts a row in the `screenshots` table.
    """
    try:
        raw = await image.read()
        ext = _ensure_image(raw)
        now = datetime.now(timezone.utc)
        captured = captured_at.astimezone(timezone.utc) if captured_at else now

        # Storage path: user_id/YYYY/MM/DD/uuid.ext
        path = f"{user.id}/{captured:%Y/%m/%d}/{uuid4().hex}.{ext}"

        # 1) Upload to Storage (no upsert)
        res = supabase_admin.storage.from_(BUCKET).upload(
            path,
            raw,
            {
                "content-type": image.content_type or f"image/{ext}",
                "x-upsert": "false",
            },
        )
        if isinstance(res, dict) and res.get("error"):
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {res['error']['message']}")

        # 2) Resolve URL (public or signed)
        url = _public_or_signed_url(path)

        # 3) Insert metadata row in screenshots table
        insert_data = {
            "user_id": str(user.id),
            "image_url": url,
            "captured_at": captured.isoformat(),
        }
        db_res = supabase_admin.table("screenshots").insert(insert_data).execute()
        if getattr(db_res, "error", None):
            # attempt cleanup if DB insert fails
            try:
                supabase_admin.storage.from_(BUCKET).remove([path])
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"DB insert failed: {db_res.error.message}")

        return {
            "status": "success",
            "image_url": url,
            "record": db_res.data[0] if getattr(db_res, "data", None) else insert_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record")
def record_screenshot(
    payload: ScreenshotIn,
    user: User = Depends(get_current_user),
):
    """
    Record metadata for an existing screenshot URL (no file content).
    Writes to the screenshots project `screenshots` table.
    """
    captured_at = payload.captured_at or datetime.now(timezone.utc)

    ins = (
        supabase_admin.table("screenshots")
        .insert(
            {
                "user_id": str(user.id),
                "image_url": str(payload.image_url),
                "captured_at": captured_at.isoformat(),
            }
        )
        .execute()
    )

    if getattr(ins, "error", None):
        raise HTTPException(status_code=400, detail=str(ins.error))

    row = ins.data[0] if getattr(ins, "data", None) else None
    return {"status": "success", "id": (row or {}).get("id")}
