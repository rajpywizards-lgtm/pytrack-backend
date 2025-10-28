# app/routes/task.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from app.utils.auth import get_current_user, User
from app.supabase_client import supabase_admin

router = APIRouter(prefix="/task", tags=["Task"])


class AssignBody(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = None
    estimated_minutes: int = Field(ge=1)
    assigned_to: str  # user id (UUID string)


@router.post("/assign")
def assign_task(
    body: AssignBody,
    user: User = Depends(get_current_user),
):
    """
    Assign a task to a user. Only superusers can do this.
    """
    role_q = (
        supabase_admin.table("users")
        .select("role")
        .eq("id", str(user.id))
        .limit(1)
        .execute()
    )
    if not role_q.data or role_q.data[0].get("role") != "superuser":
        raise HTTPException(status_code=403, detail="Only superusers can assign tasks.")

    resp = (
        supabase_admin.table("tasks")
        .insert(
            {
                "assigned_by": str(user.id),
                "assigned_to": body.assigned_to,
                "title": body.title,
                "description": body.description,
                "estimated_minutes": body.estimated_minutes,
                # optional defaults handled by DB (status/created_at, etc.)
            }
        )
        .execute()
    )

    if not resp.data:
        raise HTTPException(status_code=400, detail="Task creation failed.")
    return {"status": "success", "task": resp.data[0]}


@router.get("/my-tasks")
def get_my_tasks(user: User = Depends(get_current_user)):
    """
    Fetch all tasks assigned to the current user.
    """
    resp = (
        supabase_admin.table("tasks")
        .select("*")
        .eq("assigned_to", str(user.id))
        .execute()
    )
    tasks = resp.data or []
    return {"status": "success", "count": len(tasks), "tasks": tasks}


class StatusBody(BaseModel):
    task_id: str
    new_status: str = Field(pattern="^(in_progress|completed)$")


@router.post("/update-status")
def update_task_status(
    body: StatusBody,
    user: User = Depends(get_current_user),
):
    """
    Update status of a task (in_progress | completed).
    Only allowed if the task belongs to the current user.
    """
    # Verify ownership
    verify = (
        supabase_admin.table("tasks")
        .select("assigned_to, status")
        .eq("id", body.task_id)
        .limit(1)
        .execute()
    )
    if not verify.data:
        raise HTTPException(status_code=404, detail="Task not found.")
    if verify.data[0]["assigned_to"] != str(user.id):
        raise HTTPException(status_code=403, detail="You can only update your own tasks.")

    update_payload = {"status": body.new_status}
    if body.new_status == "completed":
        update_payload["completed_at"] = datetime.now(timezone.utc).isoformat()

    result = (
        supabase_admin.table("tasks")
        .update(update_payload)
        .eq("id", body.task_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=400, detail="Task update failed.")
    return {"status": "success", "task": result.data[0]}
