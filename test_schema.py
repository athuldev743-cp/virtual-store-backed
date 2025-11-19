# test_schema.py
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.schemas import OrderCreate
    print("‚úÖ Successfully imported OrderCreate")
    print("Ì≥ã OrderCreate fields:", list(OrderCreate.model_fields.keys()))
    print("Ì¥ç Has payment_method:", "payment_method" in OrderCreate.model_fields)
    
    # Test creating an instance
    test_data = {
        "product_id": "68d7f30a31ce26dbc602283e",
        "quantity": 1,
        "payment_method": "upi",
        "mobile": "9876543210", 
        "address": "Test Address"
    }
    
    order = OrderCreate(**test_data)
    print("‚úÖ Schema test passed!")
    print("Ì≥¶ Test order data:", order.model_dump())
    
except ImportError as e:
    print("‚ùå Import error:", e)
except Exception as e:
    print("‚ùå Schema test failed:", e)
