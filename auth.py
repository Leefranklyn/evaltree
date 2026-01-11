import hashlib
from typing import Optional
import bcrypt
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer
from models import User
from mongoengine.errors import DoesNotExist
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = str(os.getenv("SECRET_KEY"))
ALGORITHM = str(os.getenv("ALGORITHM"))
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", 24))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    prehashed = hashlib.sha256(plain_password.encode("utf-8")).digest()
    return bcrypt.checkpw(prehashed, hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    prehashed = hashlib.sha256(password.encode("utf-8")).digest()  
    return bcrypt.hashpw(prehashed, bcrypt.gensalt(rounds=12)).decode("utf-8")

def create_access_token(email: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode = {"exp": expire, "sub": email}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

access_token_cookie = APIKeyCookie(
    name="access_token",
    auto_error=False
)

async def get_current_user(
    request: Request,
    token: str = Depends(access_token_cookie)
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - no access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = User.objects(email=email).first()
    if user is None:
        raise credentials_exception
    
    return user