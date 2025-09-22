# app/routers/users.py
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext
import traceback

from app import schemas, auth
from app.auth import hash_password
from app.database import get_db
from app.schemas import UserCreate

router = APIRouter(tags=["Users"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------------------------
# Signup
# -------------------------
@router.post("/signup", response_model=schemas.Token)
async def signup(user: UserCreate):
    try:
        print("Signup route called")
        db: AsyncIOMotorDatabase = await get_db()

        # Check if user already exists
        existing = await db["users"].find_one({"email": user.email})
        if existing:
            print("User already exists:", user.email)
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password
        hashed_pw = hash_password(user.password)
        user_dict = user.dict()
        user_dict["password"] = hashed_pw
        user_dict["role"] = "customer"  # default role

        # Insert into DB
        result = await db["users"].insert_one(user_dict)
        print("User inserted with ID:", result.inserted_id)

        # Create JWT token
        token_data = {"sub": str(result.inserted_id), "role": "customer"}
        access_token = auth.create_access_token(token_data)

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        print("Signup error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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

    # Issue a never-expiring token
    token = auth.create_access_token(
        {"sub": str(user["_id"]), "role": user.get("role")},
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
        "whatsapp": user.get("whatsapp"),
        "role": user.get("role")
    }
