from fastapi import APIRouter, HTTPException, Depends
from cuid2 import Cuid
from datetime import timedelta

from store import Store
from api.helpers import (
    create_access_token,
    TokenResponse,
    get_current_user,
)

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
CUID_GENERATOR: Cuid = Cuid(length=7)

router = APIRouter(prefix="/auth", tags=["auth"])
store = Store()


@router.post("/login", response_model=TokenResponse)
async def login(magic_token: str):
    if magic_token is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # explore User dict
    for id, user in store.get_all_users().items():
        if user.magic_token == magic_token:
            access_token = create_access_token(
                data={"sub": user.id, "role": user.role.value},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            )

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {"id": user.id, "role": user.role},
            }

    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
