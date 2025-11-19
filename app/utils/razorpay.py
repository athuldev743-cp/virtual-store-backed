import razorpay
import os
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Initialize Razorpay client
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_order(amount_in_rupees: float):
    """
    Create Razorpay order with UPI-friendly settings.
    """
    # Ensure amount is at least 1 INR (100 paise) for Razorpay
    if amount_in_rupees < 1:
        raise ValueError("Amount must be at least ₹1")
    
    amount = int(amount_in_rupees * 100)

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1,  # Auto-capture payment
        "notes": {
            "payment_method": "upi"  # Optional: Track UPI payments
        }
    })

    return order

def verify_payment(order_id, payment_id, signature):
    """
    Verify Razorpay signature with better error handling.
    """
    params = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature
    }

    try:
        client.utility.verify_payment_signature(params)
        return True
    except razorpay.errors.SignatureVerificationError as e:
        print(f"Signature verification failed: {e}")
        return False
    except Exception as e:
        print(f"Verification error: {e}")
        return False