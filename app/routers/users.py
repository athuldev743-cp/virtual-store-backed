from fastapi import APIRouter, HTTPException
from app.database import db
from app import schemas, auth
import hashlib

router = APIRouter(tags=["Users"])

# -------------------
# Signup
# -------------------
@router.post("/signup")
async def signup(user: schemas.UserCreate):
    if not user.email and not user.whatsapp:
        raise HTTPException(status_code=400, detail="Email or WhatsApp is required")
    
    # Check if email exists
    if user.email:
        existing = await db["users"].find_one({"email": user.email.lower()})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if WhatsApp exists
    if user.whatsapp:
        existing = await db["users"].find_one({"whatsapp": user.whatsapp})
        if existing:
            raise HTTPException(status_code=400, detail="WhatsApp already registered")
    
    # Hash password
    hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    user_dict["role"] = "customer"  # everyone is customer

    # Insert into DB
    result = await db["users"].insert_one(user_dict)

    # Create JWT token
    identifier = user.email or user.whatsapp
    token = auth.create_access_token({"sub": identifier, "role": "customer"})

    return {"access_token": token, "token_type": "bearer"}

# -------------------
# Login
# -------------------
@router.post("/login")
async def login(form_data: schemas.UserLogin):
    user = None
    if form_data.email:
        user = await db["users"].find_one({"email": form_data.email.lower()})
    elif form_data.whatsapp:
        user = await db["users"].find_one({"whatsapp": form_data.whatsapp})
    else:
        raise HTTPException(status_code=400, detail="Email or WhatsApp is required")
    
    if not user or not auth.verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    identifier = user.get("email") or user.get("whatsapp")
    token = auth.create_access_token({"sub": identifier, "role": user.get("role")})

    return {"access_token": token, "token_type": "bearer"}
