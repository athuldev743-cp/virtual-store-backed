# app/models.py

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

# -------------------------
# User table
# -------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)
    whatsapp = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=False)
    role = Column(String, default="Customer")

    vendors = relationship("Vendor", back_populates="user")
    orders = relationship("Order", back_populates="customer")


# -------------------------
# Vendor table
# -------------------------
class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    shop_name = Column(String)
    description = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected

    user = relationship("User", back_populates="vendors")
    products = relationship("Product", back_populates="vendor")
    orders = relationship("Order", back_populates="vendor")


# -------------------------
# Product table
# -------------------------
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    name = Column(String)
    description = Column(String, nullable=True)
    price = Column(Float)
    stock = Column(Integer)  # total available quantity

    vendor = relationship("Vendor", back_populates="products")
    orders = relationship("Order", back_populates="product")


# -------------------------
# Order table
# -------------------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    customer_id = Column(Integer, ForeignKey("users.id"))
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    quantity = Column(Integer, default=1)
    total_price = Column(Float)
    status = Column(String, default="pending")  # pending, completed, canceled
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="orders")
    customer = relationship("User", back_populates="orders")
    vendor = relationship("Vendor", back_populates="orders")
