# app/routers/users.py
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext

from app import schemas, auth
from app.database import get_db

router = APIRouter(tags=["Users"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------------------------
# Signup
# -------------------------
@router.post("/signup", response_model=schemas.Token)
async def signup(user: schemas.UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    email = (user.email or "").strip().lower()
    whatsapp = (user.whatsapp or "").strip()
    username = (user.username or "").strip()
    password = user.password.strip()

    # Check if email or whatsapp already exists
    if email:
        existing_email = await db["users"].find_one({"email": email})
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    if whatsapp:
        existing_wp = await db["users"].find_one({"whatsapp": whatsapp})
        if existing_wp:
            raise HTTPException(status_code=400, detail="WhatsApp already registered")

    hashed_password = pwd_context.hash(password)
    user_dict = {
        "username": username,
        "email": email if email else None,
        "whatsapp": whatsapp if whatsapp else None,
        "password": hashed_password,
        "role": "customer"
    }

    result = await db["users"].insert_one(user_dict)
    token = auth.create_access_token({"sub": str(result.inserted_id), "role": "customer"})
    return {"access_token": token, "token_type": "bearer"}


# -------------------------
# Login
# -------------------------
@router.post("/login", response_model=schemas.Token)
async def login(form_data: schemas.UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    identifier = (form_data.email or form_data.whatsapp or "").strip().lower()
    user = None

    if form_data.email:
        user = await db["users"].find_one({"email": identifier})
    if not user and form_data.whatsapp:
        user = await db["users"].find_one({"whatsapp": identifier})

    if not user or not pwd_context.verify(form_data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token({"sub": str(user["_id"]), "role": user.get("role")})
    return {"access_token": token, "token_type": "bearer"}


# -------------------------
# Get Current User
# -------------------------
@router.get("/me", response_model=schemas.UserOut)
async def get_me(user=Depends(auth.get_current_user)):
    return {
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "whatsapp": user.get("whatsapp"),
        "role": user.get("role")
    }
