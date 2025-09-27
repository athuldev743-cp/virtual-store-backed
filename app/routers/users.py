# app/routers/users.py
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext
from app import schemas, auth
from app.auth import hash_password, verify_password
from app.database import get_db
from bson import ObjectId
import traceback

router = APIRouter(tags=["Users"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------------
# Signup
# -------------------------
@router.post("/signup", response_model=schemas.Token)
async def signup(user: schemas.UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    email = (user.email or "").strip().lower()

    existing = await db["users"].find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        user_dict = {
            "username": user.username,
            "email": email,
            "password": hash_password(user.password),  # truncated automatically in auth.py
            "mobile": user.mobile or "",
            "address": user.address or "",
            "role": "customer",
        }

        result = await db["users"].insert_one(user_dict)

        token_data = {
            "sub": str(result.inserted_id),
            "role": "customer",
            "email": email,
        }
        access_token = auth.create_access_token(token_data)

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


# -------------------------
# Login
# -------------------------
@router.post("/login", response_model=schemas.Token)
async def login(form_data: schemas.UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    identifier = (form_data.email or "").strip().lower()
    user = await db["users"].find_one({"email": identifier})

    if not user or not verify_password(form_data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token(
        {
            "sub": str(user["_id"]),
            "role": user.get("role"),
            "email": user.get("email")
        },
        never_expire=True
    )

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
        "mobile": user.get("mobile"),      # updated field
        "address": user.get("address"),    # updated field
        "role": user.get("role")
    }
