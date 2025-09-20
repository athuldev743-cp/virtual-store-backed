# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, crud, auth, database

router = APIRouter()

# -----------------------
# Signup
# -----------------------
@router.post("/signup", response_model=schemas.UserOut, status_code=201)
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    # Validate identifier
    if not user.email and not user.whatsapp:
        raise HTTPException(status_code=400, detail="Email or WhatsApp is required")
    
    # Check if email already exists
    if user.email:
        db_user = crud.get_user_by_email(db, email=user.email.lower())
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if WhatsApp already exists
    if user.whatsapp:
        db_user = crud.get_user_by_whatsapp(db, whatsapp=user.whatsapp)
        if db_user:
            raise HTTPException(status_code=400, detail="WhatsApp already registered")
    
    # Hash password and create user
    return crud.create_user(db, user)


# -----------------------
# Login
# -----------------------
@router.post("/login", response_model=schemas.Token)
def login(form_data: schemas.UserLogin, db: Session = Depends(database.get_db)):
    user = None

    if form_data.email:
        user = crud.get_user_by_email(db, email=form_data.email.lower())
    elif form_data.whatsapp:
        user = crud.get_user_by_whatsapp(db, whatsapp=form_data.whatsapp)
    else:
        raise HTTPException(status_code=400, detail="Email or WhatsApp is required")
    
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Use email if exists, else WhatsApp as JWT subject
    identifier = user.email if user.email else user.whatsapp
    token = auth.create_access_token({"sub": identifier, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}
