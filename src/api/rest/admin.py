from fastapi import APIRouter, HTTPException, status, Depends
from cuid2 import Cuid

from typings import Permission
from store import Store

from typings import Role
from models import User
from api.helpers import (
    generate_magic_token,
    get_current_user,
)

CUID_GENERATOR: Cuid = Cuid(length=7)

router = APIRouter(prefix="/admin", tags=["admin"])
store = Store()


@router.post("/generateMagicLink", tags=["admin"])
async def generate_magic_link(
    role: str, display_name: str, current_user: dict = Depends(get_current_user)
):
    if not store.check_permission(current_user["id"], Permission.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing permission: Admin",
        )

    # fetch role
    try:
        userRole = Role(role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect Role selected",
        )

    magic_token = generate_magic_token()

    user = User(
        id=CUID_GENERATOR.generate(),
        display_name=display_name,
        magic_token=magic_token,
        is_online=False,
        role=userRole,
    )

    store.add_user(user)
    
    magic_link = f"http://localhost:5173/auth?magic_token={magic_token}"

    return {"magic_link": magic_link}
