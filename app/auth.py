# app/auth.py - Using bcrypt directly
import bcrypt
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_db
from bson import ObjectId

load_dotenv()

SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey123")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# -------------------------------
# Password hashing with bcrypt directly
# -------------------------------
def hash_password(password: str) -> str:
    """Hash a password using bcrypt (automatically handles 72-byte limit)"""
    # bcrypt internally handles the 72-byte limit, but we'll truncate to be safe
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    plain_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)

# -------------------------------
# JWT Tokens (unchanged)
# -------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

def create_access_token(data: dict, never_expire: bool = True) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if not never_expire:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    """Fetch current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier: str = payload.get("sub")
        if not identifier:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db["users"].find_one({"_id": ObjectId(identifier)})
    if not user:
        raise credentials_exception
    return user

def require_role(required_roles: List[str]):
    """FastAPI dependency to require a role"""
    async def role_checker(user=Depends(get_current_user)) -> dict:
        if user.get("role") not in required_roles:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return user
    return role_checker

def decode_access_token(token: str) -> Dict:
    """Decode JWT token payload (without FastAPI dependencies)"""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])