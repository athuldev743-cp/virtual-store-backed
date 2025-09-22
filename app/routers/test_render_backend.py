import requests

URL = "https://virtual-store-backed.onrender.com/api/users/signup"

data = {
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "Abc123!@"
}

try:
    response = requests.post(URL, json=data)
    print("Status Code:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
