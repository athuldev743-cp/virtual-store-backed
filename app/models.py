# app/models.py
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
import re
from bson import ObjectId

# -----------------------
# Helper function
# -----------------------
def oid_str(oid: ObjectId) -> Optional[str]:
    return str(oid) if oid else None

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

# -----------------------
# User Schemas
# -----------------------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    mobile: Optional[str] = None
    address: Optional[str] = None
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
    mobile: Optional[str] = None
    address: Optional[str] = None
    role: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=oid_str(doc.get("_id")),
            username=doc.get("username"),
            email=doc.get("email"),
            mobile=doc.get("mobile"),
            address=doc.get("address"),
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
        whatsapp = doc.get("whatsapp")
        if whatsapp and whatsapp.startswith("whatsapp:"):
            whatsapp = whatsapp.replace("whatsapp:", "")
        return cls(
            id=oid_str(doc.get("_id")),
            shop_name=doc.get("shop_name"),
            description=doc.get("description"),
            whatsapp=whatsapp,
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
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator('stock', mode='before')
    @classmethod
    def convert_float_to_int(cls, v):
        if v is None:
            return 0
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str) and v.replace('.', '').isdigit():
            return int(float(v))
        return v

    @classmethod
    def from_mongo(cls, doc):
        # Manual conversion before Pydantic sees the data
        stock = doc.get("stock")
        if isinstance(stock, float):
            stock = int(stock)
        
        return cls(
            id=str(doc.get("_id")),
            name=doc.get("name"),
            description=doc.get("description"),
            price=doc.get("price"),
            stock=stock,  # Already converted to int
            image_url=doc.get("image_url")
        )

# -----------------------
# Order Schemas
# -----------------------
class OrderCreate(BaseModel):
    product_id: str
    quantity: float
    mobile: Optional[str] = None
    address: Optional[str] = None
    payment_method: str  # "upi" or "cod"
    payment_status: Optional[str] = "pending"  # ✅ Add default value

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: str
    product_id: str
    customer_id: str
    vendor_id: str
    quantity: float
    total: float
    status: Optional[str] = "pending"
    remaining_stock: Optional[int] = None
    mobile: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_mongo(cls, doc):
        mobile = doc.get("mobile")
        if mobile and mobile.startswith("whatsapp:"):
            mobile = mobile.replace("whatsapp:", "")
        return cls(
            id=oid_str(doc.get("_id")),
            product_id=oid_str(doc.get("product_id")),
            customer_id=oid_str(doc.get("customer_id")),
            vendor_id=oid_str(doc.get("vendor_id")),
            quantity=doc.get("quantity"),
            total=doc.get("total"),
            status=doc.get("status", "pending"),
            remaining_stock=doc.get("remaining_stock"),
            mobile=mobile,
            address=doc.get("address"),
        )