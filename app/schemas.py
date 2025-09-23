# app/schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
import re
from bson import ObjectId

# -----------------------
# Helper function
# -----------------------
def oid_str(oid: ObjectId) -> Optional[str]:
    return str(oid) if oid else None

# -----------------------
# User Schemas
# -----------------------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    whatsapp: Optional[str] = None
    password: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("password")
    def password_strength(cls, v):
        if not re.match(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", v
        ):
            raise ValueError(
                "Password must be at least 8 chars, include upper, lower, number, and special char"
            )
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: str
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=oid_str(doc.get("_id")),
            username=doc.get("username"),
            email=doc.get("email"),
            role=doc.get("role")
        )


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
    whatsapp: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VendorOut(BaseModel):
    id: str
    shop_name: str
    description: Optional[str] = None
    whatsapp: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=oid_str(doc.get("_id")),
            shop_name=doc.get("shop_name"),
            description=doc.get("description"),
            whatsapp=doc.get("whatsapp"),
            status=doc.get("status"),
        )

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

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=oid_str(doc.get("_id")),
            name=doc.get("name"),
            description=doc.get("description"),
            price=doc.get("price"),
            stock=doc.get("stock"),
        )

# -----------------------
# Order Schemas
# -----------------------
class OrderCreate(BaseModel):
    product_id: str
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: str
    product_id: str
    customer_id: str
    vendor_id: str
    quantity: int
    total_price: float
    status: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=oid_str(doc.get("_id")),
            product_id=oid_str(doc.get("product_id")),
            customer_id=oid_str(doc.get("customer_id")),
            vendor_id=oid_str(doc.get("vendor_id")),
            quantity=doc.get("quantity"),
            total_price=doc.get("total_price"),
            status=doc.get("status"),
        )
