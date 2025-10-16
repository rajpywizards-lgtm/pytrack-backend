"""
auth.py
----------
This utility module will later handle login, token verification, and
user validation logic. For now, it just connects to Supabase auth.
"""

from app.supabase_client import supabase

def list_users():
    """Test function to list all registered users from Supabase Auth."""
    response = supabase.auth.admin.list_users()
    return response
