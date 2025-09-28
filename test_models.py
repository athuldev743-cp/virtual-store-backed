# test_model.py
from app.models import ProductOut

# Test with the exact problematic value
test_data = {
    "id": "123",
    "name": "Test Product",
    "price": 10.99,
    "stock": 3898792.5,  # Float value that was causing error
    "image_url": None
}

try:
    product = ProductOut(**test_data)
    print("✅ SUCCESS: Model accepted float stock value")
    print(f"Stock value: {product.stock} (type: {type(product.stock)})")
except Exception as e:
    print("❌ ERROR: Model rejected float stock value")
    print(f"Error: {e}")