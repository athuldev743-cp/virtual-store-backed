# app/routers/users.py
from fastapi import APIRouter, HTTPException
from app import schemas, auth
from app.database import db
from passlib.context import CryptContext
import re

router = APIRouter(tags=["Users"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------
# Signup
# -------------------
# -------------------
# Signup
# -------------------
@router.post("/signup", response_model=schemas.Token)
async def signup(user: schemas.UserCreate):
    # Strip spaces
    username = user.username.strip()
    email = user.email.strip().lower()
    password = user.password.strip()

    # Check if email exists
    existing = await db["users"].find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ✅ Password validation
    if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long, include one uppercase letter, one lowercase letter, one number, and one special character."
        )

    # Hash password
    hashed_password = pwd_context.hash(password)

    # Insert into DB
    user_dict = {
        "username": username,
        "email": email,
        "password": hashed_password,
        "role": "customer"  # default role
    }
    result = await db["users"].insert_one(user_dict)

    # Create JWT token
    token = auth.create_access_token({"sub": str(result.inserted_id), "role": "customer"})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# -------------------
# Login
# -------------------
@router.post("/login", response_model=schemas.Token)
async def login(form_data: schemas.UserLogin):
    email_or_whatsapp = form_data.email.strip() if form_data.email else None
    user = None

    if email_or_whatsapp:
        user = await db["users"].find_one({"email": email_or_whatsapp.lower()})
    elif getattr(form_data, "whatsapp", None):
        whatsapp = form_data.whatsapp.strip()
        user = await db["users"].find_one({"whatsapp": whatsapp})
    else:
        raise HTTPException(status_code=400, detail="Email or WhatsApp is required")

    if not user or not pwd_context.verify(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Use MongoDB _id as identifier
    token = auth.create_access_token({"sub": str(user["_id"]), "role": user.get("role")})

    return {
        "access_token": token,
        "token_type": "bearer"
    }
