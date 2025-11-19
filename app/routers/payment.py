from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils.razorpay import create_order, verify_payment
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class CreateOrderRequest(BaseModel):
    amount_in_rupees: float

class VerifyRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str

@router.post("/create-order")
def create_order_route(data: CreateOrderRequest):
    try:
        logger.info(f"Creating order for amount: {data.amount_in_rupees}")
        order = create_order(data.amount_in_rupees)
        return order   
    except Exception as e:
        logger.error(f"Order creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-payment")
def verify_payment_route(data: VerifyRequest):
    try:
        logger.info(f"Verifying payment for order: {data.order_id}")
        is_valid = verify_payment(
            data.order_id,
            data.payment_id,
            data.signature
        )
        return {"success": is_valid}
    except Exception as e:
        logger.error(f"Payment verification failed: {str(e)}")
        return {"success": False, "error": str(e)}