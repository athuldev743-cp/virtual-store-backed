from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional

# -----------------------
# User Schemas
# -----------------------
class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    whatsapp: Optional[str] = None
    password: str
    password_confirm: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("password")
    def password_strength(cls, v):
        import re
        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$", v):
            raise ValueError(
                "Password must be 8+ chars, include upper, lower, number, special char"
            )
        return v

    @field_validator("password_confirm")
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class UserLogin(BaseModel):
    email: Optional[EmailStr] = None
    whatsapp: Optional[str] = None
    password: str

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    whatsapp: Optional[str] = None
    role: str

    model_config = ConfigDict(from_attributes=True)


# JWT Token response schema
class Token(BaseModel):
    access_token: str
    token_type: str

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# Vendor Schemas
# -----------------------
class VendorCreate(BaseModel):
    shop_name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VendorOut(BaseModel):
    id: int
    shop_name: str
    description: Optional[str] = None
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
    id: int
    name: str
    description: Optional[str] = None
    price: float
    stock: int

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# Order Schemas
# -----------------------
class OrderCreate(BaseModel):
    product_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    product_id: int
    customer_id: int
    vendor_id: int
    quantity: int
    total_price: float
    status: str

    model_config = ConfigDict(from_attributes=True)
