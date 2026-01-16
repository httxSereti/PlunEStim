from fastapi import APIRouter
from store import Store

router = APIRouter(tags=["users"])
store = Store()

@router.get("/users", tags=["users"])
async def read_users():
    return store.get_all_users()

@router.get("/users/{user_id}", tags=["users"])
async def read_user(user_id: str):
    return store.get_user(user_id)