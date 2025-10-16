"""
main.py
----------
FastAPI entry point for PyTrack backend.
"""

from fastapi import FastAPI
from app.supabase_client import supabase
from app.routes import user, task

app = FastAPI(
    title="PyTrack Backend",
    description="FastAPI + Supabase starter backend for PyTrack system",
    version="1.0.0"
)

# Include routers
app.include_router(user.router)
app.include_router(task.router)

@app.get("/")
def root():
    """Test root endpoint."""
    return {"message": "✅ PyTrack backend is running!", "supabase_connected": bool(supabase)}
