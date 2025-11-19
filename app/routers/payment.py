from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import os
from typing import Optional

from app.database import get_db
from app.schemas import (
    UPIOrderCreate, 
    PaymentConfirm, 
    PaymentResponse, 
    UPIOrderOut,
    OrderCreate,
    OrderOut
)

router = APIRouter()

# Get environment variables
UPI_ID = os.getenv("UPI_ID", "yourupi@bank")
STORE_NAME = os.getenv("STORE_NAME", "Virtual Store")

@router.post("/upi/create", response_model=PaymentResponse)
async def create_upi_payment(
    order_data: UPIOrderCreate, 
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create a UPI payment order"""
    try:
        # Verify the main order exists
        main_order = await db.orders.find_one({"_id": ObjectId(order_data.order_id)})
        if not main_order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Generate unique UPI order ID
        upi_order_id = f"UPI{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create UPI order document
        upi_order = {
            "order_id": order_data.order_id,
            "upi_order_id": upi_order_id,
            "amount": order_data.amount,
            "customer_id": ObjectId(order_data.customer_id),
            "status": "pending",
            "upi_id": UPI_ID,
            "store_name": STORE_NAME,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Insert into database
        result = await db.upi_orders.insert_one(upi_order)
        
        # Generate UPI payment link
        encoded_store_name = STORE_NAME.replace(" ", "%20")
        upi_link = f"upi://pay?pa={UPI_ID}&pn={encoded_store_name}&am={order_data.amount:.2f}&cu=INR&tn=Order {order_data.order_id}"
        
        return PaymentResponse(
            success=True,
            message="UPI payment order created successfully",
            order_id=order_data.order_id,
            upi_link=upi_link
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {str(e)}")

@router.post("/upi/confirm", response_model=PaymentResponse)
async def confirm_upi_payment(
    confirm_data: PaymentConfirm, 
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Confirm UPI payment after user clicks 'I Paid'"""
    try:
        # Find the UPI order
        upi_order = await db.upi_orders.find_one({"order_id": confirm_data.order_id})
        if not upi_order:
            raise HTTPException(status_code=404, detail="UPI order not found")
        
        # Verify amount matches
        if upi_order["amount"] != confirm_data.amount:
            raise HTTPException(status_code=400, detail="Amount mismatch")
        
        # Update UPI order status
        await db.upi_orders.update_one(
            {"order_id": confirm_data.order_id},
            {
                "$set": {
                    "status": "paid",
                    "transaction_id": confirm_data.transaction_id,
                    "paid_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        
        # Update main order payment status
        await db.orders.update_one(
            {"_id": ObjectId(confirm_data.order_id)},
            {
                "$set": {
                    "payment_status": "paid",
                    "status": "confirmed",
                    "updated_at": datetime.now()
                }
            }
        )
        
        return PaymentResponse(
            success=True,
            message="Payment confirmed successfully",
            order_id=confirm_data.order_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment confirmation failed: {str(e)}")

@router.get("/upi/order/{order_id}", response_model=UPIOrderOut)
async def get_upi_order_status(
    order_id: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get UPI order status"""
    try:
        upi_order = await db.upi_orders.find_one({"order_id": order_id})
        if not upi_order:
            raise HTTPException(status_code=404, detail="UPI order not found")
        
        return UPIOrderOut.from_mongo(upi_order)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order status: {str(e)}")

@router.get("/upi/orders/user/{user_id}")
async def get_user_upi_orders(
    user_id: str, 
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all UPI orders for a user"""
    try:
        upi_orders = await db.upi_orders.find(
            {"customer_id": ObjectId(user_id)}
        ).sort("created_at", -1).to_list(length=50)
        
        return [UPIOrderOut.from_mongo(order) for order in upi_orders]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user orders: {str(e)}")