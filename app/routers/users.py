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
    print(f"[DEBUG] Signup payload: {user}")

    existing = await db["users"].find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        print(f"[DEBUG] Before hash_password call")
        print(f"[DEBUG] Password length: {len(user.password)} chars, {len(user.password.encode('utf-8'))} bytes")
        
        # Test the hash_password function directly
        test_hash = hash_password(user.password)
        print(f"[DEBUG] hash_password succeeded: {test_hash[:50]}...")
        
        user_dict = {
            "username": user.username,
            "email": email,
            "password": test_hash,  # Use the already hashed password
            "mobile": user.mobile or "",
            "address": user.address or "",
            "role": "customer",
        }

        result = await db["users"].insert_one(user_dict)
        print(f"[DEBUG] Inserted user ID: {result.inserted_id}")

        token_data = {"sub": str(result.inserted_id), "role": "customer", "email": email}
        access_token = auth.create_access_token(token_data)
        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        print(f"[DEBUG] ERROR TYPE: {type(e)}")
        print(f"[DEBUG] ERROR MESSAGE: {str(e)}")
        import traceback
        print(f"[DEBUG] FULL TRACEBACK:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
