# app/models.py
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
import re
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
# -----------------------
# Product Schemas
# -----------------------
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int

    model_config = ConfigDict(from_attributes=True)

class ProductOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    # Handle both float conversion and ObjectId conversion
    @field_validator('stock', 'id', mode='before')
    @classmethod
    def convert_types(cls, v, info):
        if info.field_name == 'stock' and isinstance(v, float):
            return int(v)
        if info.field_name == 'id' and isinstance(v, ObjectId):
            return str(v)
        return v

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=doc.get("_id"),
            name=doc.get("name"),
            description=doc.get("description"),
            price=doc.get("price"),
            stock=doc.get("stock"),
            image_url=doc.get("image_url")
        )


class OrderOut(BaseModel):
    id: str
    customer_id: str
    vendor_id: str
    product_id: str
    quantity: int
    total_price: float
    status: str

    model_config = ConfigDict(from_attributes=True)
