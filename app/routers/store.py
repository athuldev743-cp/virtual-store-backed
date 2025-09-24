# app/routers/store.py
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Body, Form
from typing import List, Optional
from pathlib import Path
import shutil
import os
import asyncio
from bson import ObjectId
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app import schemas, auth
from app.utils.twilio_utils import send_whatsapp

router = APIRouter(tags=["Store"])

# -------------------------
# Config & Uploads
# -------------------------
UPLOAD_DIR = Path("uploads/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TWILIO_WHATSAPP_ADMIN = os.getenv("TWILIO_WHATSAPP_NUMBER")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")  # Absolute URL


def save_uploaded_file(file: UploadFile, vendor_id: str) -> str:
    """Save uploaded file and return absolute URL"""
    filename = f"{vendor_id}_{Path(file.filename).name}"
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"{BACKEND_URL}/uploads/products/{filename}" 


# -------------------------
# Customer Endpoints
# -------------------------
@router.get("/products", response_model=List[schemas.ProductOut])
async def list_products(db=Depends(get_db)):
    products_cursor = db["products"].find()
    products = []
    async for p in products_cursor:
        p["id"] = str(p["_id"])
        products.append(p)
    return products


# -------------------------
# Vendor Endpoints
# -------------------------
@router.post("/products", response_model=schemas.ProductOut)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(0.0),
    stock: float = Form(0.0),
    file: Optional[UploadFile] = File(None),
    user=Depends(auth.require_role(["vendor"])),
    db=Depends(get_db)
):
    vendor = await db["vendors"].find_one({"user_id": str(user["_id"]), "status": "approved"})
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor not approved")

    product_doc = {
        "vendor_id": vendor["_id"],
        "name": name,
        "description": description,
        "price": price,
        "stock": stock,
    }

    if file:
        product_doc["image_url"] = save_uploaded_file(file, str(vendor["_id"]))

    result = await db["products"].insert_one(product_doc)
    product_doc["id"] = str(result.inserted_id)
    return product_doc


@router.put("/products/{product_id}", response_model=schemas.ProductOut)
async def update_product(
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
        updated_data["image_url"] = save_uploaded_file(file, str(vendor["_id"]))

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

    vendor_doc = {
        "user_id": str(user["_id"]),
        "shop_name": shop_name,
        "whatsapp": whatsapp or user.get("whatsapp"),
        "description": description,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    result = await db["vendors"].insert_one(vendor_doc)
    vendor_doc["id"] = str(result.inserted_id)
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


# -------------------------
# Orders Endpoints
# -------------------------
@router.get("/orders")
async def get_orders(user=Depends(auth.get_current_user), db=Depends(get_db)):
    if user.get("role") == "customer":
        orders_cursor = db["orders"].find({"customer_id": str(user["_id"])})
    elif user.get("role") == "vendor":
        vendor = await db["vendors"].find_one({"user_id": str(user["_id"])})
        if not vendor:
            return []
        orders_cursor = db["orders"].find({"vendor_id": str(vendor["_id"])})
    elif user.get("role") == "admin":
        orders_cursor = db["orders"].find()
    else:
        return []

    orders = []
    async for o in orders_cursor:
        o["id"] = str(o["_id"])
        orders.append(o)
    return orders


@router.post("/orders")
async def place_order(
    product_id: str,
    quantity: float,
    mobile: str = None,
    address: str = None,
    user=Depends(auth.require_role(["customer"])),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    product = await db["products"].find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["stock"] < quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    new_stock = product["stock"] - quantity
    await db["products"].update_one({"_id": ObjectId(product_id)}, {"$set": {"stock": new_stock}})

    order_doc = {
        "product_id": str(product["_id"]),
        "vendor_id": str(product["vendor_id"]),
        "customer_id": str(user["_id"]),
        "quantity": quantity,
        "total": product["price"] * quantity,
        "created_at": datetime.utcnow(),
        "mobile": mobile or user.get("whatsapp", "N/A"),
        "address": address or user.get("address", "N/A"),
        "status": "pending"
    }

    result = await db["orders"].insert_one(order_doc)
    order_doc["id"] = str(result.inserted_id)

    vendor = await db["vendors"].find_one({"_id": ObjectId(product["vendor_id"])})
    if vendor:
        vendor_user = await db["users"].find_one({"_id": ObjectId(vendor["user_id"])})
        vendor_whatsapp = vendor_user.get("whatsapp") if vendor_user else None
        if vendor_whatsapp:
            msg = (
                f"🛒 *New Order Received!*\n\n"
                f"📦 Product: {product['name']}\n"
                f"⚖️ Quantity: {quantity} kg\n"
                f"💰 Total: ₹{product['price'] * quantity:.2f}\n\n"
                f"👤 Customer: {user.get('username', 'N/A')}\n"
                f"📱 Mobile: {order_doc['mobile']}\n"
                f"📍 Address: {order_doc['address']}"
            )
            asyncio.create_task(send_whatsapp(vendor_whatsapp, msg))

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
