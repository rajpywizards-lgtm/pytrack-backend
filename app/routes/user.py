from fastapi import APIRouter, HTTPException, Depends
from app.supabase_client import supabase
from app.utils.auth import list_users, register_user, login_user, verify_supabase_token, register_superuser

router = APIRouter(prefix="/user", tags=["User"])

@router.post("/register")
def register(email: str, password: str):
    """
    Create a new user via Supabase Auth.
    """
    result = register_user(email, password)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@router.post("/login")
def login(email: str, password: str):
    """
    Log in an existing user.
    Returns access and refresh tokens.
    """
    result = login_user(email, password)
    if result.get("status") == "error":
        raise HTTPException(status_code=401, detail=result.get("message"))
    return result

@router.get("/me")
def get_my_profile(user_data: dict = Depends(verify_supabase_token)):
    """
    Returns info of the currently authenticated user.
    Requires: Authorization: Bearer <access_token>
    """
    return {"status": "success", "user": user_data}
@router.get("/list")
def get_users():
    """
    List all users (admin only).
    """
    users = list_users()
    if not users:
        return {"user_count": 0, "users": []}
    return {
        "user_count": len(users),
        "users": [u.email for u in users]
    }

@router.post("/create-superuser")
def create_superuser(
    email: str,
    password: str,
    user_data: dict = Depends(verify_supabase_token)
):
    """
    Creates a new superuser (employer).
    Only existing superusers can perform this.
    """
    current_user_id = user_data.get("user_id")
    role_check = supabase.table("users").select("role").eq("id", current_user_id).execute()

    if not role_check.data or role_check.data[0]["role"] != "superuser":
        raise HTTPException(status_code=403, detail="Only superusers can create other superusers.")

    result = register_superuser(email, password)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result