import razorpay
import os
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Initialize Razorpay client with better configuration
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_order(amount_in_rupees: float):
    """
    Create Razorpay order with proper error handling.
    """
    try:
        # Validate amount
        if amount_in_rupees < 1:
            raise ValueError("Amount must be at least ₹1")
        
        amount = int(amount_in_rupees * 100)
        
        # Ensure amount is at least 100 paise (₹1)
        if amount < 100:
            amount = 100

        order_data = {
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1,  # Auto-capture payments
            "notes": {
                "integration": "fastapi_react"
            }
        }

        print(f"Creating order with data: {order_data}")  # Debug log
        
        order = client.order.create(order_data)
        print(f"Order created: {order}")  # Debug log
        
        return order
        
    except razorpay.errors.BadRequestError as e:
        print(f"Razorpay BadRequestError: {e}")
        raise Exception(f"Payment error: {str(e)}")
    except Exception as e:
        print(f"Error creating order: {e}")
        raise Exception(f"Failed to create payment order: {str(e)}")

def verify_payment(order_id, payment_id, signature):
    """
    Verify Razorpay signature with comprehensive error handling.
    """
    try:
        # Validate inputs
        if not all([order_id, payment_id, signature]):
            return False
            
        params = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        print(f"Verifying payment with params: {params}")  # Debug log
        
        client.utility.verify_payment_signature(params)
        print("Payment verification successful")
        return True
        
    except razorpay.errors.SignatureVerificationError as e:
        print(f"Signature verification failed: {e}")
        return False
    except Exception as e:
        print(f"Verification error: {e}")
        return False