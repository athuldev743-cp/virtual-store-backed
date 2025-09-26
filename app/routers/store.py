# app/routers/store.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body, Request
from typing import List, Optional
from pathlib import Path
import shutil
import os
import asyncio
from bson import ObjectId
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from app.database import get_db
from app import schemas, auth
from app.utils.twilio_utils import send_whatsapp
from bson.errors import InvalidId
from fastapi import Form
from fastapi import app

router = APIRouter(tags=["Store"])

# -------------------------
# Config & Uploads
# -------------------------
UPLOAD_DIR = Path("uploads/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TWILIO_WHATSAPP_ADMIN = os.getenv("TWILIO_WHATSAPP_NUMBER")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")  # Absolute URL

def save_uploaded_file(file: UploadFile, vendor_id: str, request: Request) -> str:
    filename = f"{vendor_id}_{Path(file.filename).name}"
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    url = str(request.url_for("uploads", path=f"products/{filename}"))
    return url

# -------------------------
# Customer Endpoints
# -------------------------
class OrderCreate(BaseModel):
    product_id: str
    quantity: float = Field(..., gt=0)
    mobile: Optional[str] = None
    address: Optional[str] = None

@router.post("/orders")
async def place_order(
    order: OrderCreate,
    user=Depends(auth.require_role(["customer"])),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    product = await db["products"].find_one({"_id": ObjectId(order.product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["stock"] < order.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    new_stock = product["stock"] - order.quantity
    await db["products"].update_one({"_id": ObjectId(order.product_id)}, {"$set": {"stock": new_stock}})

    order_doc = {
        "product_id": str(product["_id"]),
        "vendor_id": str(product["vendor_id"]),
        "customer_id": str(user["_id"]),
        "quantity": order.quantity,
        "total": product["price"] * order.quantity,
        "created_at": datetime.utcnow(),
        "mobile": order.mobile or user.get("whatsapp", "N/A"),
        "address": order.address or user.get("address", "N/A"),
        "status": "pending"
    }

   
    result = await db["orders"].insert_one(order_doc)
    order_doc["id"] = str(result.inserted_id)

# ------------------------- 
# Notify vendor via WhatsApp
    vendor = await db["vendors"].find_one({"_id": ObjectId(product["vendor_id"])})
    if vendor and vendor.get("whatsapp"):
     msg = (
        f"🛒 *New Order Received!*\n\n"
        f"📦 Product: {product['name']}\n"
        f"⚖️ Quantity: {order.quantity} kg\n"
        f"💰 Total: ₹{product['price'] * order.quantity:.2f}\n\n"
        f"👤 Customer: {user.get('username', 'N/A')}\n"
        f"📱 Mobile: {order_doc['mobile']}\n"
        f"📍 Address: {order_doc['address']}"
    )
    whatsapp_sent = await send_whatsapp(vendor["whatsapp"], msg)

# Include in response
    order_doc["vendor_notified"] = whatsapp_sent


     

    return {
        "id": order_doc["id"],
        "product_id": order_doc["product_id"],
        "vendor_id": order_doc["vendor_id"],
        "customer_id": order_doc["customer_id"],
        "quantity": order_doc["quantity"],
        "total": order_doc["total"],
        "mobile": order_doc["mobile"],
        "address": order_doc["address"],
        "status": order_doc["status"],
        "remaining_stock": new_stock
    }

# -------------------------
# Vendor Endpoints
# -------------------------
@router.put("/products/{product_id}", response_model=schemas.ProductOut)
async def update_product(
    request: Request,
    product_id: str,
    name: str,
    description: str,
    price: float,
    stock: int,
    file: Optional[UploadFile] = File(None),
    user=Depends(auth.require_role(["vendor"])),
    db=Depends(get_db)
):
    vendor = await db["vendors"].find_one({"user_id": str(user["_id"]), "status": "approved"})
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor not approved")

    db_product = await db["products"].find_one({"_id": ObjectId(product_id), "vendor_id": vendor["_id"]})
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    updated_data = {"name": name, "description": description, "price": price, "stock": stock}
    if file:
        updated_data["image_url"] = save_uploaded_file(file, str(vendor["_id"]), request)

    await db["products"].update_one({"_id": db_product["_id"]}, {"$set": updated_data})
    updated_product = await db["products"].find_one({"_id": db_product["_id"]})
    updated_product["id"] = str(updated_product["_id"])
    return updated_product

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    user=Depends(auth.require_role(["vendor"])),
    db=Depends(get_db)
):
    vendor = await db["vendors"].find_one({"user_id": str(user["_id"]), "status": "approved"})
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor not approved")

    db_product = await db["products"].find_one({"_id": ObjectId(product_id), "vendor_id": vendor["_id"]})
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db["products"].delete_one({"_id": db_product["_id"]})
    return {"detail": "Product deleted successfully"}
@router.post("/products", response_model=schemas.ProductOut)
async def create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    stock: float = Form(...),
    file: Optional[UploadFile] = File(None),
    user=Depends(auth.require_role(["vendor"])),
    db=Depends(get_db)
):
    # Check vendor approval
    vendor = await db["vendors"].find_one({"user_id": str(user["_id"]), "status": "approved"})
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor not approved")

    product_doc = {
        "vendor_id": vendor["_id"],
        "name": name,
        "description": description,
        "price": price,
        "stock": stock,
        "image_url": save_uploaded_file(file, str(vendor["_id"]), request) if file else None,
        "created_at": datetime.utcnow()
    }

    result = await db["products"].insert_one(product_doc)
    product_doc["id"] = str(result.inserted_id)
    return product_doc

@router.post("/vendors/apply", response_model=schemas.VendorOut)
async def apply_vendor_endpoint(
    shop_name: str = Body(...),
    whatsapp: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    user=Depends(auth.require_role(["customer"])),
    db=Depends(get_db)
):
    existing = await db["vendors"].find_one({
        "user_id": str(user["_id"]),
        "status": {"$in": ["pending", "approved"]}
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have a vendor application or are a vendor")

    # Normalize WhatsApp number
    normalized_whatsapp = whatsapp or user.get("whatsapp")
    if normalized_whatsapp:
        raw_number = normalized_whatsapp.strip().replace(" ", "")
        if not raw_number.startswith("+"):
            raw_number = "+91" + raw_number  # assume India
        normalized_whatsapp = f"whatsapp:{raw_number}"

    vendor_doc = {
        "user_id": str(user["_id"]),
        "shop_name": shop_name,
        "whatsapp": normalized_whatsapp,
        "description": description,
        "status": "pending",
        "created_at": datetime.utcnow()
    }

    # Insert into DB
    result = await db["vendors"].insert_one(vendor_doc)
    vendor_doc["id"] = str(result.inserted_id)

    # Send WhatsApp to the applicant
    if normalized_whatsapp:
        asyncio.create_task(
            send_whatsapp(
                normalized_whatsapp,
                "✅ Your vendor application has been received! Please wait for approval."
            )
        )

    # Optional: Notify admin WhatsApp
    if TWILIO_WHATSAPP_ADMIN:
        asyncio.create_task(
            send_whatsapp(
                TWILIO_WHATSAPP_ADMIN,
                f"🆕 New Vendor Application!\nShop: {shop_name}\nUser: {user.get('username')}\nWhatsApp: {normalized_whatsapp}"
            )
        )

    return vendor_doc


@router.get("/vendors/status/{user_id}", response_model=dict)
async def get_vendor_status(user_id: str, db=Depends(get_db)):
    vendor = await db["vendors"].find_one({"user_id": user_id})
    if not vendor:
        return {"status": "none"}
    return {"status": vendor.get("status", "pending")}

@router.get("/vendors", response_model=List[schemas.VendorOut])
async def list_approved_vendors(db=Depends(get_db)):
    vendors_cursor = db["vendors"].find({"status": "approved"})
    vendors = []
    async for v in vendors_cursor:
        v["id"] = str(v["_id"])
        vendors.append(v)
    return vendors

@router.get("/vendors/{vendor_id}/products", response_model=List[schemas.ProductOut])
async def get_vendor_products(vendor_id: str, db=Depends(get_db)):
    try:
        vendor_oid = ObjectId(vendor_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid vendor_id")

    products_cursor = db["products"].find({"vendor_id": vendor_oid})
    products = []
    async for p in products_cursor:
        p["id"] = str(p["_id"])
        products.append(p)
    return products

# -------------------------
# Admin Endpoints
# -------------------------
@router.get("/vendors/pending", response_model=List[schemas.VendorOut])
async def list_pending_vendors(user=Depends(auth.require_role(["admin"])), db=Depends(get_db)):
    vendors_cursor = db["vendors"].find({"status": "pending"})
    vendors = []
    async for v in vendors_cursor:
        v["id"] = str(v["_id"])
        vendors.append(v)
    return vendors

@router.post("/vendors/{vendor_id}/approve")
async def approve_vendor(vendor_id: str, user=Depends(auth.require_role(["admin"])), db=Depends(get_db)):
    vendor = await db["vendors"].find_one({"_id": ObjectId(vendor_id)})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    await db["vendors"].update_one({"_id": ObjectId(vendor_id)}, {"$set": {"status": "approved"}})
    await db["users"].update_one({"_id": ObjectId(vendor["user_id"])}, {"$set": {"role": "vendor"}})

    user_doc = await db["users"].find_one({"_id": ObjectId(vendor["user_id"])})
    if user_doc and user_doc.get("whatsapp"):
        asyncio.create_task(send_whatsapp(user_doc.get("whatsapp"), "Congratulations! Your vendor application has been approved."))

    return {"detail": f"Vendor {vendor_id} approved"}

@router.post("/vendors/{vendor_id}/reject")
async def reject_vendor(vendor_id: str, user=Depends(auth.require_role(["admin"])), db=Depends(get_db)):
    vendor = await db["vendors"].find_one({"_id": ObjectId(vendor_id)})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    await db["vendors"].update_one({"_id": ObjectId(vendor_id)}, {"$set": {"status": "rejected"}})
    user_doc = await db["users"].find_one({"_id": ObjectId(vendor["user_id"])})
    if user_doc and user_doc.get("whatsapp"):
        asyncio.create_task(send_whatsapp(user_doc.get("whatsapp"), "Your vendor application has been rejected. You can reapply later."))

    return {"detail": f"Vendor {vendor_id} rejected"}

