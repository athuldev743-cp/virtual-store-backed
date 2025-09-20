# app/models.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from bson import ObjectId

# -------------------------
# Helper for ObjectId
# -------------------------
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# -------------------------
# User Schemas
# -------------------------
class UserCreate(BaseModel):
    username: Optional[str]
    email: Optional[EmailStr]
    whatsapp: Optional[str]
    password: str

class UserOut(BaseModel):
    id: str
    username: Optional[str]
    email: Optional[EmailStr]
    whatsapp: Optional[str]
    role: str

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email: Optional[EmailStr]
    whatsapp: Optional[str]
    password: str

# -------------------------
# Vendor Schemas
# -------------------------
class VendorCreate(BaseModel):
    shop_name: str
    description: Optional[str]

class VendorOut(BaseModel):
    id: str
    user_id: str
    shop_name: str
    description: Optional[str]
    status: str

    class Config:
        orm_mode = True

# -------------------------
# Product Schemas
# -------------------------
class ProductCreate(BaseModel):
    name: str
    description: Optional[str]
    price: float
    stock: int

class ProductOut(ProductCreate):
    id: str
    vendor_id: str

    class Config:
        orm_mode = True

# -------------------------
# Order Schemas
# -------------------------
class OrderCreate(BaseModel):
    product_id: str
    quantity: int = 1

class OrderOut(BaseModel):
    id: str
    customer_id: str
    vendor_id: str
    product_id: str
    quantity: int
    total_price: float
    status: str
