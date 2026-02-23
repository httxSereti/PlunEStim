from fastapi import APIRouter, HTTPException, status, Depends
from typings import Permission
from store import Store

from api.helpers import (
    get_current_user,
)

router = APIRouter(tags=["users"])
store = Store()

@router.get("/users", tags=["users"])
async def read_users(current_user: dict = Depends(get_current_user)):
    if not store.check_permission(current_user["id"], Permission.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing permission: Admin",
        )

    return store.get_all_users()

@router.get("/users/{user_id}", tags=["users"])
async def read_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if not store.check_permission(current_user["id"], Permission.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing permission: Admin",
        )

    return store.get_user(user_id)