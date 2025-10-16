from fastapi import APIRouter, Depends, HTTPException, status
from app.utils.auth import verify_supabase_token
from app.supabase_client import supabase, supabase_admin

router = APIRouter(prefix="/task", tags=["Task"])

# -------------------- ASSIGN TASK (Superuser Only) --------------------
@router.post("/assign")
def assign_task(
    title: str,
    description: str,
    estimated_minutes: int,
    assigned_to: str,
    user_data: dict = Depends(verify_supabase_token)
):
    """
    Assign a task to a user. Only superusers can perform this action.
    """
    current_user_id = user_data.get("user_id")
    current_user_role = supabase.table("users").select("role").eq("id", current_user_id).execute()
    if not current_user_role.data or current_user_role.data[0]["role"] != "superuser":
        raise HTTPException(status_code=403, detail="Only superusers can assign tasks.")

    response = supabase_admin.table("tasks").insert({
        "assigned_by": current_user_id,
        "assigned_to": assigned_to,
        "title": title,
        "description": description,
        "estimated_minutes": estimated_minutes
    }).execute()

    if response.data:
        return {"status": "success", "task": response.data[0]}
    else:
        raise HTTPException(status_code=400, detail="Task creation failed.")


# -------------------- FETCH MY TASKS (Employee) --------------------
@router.get("/my-tasks")
def get_my_tasks(user_data: dict = Depends(verify_supabase_token)):
    """
    Fetch all tasks assigned to the currently logged-in user.
    """
    current_user_id = user_data.get("user_id")

    response = supabase_admin.table("tasks") \
        .select("*") \
        .eq("assigned_to", current_user_id) \
        .execute()

    if response.data is None:
        raise HTTPException(status_code=404, detail="No tasks found.")
    return {"status": "success", "count": len(response.data), "tasks": response.data}


# -------------------- UPDATE TASK STATUS (Employee) --------------------
@router.post("/update-status")
def update_task_status(
    task_id: str,
    new_status: str,
    user_data: dict = Depends(verify_supabase_token)
):
    """
    Update status of a task (in_progress / completed).
    Only allowed if the task belongs to the current user.
    """
    current_user_id = user_data.get("user_id")

    # Verify the task belongs to this user
    verify_task = supabase.table("tasks").select("assigned_to, status").eq("id", task_id).execute()
    if not verify_task.data:
        raise HTTPException(status_code=404, detail="Task not found.")
    if verify_task.data[0]["assigned_to"] != current_user_id:
        raise HTTPException(status_code=403, detail="You can only update your own tasks.")

    if new_status not in ["in_progress", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status value.")

    update_payload = {"status": new_status}
    if new_status == "completed":
        from datetime import datetime
        update_payload["completed_at"] = datetime.utcnow().isoformat()

    result = supabase_admin.table("tasks").update(update_payload).eq("id", task_id).execute()

    if result.data:
        return {"status": "success", "task": result.data[0]}
    else:
        raise HTTPException(status_code=400, detail="Task update failed.")
