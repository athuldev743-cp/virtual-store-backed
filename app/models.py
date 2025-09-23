# app/models.py
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from bson import ObjectId

# -------------------------
# Helper for ObjectId
# -------------------------
class PyObjectId(ObjectId):
    """Custom Pydantic type to handle MongoDB ObjectId"""
    
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

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: str
    username: Optional[str]
    email: Optional[EmailStr]
    whatsapp: Optional[str]
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: Optional[EmailStr]
    whatsapp: Optional[str]
    password: str

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Vendor Schemas
# -------------------------
class VendorCreate(BaseModel):
    shop_name: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class VendorOut(BaseModel):
    id: str
    user_id: str
    shop_name: str
    description: Optional[str]
    status: str

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Product Schemas
# -------------------------
class ProductCreate(BaseModel):
    name: str
    description: Optional[str]
    price: float
    stock: int

    model_config = ConfigDict(from_attributes=True)


class ProductOut(ProductCreate):
    id: str
    vendor_id: str

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Order Schemas
# -------------------------
class OrderCreate(BaseModel):
    product_id: str
    quantity: int = 1

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: str
    customer_id: str
    vendor_id: str
    product_id: str
    quantity: int
    total_price: float
    status: str

    model_config = ConfigDict(from_attributes=True)
