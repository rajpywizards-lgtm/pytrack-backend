"""
user.py
----------
All user-related routes: registration, login, profile.
"""

from fastapi import APIRouter
from app.utils.auth import list_users

router = APIRouter(prefix="/user", tags=["User"])

@router.get("/list")
def get_users():
    """
    Fetches all Supabase users (for testing).
    Requires service role key in .env.
    """
    users = list_users()
    return {
        "user_count": len(users),
        "users": [user.email for user in users]
    }
