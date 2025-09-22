# app/test_jwt.py
from app.auth import decode_access_token

# Replace with a real token from login/signup
token = "YOUR_JWT_HERE"

try:
    payload = decode_access_token(token)
    print("Token valid ✅")
    print(payload)
except Exception as e:
    print("Token invalid ❌", e)
