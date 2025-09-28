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
from fastapi.responses import FileResponse
from pathlib import Path
import cloudinary 
import cloudinary.uploader
import cloudinary.api

router = APIRouter(tags=["Store"])

# -------------------------
# Config & Uploads
# -------------------------
UPLOAD_DIR = Path("uploads/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TWILIO_WHATSAPP_ADMIN = os.getenv("TWILIO_WHATSAPP_NUMBER")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")  # Absolute URL


# -------------------------
# Cloudinary setup
# -------------------------
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def upload_to_cloudinary(file: UploadFile, folder: str = "virtual_store") -> str:
    """
    Uploads a file to Cloudinary and returns the secure URL
    """
    try:
        result = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            public_id=f"{folder}_{Path(file.filename).stem}_{int(datetime.utcnow().timestamp())}",
            overwrite=True,
            resource_type="image"
        )
        return result.get("secure_url")
    except Exception as e:
        print("Cloudinary upload failed:", e)
        return None

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
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    product = await db["products"].find_one({"_id": ObjectId(order.product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Convert stock to int if it's float
    product_stock = product.get("stock", 0)
    if isinstance(product_stock, float):
        product_stock = int(product_stock)
    
    if product_stock < order.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    new_stock = product_stock - order.quantity
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

@router.get("/products/{product_id}", response_model=schemas.ProductOut)
async def get_product(product_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    try:
        product = await db["products"].find_one({"_id": ObjectId(product_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Convert stock to int if it's float
    stock = product.get("stock", 0)
    if isinstance(stock, float):
        stock = int(stock)
        product["stock"] = stock
    
    return schemas.ProductOut.from_mongo(product)

@router.get("/products", response_model=List[schemas.ProductOut])
async def list_all_products(db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    products_cursor = db["products"].find({})
    products = []
    async for p in products_cursor:
        # Convert stock to int if it's float
        stock = p.get("stock", 0)
        if isinstance(stock, float):
            stock = int(stock)
        
        products.append(
            schemas.ProductOut(
                id=str(p["_id"]),
                name=p.get("name", ""),
                description=p.get("description"),
                price=p.get("price", 0),
                stock=stock,  # Use converted stock value
                image_url=p.get("image_url")
            )
        )
    return products

# -------------------------
# Vendor Endpoints
# -------------------------
@router.put("/products/{product_id}", response_model=schemas.ProductOut)
async def update_product(
    request: Request,
    product_id: str,
    name: str = Form(...),           # ADD Form()
    description: str = Form(...),    # ADD Form()
    price: float = Form(...),        # ADD Form()
    stock: int = Form(...),          # ADD Form()
    file: Optional[UploadFile] = File(None),
    user=Depends(auth.require_role(["vendor"])),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    # ... rest of your code remains the same
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    vendor = await db["vendors"].find_one({"user_id": str(user["_id"]), "status": "approved"})
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor not approved")

    db_product = await db["products"].find_one({"_id": ObjectId(product_id), "vendor_id": vendor["_id"]})
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    updated_data = {"name": name, "description": description, "price": price, "stock": stock}
    
    if file:
        # Upload image to Cloudinary instead of local storage
        updated_data["image_url"] = upload_to_cloudinary(file, folder=f"vendor_{vendor['_id']}")

    await db["products"].update_one({"_id": db_product["_id"]}, {"$set": updated_data})
    updated_product = await db["products"].find_one({"_id": db_product["_id"]})
    
    # Convert stock to int if it's float
    stock = updated_product.get("stock", 0)
    if isinstance(stock, float):
        stock = int(stock)
    
    return schemas.ProductOut(
        id=str(updated_product["_id"]),
        name=updated_product.get("name", ""),
        description=updated_product.get("description"),
        price=updated_product.get("price", 0),
        stock=stock,
        image_url=updated_product.get("image_url")
    )

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    user=Depends(auth.require_role(["vendor"])),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
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
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # Check vendor approval
    vendor = await db["vendors"].find_one({"user_id": str(user["_id"]), "status": "approved"})
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor not approved")

    image_url = None
    if file:
        image_url = upload_to_cloudinary(file, folder=f"vendor_{vendor['_id']}")

    # Convert stock to int if it's float
    if isinstance(stock, float):
        stock = int(stock)

    product_doc = {
        "vendor_id": vendor["_id"],
        "name": name,
        "description": description,
        "price": price,
        "stock": stock,
        "image_url": image_url,
        "created_at": datetime.utcnow()
    }

    result = await db["products"].insert_one(product_doc)
    
    return schemas.ProductOut(
        id=str(result.inserted_id),
        name=name,
        description=description,
        price=price,
        stock=stock,
        image_url=image_url
    )

@router.post("/vendors/apply", response_model=schemas.VendorOut)
async def apply_vendor_endpoint(
    shop_name: str = Body(...),
    whatsapp: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    user=Depends(auth.require_role(["customer"])),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
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
async def get_vendor_status(user_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    vendor = await db["vendors"].find_one({"user_id": user_id})
    if not vendor:
        return {"status": "none"}
    return {"status": vendor.get("status", "pending")}

@router.get("/vendors", response_model=List[schemas.VendorOut])
async def list_approved_vendors(db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    vendors_cursor = db["vendors"].find({"status": "approved"})
    vendors = []
    async for v in vendors_cursor:
        v["id"] = str(v["_id"])
        vendors.append(v)
    return vendors

@router.get("/vendors/{vendor_id}/products", response_model=List[schemas.ProductOut])
async def get_vendor_products(vendor_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    try:
        vendor_oid = ObjectId(vendor_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid vendor_id")

    products_cursor = db["products"].find({"vendor_id": vendor_oid})
    products = []
    async for p in products_cursor:
        # Convert stock to int if it's float
        stock = p.get("stock", 0)
        if isinstance(stock, float):
            stock = int(stock)
        
        products.append(
            schemas.ProductOut(
                id=str(p["_id"]),
                name=p.get("name", ""),
                description=p.get("description"),
                price=p.get("price", 0),
                stock=stock,
                image_url=p.get("image_url")
            )
        )
    return products
@router.get("/vendors/my-vendor", response_model=schemas.VendorOut)
async def get_my_vendor(
    user=Depends(auth.require_role(["vendor"])),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get the vendor profile for the currently logged-in user"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # Find the vendor that belongs to the current user
    vendor = await db["vendors"].find_one({"user_id": str(user["_id"])})
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Convert stock values to int if they're floats
    if 'stock' in vendor and isinstance(vendor['stock'], float):
        vendor['stock'] = int(vendor['stock'])
    
    return schemas.VendorOut.from_mongo(vendor)

# -------------------------
# Admin Endpoints
# -------------------------
@router.get("/vendors/pending", response_model=List[schemas.VendorOut])
async def list_pending_vendors(user=Depends(auth.require_role(["admin"])), db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    vendors_cursor = db["vendors"].find({"status": "pending"})
    vendors = []
    async for v in vendors_cursor:
        v["id"] = str(v["_id"])
        vendors.append(v)
    return vendors

@router.post("/vendors/{vendor_id}/approve")
async def approve_vendor(vendor_id: str, user=Depends(auth.require_role(["admin"])), db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    vendor = await db["vendors"].find_one({"_id": ObjectId(vendor_id)})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    await db["vendors"].update_one({"_id": ObjectId(vendor_id)}, {"$set": {"status": "approved"}})
    await db["users"].update_one({"_id": ObjectId(vendor["user_id"])}, {"$set": {"role": "vendor"}})

    # Get the updated user to create a new token
    updated_user = await db["users"].find_one({"_id": ObjectId(vendor["user_id"])})
    
    # Create new token with updated role
    new_token_data = {
        "sub": str(updated_user["_id"]),
        "role": updated_user.get("role", "vendor"),
        "email": updated_user.get("email")
    }
    new_token = auth.create_access_token(new_token_data)

    # Notify user
    if updated_user and updated_user.get("whatsapp"):
        asyncio.create_task(send_whatsapp(updated_user.get("whatsapp"), "Congratulations! Your vendor application has been approved."))

    return {
        "detail": f"Vendor {vendor_id} approved",
        "new_token": new_token  # Return the new token
    }

@router.post("/vendors/{vendor_id}/reject")
async def reject_vendor(vendor_id: str, user=Depends(auth.require_role(["admin"])), db: AsyncIOMotorDatabase = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    vendor = await db["vendors"].find_one({"_id": ObjectId(vendor_id)})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    await db["vendors"].update_one({"_id": ObjectId(vendor_id)}, {"$set": {"status": "rejected"}})
    user_doc = await db["users"].find_one({"_id": ObjectId(vendor["user_id"])})
    if user_doc and user_doc.get("whatsapp"):
        asyncio.create_task(send_whatsapp(user_doc.get("whatsapp"), "Your vendor application has been rejected. You can reapply later."))

    return {"detail": f"Vendor {vendor_id} rejected"}