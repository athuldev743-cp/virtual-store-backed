# app/routers/users.py
from fastapi import APIRouter, HTTPException, Depends
from app.database import db
from app import schemas, auth
from bson import ObjectId
import hashlib

router = APIRouter(tags=["Users"])

# -----------------------
# Signup
# -----------------------
@router.post("/signup", response_model=schemas.UserOut, status_code=201)
async def signup(user: schemas.UserCreate):
    # Validate identifier
    if not user.email and not user.whatsapp:
        raise HTTPException(status_code=400, detail="Email or WhatsApp is required")
    
    # Check if email already exists
    if user.email:
        existing = await db["users"].find_one({"email": user.email.lower()})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if WhatsApp already exists
    if user.whatsapp:
        existing = await db["users"].find_one({"whatsapp": user.whatsapp})
        if existing:
            raise HTTPException(status_code=400, detail="WhatsApp already registered")
    
    # Hash password
    hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
    user_dict = user.dict()
    user_dict["password"] = hashed_password

    # Set default role
    role = "customer"
    user_dict["role"] = role

    # Insert user into MongoDB
    result = await db["users"].insert_one(user_dict)

    return {
        "id": str(result.inserted_id),
        "email": user.email,
        "whatsapp": user.whatsapp,
        "role": role  # <-- return the correct role
    }



# -----------------------
# Login
# -----------------------
@router.post("/login", response_model=schemas.Token)
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
    
    # Use email if exists, else WhatsApp as JWT subject
    identifier = user.get("email") or user.get("whatsapp")
    token = auth.create_access_token({"sub": identifier, "role": user.get("role")})
    return {"access_token": token, "token_type": "bearer"}
