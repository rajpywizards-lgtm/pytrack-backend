"""
main.py
----------
FastAPI entry point for PyTrack backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.supabase_client import supabase
from app.routes import user, task, screenshot

app = FastAPI(
    title="PyTrack Backend",
    description="FastAPI + Supabase backend for PyTrack",
    version="1.0.0",
)

# CORS (kept wide-open; fine for desktop/native client)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(user.router)
app.include_router(task.router)
app.include_router(screenshot.router)

@app.get("/")
def root():
    """Test root endpoint."""
    return {"message": "✅ PyTrack backend is running!", "supabase_connected": bool(supabase)}

@app.get("/health")
def health():
    return {"ok": True}
