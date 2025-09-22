# app/schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
import re

# -----------------------
# User Schemas
# -----------------------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("password")
    def password_strength(cls, v):
        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$", v):
            raise ValueError(
                "Password must be 8+ chars, include upper, lower, number, special char"
            )
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(from_attributes=True)

class UserOut(BaseModel):
    id: str  # MongoDB ObjectId as string
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    whatsapp: Optional[str] = None
    role: str

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# Vendor Schemas
# -----------------------
class VendorApply(BaseModel):
    shop_name: str
    description: Optional[str] = None
    whatsapp: Optional[str] = None  # Only required when applying

    model_config = ConfigDict(from_attributes=True)

class VendorOut(BaseModel):
    id: str                # MongoDB ObjectId as string
    shop_name: str
    description: Optional[str] = None
    whatsapp: Optional[str] = None
    status: str  # pending, approved, rejected

    model_config = ConfigDict(from_attributes=True)


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
    id: str                # MongoDB ObjectId as string
    name: str
    description: Optional[str] = None
    price: float
    stock: int

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# Order Schemas
# -----------------------
class OrderCreate(BaseModel):
    product_id: str        # MongoDB ObjectId as string
    quantity: int

    model_config = ConfigDict(from_attributes=True)

class OrderOut(BaseModel):
    id: str                # MongoDB ObjectId as string
    product_id: str
    customer_id: str
    vendor_id: str
    quantity: int
    total_price: float
    status: str

    model_config = ConfigDict(from_attributes=True)
