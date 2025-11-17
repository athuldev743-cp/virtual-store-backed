from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils.razorpay import create_order, verify_payment   # FIXED IMPORT

router = APIRouter()

class CreateOrderRequest(BaseModel):
    amount: float  # amount in rupees

class VerifyRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str


@router.post("/create-order")
def create_order_route(data: CreateOrderRequest):
    try:
        order = create_order(data.amount)
        return {"order": order}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify")
def verify_payment_route(data: VerifyRequest):
    is_valid = verify_payment(
        data.order_id,
        data.payment_id,
        data.signature
    )
    return {"success": is_valid}
