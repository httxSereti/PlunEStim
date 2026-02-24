import jwt
import os
import dotenv

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional

from store import Store

dotenv.load_dotenv("config.env")

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

security = HTTPBearer()
store = Store()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        userId: str = payload.get("sub")

        if userId is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = store.get_user(userId)

        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return {
            "id": userId,
            "role": user.role,
            "permissions": user.custom_permissions,
            "display_name": user.display_name,
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except (jwt.PyJWTError, jwt.exceptions.InvalidSignatureError):
        raise HTTPException(status_code=401, detail="Invalid token")
