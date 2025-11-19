from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
import re
from bson import ObjectId
from datetime import datetime  # ✅ ADD THIS IMPORT

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
    mobile: Optional[str] = None       # ✅ replaced whatsapp with mobile
    address: Optional[str] = None      # ✅ new field
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
    mobile: Optional[str] = None       # ✅ replaced whatsapp with mobile
    address: Optional[str] = None      # ✅ new field
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
    whatsapp: Optional[str] = None
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_mongo(cls, vendor_dict):
        """Convert MongoDB document to VendorOut"""
        if not vendor_dict:
            return None
            
        # Convert ObjectId to string
        if '_id' in vendor_dict:
            vendor_dict = vendor_dict.copy()
            vendor_dict['id'] = str(vendor_dict['_id'])
            
        return cls(**vendor_dict)


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
    
    @classmethod
    def from_mongo(cls, product_dict):
        """Convert MongoDB document to ProductOut"""
        if not product_dict:
            return None
            
        # Convert ObjectId to string
        if '_id' in product_dict:
            product_dict = product_dict.copy()
            product_dict['id'] = str(product_dict['_id'])
        
        # Ensure stock is integer
        if 'stock' in product_dict and isinstance(product_dict['stock'], float):
            product_dict['stock'] = int(product_dict['stock'])
            
        return cls(**product_dict)


# -----------------------
# Order Schemas
# -----------------------
class OrderCreate(BaseModel):
    product_id: str
    quantity: float  # consistent with store.py
    mobile: Optional[str] = None
    address: Optional[str] = None
    payment_method: str  # ✅ ADD THIS LINE - "upi" or "cod"

    model_config = ConfigDict(from_attributes=True)

class OrderOut(BaseModel):
    id: str
    product_id: str
    customer_id: str
    vendor_id: str
    quantity: float
    total: float
    status: Optional[str] = "pending"
    payment_method: Optional[str] = None  # ✅ ADD THIS
    payment_status: Optional[str] = None  # ✅ ADD THIS
    remaining_stock: Optional[int] = None
    mobile: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=oid_str(doc.get("_id")),
            product_id=oid_str(doc.get("product_id")),
            customer_id=oid_str(doc.get("customer_id")),
            vendor_id=oid_str(doc.get("vendor_id")),
            quantity=doc.get("quantity"),
            total=doc.get("total"),
            status=doc.get("status", "pending"),
            payment_method=doc.get("payment_method"),  # ✅ ADD THIS
            payment_status=doc.get("payment_status"),  # ✅ ADD THIS
            remaining_stock=doc.get("remaining_stock"),
            mobile=doc.get("mobile"),
            address=doc.get("address"),
        )
# -----------------------
# Payment Schemas (ADD THIS SECTION)
# -----------------------

class UPIOrderCreate(BaseModel):
    """Schema for creating UPI payment order"""
    order_id: str
    amount: float
    customer_id: str

    model_config = ConfigDict(from_attributes=True)

class PaymentConfirm(BaseModel):
    """Schema for payment confirmation"""
    order_id: str
    amount: float
    transaction_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PaymentResponse(BaseModel):
    """Generic payment response"""
    success: bool
    message: str
    order_id: Optional[str] = None
    upi_link: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class UPIOrderOut(BaseModel):
    """Schema for UPI order response"""
    id: str
    order_id: str
    upi_order_id: str
    amount: float
    customer_id: str
    status: str
    upi_id: str
    store_name: str
    transaction_id: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=str(doc.get("_id")),
            order_id=doc.get("order_id"),
            upi_order_id=doc.get("upi_order_id"),
            amount=doc.get("amount"),
            customer_id=str(doc.get("customer_id")),
            status=doc.get("status", "pending"),
            upi_id=doc.get("upi_id"),
            store_name=doc.get("store_name"),
            transaction_id=doc.get("transaction_id"),
            created_at=doc.get("created_at"),
            paid_at=doc.get("paid_at")
        )