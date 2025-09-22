# app/routers/users.py
from fastapi import APIRouter, HTTPException
from app import schemas, auth
from app.database import db
from passlib.context import CryptContext

router = APIRouter(tags=["Users"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------
# Signup
# -------------------
@router.post("/signup", response_model=schemas.Token)
async def signup(user: schemas.UserCreate):
    username = user.username.strip()
    email = user.email.strip().lower()
    password = user.password.strip()

    # Check if email already exists
    existing = await db["users"].find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password = pwd_context.hash(password)

    # Insert into DB
    user_dict = {
        "username": username,
        "email": email,
        "password": hashed_password,
        "role": "customer"
    }
    result = await db["users"].insert_one(user_dict)

    # Create JWT token
    token = auth.create_access_token({"sub": str(result.inserted_id), "role": "customer"})

    return {"access_token": token, "token_type": "bearer"}

# -------------------
# Login
# -------------------
@router.post("/login", response_model=schemas.Token)
async def login(form_data: schemas.UserLogin):
    email = form_data.email.strip().lower()
    user = await db["users"].find_one({"email": email})

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(form_data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token({"sub": str(user["_id"]), "role": user.get("role")})

    return {"access_token": token, "token_type": "bearer"}
