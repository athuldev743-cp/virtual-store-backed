# app/auth.py
import os
from datetime import datetime, timedelta
from typing import Optional, List
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

# Import get_db instead of db
from app.database import get_db

# Load .env
load_dotenv()

# -------------------------------
# Environment variables
# -------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# -------------------------------
# Password hashing
# -------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# -------------------------------
# JWT Tokens
# -------------------------------
# -------------------------------
# JWT Tokens
# -------------------------------
def create_access_token(data: dict, never_expire: bool = True) -> str:
    """
    Creates an access token.
    If never_expire=True, token will not have an expiration and stays valid until logout.
    """
    to_encode = data.copy()
    
    if not never_expire:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)



def create_refresh_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# -------------------------------
# OAuth2 and current user dependency
# -------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier: str = payload.get("sub")
        if identifier is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = get_db()
    # first try email
    user = await db["users"].find_one({"email": identifier})
    if not user:
        # fallback to whatsapp
        user = await db["users"].find_one({"whatsapp": identifier})
    if not user:
        raise credentials_exception
    return user

# -------------------------------
# Role dependency helper
# -------------------------------
def require_role(required_roles: List[str]):
    async def role_checker(user=Depends(get_current_user)):
        if user.get("role") not in required_roles:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return user
    return role_checker
# Helper to decode access token (for tests / scripts)
# -------------------------------
def decode_access_token(token: str) -> dict:
    """
    Decode a JWT token and return its payload without FastAPI dependencies.
    Raises JWTError if token is invalid.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])