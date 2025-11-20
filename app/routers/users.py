from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app import schemas, auth
from app.auth import hash_password, verify_password
from app.database import get_db
import traceback

router = APIRouter(tags=["Users"])

@router.post("/signup", response_model=schemas.Token)
async def signup(user: schemas.UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise RuntimeError("Database not connected")
    
    email = (user.email or "").strip().lower()
    
    # Add password validation
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    
    if not any(char.isdigit() for char in user.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")
    
    if not any(char.isupper() for char in user.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    
    if not any(char.islower() for char in user.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")

    existing = await db["users"].find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        # Add more debugging
        print(f"[DEBUG] Password to hash: '{user.password}'")
        print(f"[DEBUG] Password type: {type(user.password)}")
        
        hashed_password = hash_password(user.password)
        print(f"[DEBUG] Hashed password type: {type(hashed_password)}")
        print(f"[DEBUG] Hashed password sample: {str(hashed_password)[:50]}")

        # Ensure it's a string
        if not isinstance(hashed_password, str):
            hashed_password = str(hashed_password)
            
        user_dict = {
            "username": user.username,
            "email": email,
            "password": hashed_password,
            "mobile": user.mobile or "",
            "address": user.address or "",
            "role": "customer",
        }

        result = await db["users"].insert_one(user_dict)
        
        token_data = {"sub": str(result.inserted_id), "role": "customer", "email": email}
        access_token = auth.create_access_token(token_data)
        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        print(f"[DEBUG] ERROR during signup: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error during registration")


@router.post("/login", response_model=schemas.Token)
async def login(form_data: schemas.UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise RuntimeError("Database not connected")
    identifier = (form_data.email or "").strip().lower()
    user = await db["users"].find_one({"email": identifier})
    if not user or not verify_password(form_data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token({
        "sub": str(user["_id"]),
        "role": user.get("role"),
        "email": user.get("email")
    }, never_expire=True)

    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
async def get_me(user=Depends(auth.get_current_user)):
    return {
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "mobile": user.get("mobile"),
        "address": user.get("address"),
        "role": user.get("role")
    }
