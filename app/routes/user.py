# app/routes/user.py
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Any

from app.utils.auth import (
    list_users,
    register_user,
    login_user,
    register_superuser,
    get_current_user,
    User,
)
from app.supabase_client import supabase_admin

router = APIRouter(prefix="/user", tags=["User"])


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(request: AuthRequest):
    res = register_user(request.email, request.password)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res


@router.post("/login")
def login(request: AuthRequest):
    res = login_user(request.email, request.password)
    if res.get("status") == "error":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=res.get("message"))
    return res


@router.get("/me")
def get_my_profile(user: User = Depends(get_current_user)):
    return {"status": "success", "user": {"id": user.id, "email": user.email}}


@router.get("/list")
def get_users() -> dict[str, Any]:
    """
    List all users (admin-only would be ideal; leaving open if your RLS allows).
    """
    resp = list_users()
    # Try to normalize common shapes
    users_list = []
    # If SDK returns an object with .users
    if hasattr(resp, "users"):
        users_list = [u.email for u in getattr(resp, "users", []) if getattr(u, "email", None)]
    # If helper already returned a list of dicts or objects
    elif isinstance(resp, (list, tuple)):
        for u in resp:
            email = getattr(u, "email", None) if not isinstance(u, dict) else u.get("email")
            if email:
                users_list.append(email)

    return {"user_count": len(users_list), "users": users_list}


@router.post("/create-superuser")
def create_superuser(
    request: AuthRequest,
    user: User = Depends(get_current_user),
):
    role_check = (
        supabase_admin.table("users").select("role").eq("id", str(user.id)).limit(1).execute()
    )
    if not role_check.data or role_check.data[0].get("role") != "superuser":
        raise HTTPException(status_code=403, detail="Only superusers can create other superusers.")

    res = register_superuser(request.email, request.password)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res
