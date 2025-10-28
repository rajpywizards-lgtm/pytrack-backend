"""
auth.py
----------
Handles Supabase Auth: signup, login, user listing + server-verified current user.
"""

from dataclasses import dataclass
from typing import Optional

from app.supabase_client import supabase, supabase_admin
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# -------------------------
# Public user object for routes
# -------------------------
@dataclass
class User:
    id: str
    email: Optional[str] = None

# -------------------------
# (Optional) Lightweight, unverified claim reader
# Keep for debugging / non-critical flows only.
# -------------------------
def verify_supabase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Reads JWT claims without verifying signature.
    Prefer `get_current_user` for real auth in routes.
    """
    token = credentials.credentials
    try:
        payload = jwt.get_unverified_claims(token)
        user_id = payload.get("sub")   # Supabase uses 'sub' for user id
        email = payload.get("email")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Supabase token.",
            )
        return {"user_id": user_id, "email": email}
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )

# -------------------------
# Strong verification via Supabase (recommended)
# -------------------------
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Validates the Bearer token with Supabase (server-side) and returns a User object.
    Uses the SERVICE ROLE client to ensure signature & expiry are checked by Supabase.
    """
    token = credentials.credentials
    try:
        resp = supabase_admin.auth.get_user(token)
        if not getattr(resp, "user", None):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
            )
        u = resp.user
        return User(id=u.id, email=getattr(u, "email", None))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )

# -------------------------
# User management helpers
# -------------------------
def register_user(email: str, password: str, role: str = "employee"):
    """
    Register a new user (employee or superuser) via Supabase Auth.
    """
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            create_user_metadata(response.user.id, response.user.email, role)
            return {"status": "success", "email": response.user.email, "role": role}
        else:
            return {"status": "error", "message": str(response)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def create_user_metadata(user_id: str, email: str, role: str = "employee"):
    """Insert into users table to store role metadata."""
    try:
        supabase_admin.table("users").insert({
            "id": user_id,
            "full_name": email.split("@")[0].title(),
            "role": role,
            "email": email,
        }).execute()
        print(f"✅ Metadata created for {email} ({role})")
    except Exception as e:
        print("⚠️ Metadata creation failed:", e)

def register_superuser(email: str, password: str):
    """Registers a superuser directly."""
    return register_user(email, password, role="superuser")

def login_user(email: str, password: str):
    """
    Log in existing user with Supabase Auth.
    Returns access and refresh tokens if successful.
    """
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.session:
            return {
                "status": "success",
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user_email": response.user.email
            }
        else:
            return {"status": "error", "message": "Invalid login or no session returned."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def list_users():
    """Admin-only: list all users (requires SERVICE_ROLE)."""
    try:
        response = supabase.auth.admin.list_users()
        return response
    except Exception:
        return []
