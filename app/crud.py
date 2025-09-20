from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------------
# User
# -------------------------
def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email.lower() if user.email else None,
        whatsapp=user.whatsapp,
        password=hashed_password,
        role="Customer"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_whatsapp(db: Session, whatsapp: str):
    return db.query(models.User).filter(models.User.whatsapp == whatsapp).first()


# -------------------------
# Vendor
# -------------------------
def apply_vendor(db: Session, user: models.User, vendor_data: schemas.VendorCreate):
    # Create vendor request
    db_vendor = models.Vendor(
        user_id=user.id,
        shop_name=vendor_data.shop_name,
        description=vendor_data.description,
        status="pending"
    )
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor, "Vendor application submitted"


# -------------------------
# Product
# -------------------------
def create_product(db: Session, product: schemas.ProductCreate, vendor_id: int):
    db_product = models.Product(**product.model_dump(), vendor_id=vendor_id)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


# -------------------------
# Order
# -------------------------
def create_order(db: Session, customer: models.User, product_id: int, quantity: int = 1):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return None, "Product not found"
    if product.stock < quantity:
        return None, "Not enough stock"

    product.stock -= quantity
    db.commit()
    db.refresh(product)

    vendor = db.query(models.Vendor).filter(models.Vendor.id == product.vendor_id).first()
    total_price = product.price * quantity

    order = models.Order(
        product_id=product.id,
        customer_id=customer.id,
        vendor_id=vendor.id,
        quantity=quantity,
        total_price=total_price
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return order, "Order placed successfully"


# -------------------------
# List products
# -------------------------
def list_products(db: Session):
    return db.query(models.Product).all()
