# app/routers/store.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud, database, auth, models
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from twilio.rest import Client
import logging

router = APIRouter()

# -------------------------
# OAuth2 / JWT
# -------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")
SECRET_KEY = auth.SECRET_KEY
ALGORITHM = auth.ALGORITHM

# -------------------------
# Twilio WhatsApp
# -------------------------
TWILIO_SID = "your_twilio_sid"
TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

def send_whatsapp(to: str, message: str):
    """Send WhatsApp message via Twilio"""
    if not to:
        return
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=f"whatsapp:{to}"
        )
    except Exception as e:
        logging.error(f"Failed to send WhatsApp message: {e}")

# -------------------------
# Dependencies
# -------------------------
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier: str = payload.get("sub")
        if identifier is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Try email first, then WhatsApp
    user = crud.get_user_by_email(db, identifier) or crud.get_user_by_whatsapp(db, identifier)
    if not user:
        raise credentials_exception
    return user

def require_role(required_roles: List[str]):
    def role_checker(user: models.User = Depends(get_current_user)):
        if user.role not in required_roles:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return user
    return role_checker

# -------------------------
# Customer Endpoints
# -------------------------
@router.get("/products", response_model=List[schemas.ProductOut])
def list_products(db: Session = Depends(database.get_db)):
    return crud.list_products(db)

@router.post("/orders", response_model=schemas.OrderOut)
def place_order(
    order_data: schemas.OrderCreate,
    user: models.User = Depends(require_role(["customer"])),
    db: Session = Depends(database.get_db)
):
    order, msg = crud.create_order(db, user, order_data.product_id, order_data.quantity)
    if not order:
        raise HTTPException(status_code=400, detail=msg)

    # WhatsApp notification to vendor
    vendor = db.query(models.Vendor).filter(models.Vendor.id == order.vendor_id).first()
    if vendor and getattr(vendor.user, "whatsapp", None):
        message = (
            f"New order from {user.username}: {order.quantity} x {order.product.name}. "
            f"Total: {order.total_price}. Remaining stock: {order.product.stock}"
        )
        send_whatsapp(vendor.user.whatsapp, message)

    return order

# -------------------------
# Vendor Endpoints
# -------------------------
@router.post("/apply-vendor", response_model=schemas.VendorOut)
def apply_vendor(
    vendor_data: schemas.VendorCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    vendor, msg = crud.apply_vendor(db, current_user, vendor_data)
    if not vendor:
        raise HTTPException(status_code=400, detail=msg)
    return vendor

@router.post("/products", response_model=schemas.ProductOut)
def create_product(
    product: schemas.ProductCreate,
    user: models.User = Depends(require_role(["vendor"])),
    db: Session = Depends(database.get_db)
):
    vendor = db.query(models.Vendor).filter(
        models.Vendor.user_id == user.id, models.Vendor.status == "approved"
    ).first()
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor not approved")
    return crud.create_product(db, product, vendor.id)

@router.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    product: schemas.ProductCreate,
    user: models.User = Depends(require_role(["vendor"])),
    db: Session = Depends(database.get_db)
):
    vendor = db.query(models.Vendor).filter(
        models.Vendor.user_id == user.id, models.Vendor.status == "approved"
    ).first()
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor not approved")
    db_product = db.query(models.Product).filter(
        models.Product.id == product_id, models.Product.vendor_id == vendor.id
    ).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.name = product.name
    db_product.description = product.description
    db_product.price = product.price
    db_product.stock = product.stock
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    user: models.User = Depends(require_role(["vendor"])),
    db: Session = Depends(database.get_db)
):
    vendor = db.query(models.Vendor).filter(
        models.Vendor.user_id == user.id, models.Vendor.status == "approved"
    ).first()
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor not approved")
    db_product = db.query(models.Product).filter(
        models.Product.id == product_id, models.Product.vendor_id == vendor.id
    ).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"detail": "Product deleted successfully"}

# -------------------------
# Admin Endpoints
# -------------------------
@router.get("/vendors/pending", response_model=List[schemas.VendorOut])
def list_pending_vendors(
    user: models.User = Depends(require_role(["admin"])),
    db: Session = Depends(database.get_db)
):
    return db.query(models.Vendor).filter(models.Vendor.status == "pending").all()

@router.post("/vendors/{vendor_id}/approve")
def approve_vendor(
    vendor_id: int,
    user: models.User = Depends(require_role(["admin"])),
    db: Session = Depends(database.get_db)
):
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    vendor.status = "approved"
    vendor.user.role = "vendor"
    db.commit()
    return {"detail": f"Vendor {vendor_id} approved"}

@router.post("/vendors/{vendor_id}/reject")
def reject_vendor(
    vendor_id: int,
    user: models.User = Depends(require_role(["admin"])),
    db: Session = Depends(database.get_db)
):
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    vendor.status = "rejected"
    db.commit()
    return {"detail": f"Vendor {vendor_id} rejected"}

# -------------------------
# Orders history
# -------------------------
@router.get("/orders")
def get_orders(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    if user.role == "customer":
        return db.query(models.Order).filter(models.Order.customer_id == user.id).all()
    elif user.role == "vendor":
        vendor = db.query(models.Vendor).filter(models.Vendor.user_id == user.id).first()
        if not vendor:
            return []
        return db.query(models.Order).filter(models.Order.vendor_id == vendor.id).all()
    elif user.role == "admin":
        return db.query(models.Order).all()
