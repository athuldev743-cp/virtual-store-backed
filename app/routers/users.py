# app/routers/users.py
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext
import traceback

from app import schemas, auth
from app.auth import hash_password
from app.database import get_db

router = APIRouter(tags=["Users"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------------------------
# Signup
# -------------------------
@router.post("/signup", response_model=schemas.Token)
async def signup(user: schemas.UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Create a new user and return an access token.
    """
    try:
        # Validate input
        if not user.email or not user.password:
            raise HTTPException(status_code=400, detail="Email and password required")

        # Check if user already exists
        existing = await db["users"].find_one({"email": user.email.lower()})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password
        hashed_pw = hash_password(user.password)

        # Convert Pydantic model to dict safely
        user_dict = user.model_dump() if hasattr(user, "model_dump") else user.dict()
        user_dict["password"] = hashed_pw
        user_dict["role"] = "customer"  # default role

        # Insert user into DB
        result = await db["users"].insert_one(user_dict)

        # Create JWT token
        token_data = {"sub": str(result.inserted_id), "role": "customer"}
        access_token = auth.create_access_token(token_data)

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


# -------------------------
# Login
# -------------------------
@router.post("/login", response_model=schemas.Token)
async def login(form_data: schemas.UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Authenticate user via email or WhatsApp and return access token.
    """
    try:
        identifier = (form_data.email or form_data.whatsapp or "").strip().lower()
        user = None

        if form_data.email:
            user = await db["users"].find_one({"email": identifier})
        if not user and form_data.whatsapp:
            user = await db["users"].find_one({"whatsapp": identifier})

        if not user or not pwd_context.verify(form_data.password, user.get("password", "")):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = auth.create_access_token(
            {"sub": str(user["_id"]), "role": user.get("role")},
            never_expire=True
        )

        return {"access_token": token, "token_type": "bearer"}

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


# -------------------------
# Get Current User
# -------------------------
@router.get("/me", response_model=schemas.UserOut)
async def get_me(user=Depends(auth.get_current_user)):
    """
    Get the currently logged-in user.
    """
    return {
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "whatsapp": user.get("whatsapp"),
        "address": user.get("address"),
        "role": user.get("role")
    }
