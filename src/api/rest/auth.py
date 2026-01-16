from fastapi import APIRouter, HTTPException, status, Depends
from cuid2 import Cuid
from datetime import timedelta


from typings import Permission
from store import Store

from typings import Role
from models import User
from api.helpers import (
    generate_magic_token,
    create_access_token,
    TokenResponse,
    get_current_user,
)

ACCESS_TOKEN_EXPIRE_MINUTES = 30
CUID_GENERATOR: Cuid = Cuid(length=7)

router = APIRouter(tags=["auth"])
store = Store()


@router.post("/login", tags=["auth"], response_model=TokenResponse)
async def login(magic_token: str):
    if magic_token is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # explore User dict
    for id, user in store.get_all_users().items():
        if user.magic_token == magic_token:
            access_token = create_access_token(
                data={"sub": user.id},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            )

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {"id": user.id, "role": user.role},
            }

    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/users/inviteNewUser", tags=["users"])
async def inviteNewUser(
    role: str, display_name: str, current_user: dict = Depends(get_current_user)
):
    print(current_user)

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

    return {"magic_token": magic_token}


@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
