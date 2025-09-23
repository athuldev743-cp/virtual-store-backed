# app/crud.py
from app import schemas, auth
from app.database import get_db
from bson import ObjectId
from typing import List, Optional

# -------------------------
# User
# -------------------------
async def create_user(user: schemas.UserCreate):
    db = get_db()
    hashed_password = auth.hash_password(user.password)
    user_doc = {
        "username": user.username,
        "email": user.email.lower() if user.email else None,
        "whatsapp": getattr(user, "whatsapp", None),
        "password": hashed_password,
        "role": "customer"
    }
    result = await db["users"].insert_one(user_doc)
    user_doc["id"] = str(result.inserted_id)
    return user_doc

async def get_user_by_email(email: str):
    db = get_db()
    return await db["users"].find_one({"email": email.lower()})

async def get_user_by_whatsapp(whatsapp: str):
    db = get_db()
    return await db["users"].find_one({"whatsapp": whatsapp})

# -------------------------
# Vendor
# -------------------------
async def apply_vendor(user_id: str, vendor_data: schemas.VendorApply):
    db = get_db()
    existing = await db["vendors"].find_one({"user_id": user_id})
    if existing:
        return None, "Vendor application already exists"

    vendor_doc = {
        "user_id": user_id,
        "shop_name": vendor_data.shop_name,
        "description": vendor_data.description,
        "whatsapp": vendor_data.whatsapp,
        "status": "pending"
    }
    result = await db["vendors"].insert_one(vendor_doc)
    vendor_doc["id"] = str(result.inserted_id)
    return vendor_doc, "Vendor application submitted"

# -------------------------
# Product
# -------------------------
async def create_product(product: schemas.ProductCreate, vendor_id: str):
    db = get_db()
    product_doc = {**product.model_dump(), "vendor_id": vendor_id}
    result = await db["products"].insert_one(product_doc)
    product_doc["id"] = str(result.inserted_id)
    return product_doc

async def list_products() -> List[dict]:
    db = get_db()
    products_cursor = db["products"].find()
    products = []
    async for p in products_cursor:
        p["id"] = str(p["_id"])
        products.append(p)
    return products

# -------------------------
# Order
# -------------------------
async def create_order(customer_id: str, product_id: str, quantity: int = 1):
    db = get_db()
    product = await db["products"].find_one({"_id": ObjectId(product_id)})
    if not product:
        return None, "Product not found"
    if product["stock"] < quantity:
        return None, "Not enough stock"

    # Decrement stock
    await db["products"].update_one(
        {"_id": product["_id"]},
        {"$inc": {"stock": -quantity}}
    )

    vendor = await db["vendors"].find_one({"_id": ObjectId(product["vendor_id"])})
    total_price = product["price"] * quantity

    order_doc = {
        "product_id": str(product["_id"]),
        "customer_id": customer_id,
        "vendor_id": str(vendor["_id"]) if vendor else None,
        "quantity": quantity,
        "total_price": total_price,
        "status": "pending"
    }
    result = await db["orders"].insert_one(order_doc)
    order_doc["id"] = str(result.inserted_id)
    return order_doc, "Order placed successfully"
