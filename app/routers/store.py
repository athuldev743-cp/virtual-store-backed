# app/routers/store.py
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from typing import List, Optional
from pathlib import Path
import shutil
import os
import asyncio
from bson import ObjectId
from fastapi import Form

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


def save_uploaded_file(file: UploadFile, vendor_id: str) -> str:
    """Save uploaded file and return relative path"""
    filename = f"{vendor_id}_{Path(file.filename).name}"
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(file_path)


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


@router.post("/orders", response_model=schemas.OrderOut)
async def place_order(
    order_data: schemas.OrderCreate,
    user=Depends(auth.require_role(["customer"])),
    db=Depends(get_db)
):
    product = await db["products"].find_one({"_id": ObjectId(order_data.product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["stock"] < order_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    total_price = product["price"] * order_data.quantity
    order_doc = {
        "customer_id": str(user["_id"]),
        "vendor_id": str(product["vendor_id"]),
        "product_id": str(product["_id"]),
        "quantity": order_data.quantity,
        "total_price": total_price,
        "status": "pending"
    }

    result = await db["orders"].insert_one(order_doc)
    await db["products"].update_one(
        {"_id": product["_id"]},
        {"$inc": {"stock": -order_data.quantity}}
    )

    vendor = await db["vendors"].find_one({"_id": ObjectId(product["vendor_id"])})
    if vendor and vendor.get("whatsapp"):
        remaining_stock = product["stock"] - order_data.quantity
        message = (
            f"New order from {user.get('email') or user.get('whatsapp')}: "
            f"{order_data.quantity} x {product['name']}. Total: {total_price}. "
            f"Remaining stock: {remaining_stock}"
        )
        asyncio.create_task(send_whatsapp(vendor.get("whatsapp"), message))

    return {**order_doc, "id": str(result.inserted_id)}


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
    # check vendor approved
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

    # handle image upload
    if file:
        filename = f"{vendor['_id']}_{Path(file.filename).name}"
        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        product_doc["image_url"] = str(file_path)

    result = await db["products"].insert_one(product_doc)
    product_doc["id"] = str(result.inserted_id)
    return product_doc


@router.get("/vendors/status/{user_id}")
async def vendor_status(user_id: str, db=Depends(get_db)):
    vendor = await db["vendors"].find_one({"user_id": user_id})
    if not vendor:
        return {"status": "none"}  # Not applied yet
    return {"status": vendor.get("status", "pending")}


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
# Orders History
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
