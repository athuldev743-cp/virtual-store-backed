import requests
import json

# -------------------------------
# Signup data
# -------------------------------
signup_data = {
    "username": "testuser",
    "email": "testuser@gmail.com",
    "password": "Test@1234",
    "mobile": "9876543210",
    "address": "123 Main Street"
}

# -------------------------------
# API URL
# -------------------------------
url = "https://virtual-store-backed.onrender.com/api/users/signup"

# -------------------------------
# Send POST request
# -------------------------------
try:
    response = requests.post(url, json=signup_data)
    print(f"Status Code: {response.status_code}")
    
    try:
        print("Response JSON:", json.dumps(response.json(), indent=4))
    except Exception:
        print("Response Text:", response.text)

except requests.exceptions.RequestException as e:
    print("Request failed:", e)
