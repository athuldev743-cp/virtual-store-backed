# hash_password.py
from passlib.context import CryptContext

# Same bcrypt config as your backend
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Replace this with the password you want for admin
plain_password = "AdminPassword123!"

hashed_password = pwd_context.hash(plain_password)
print("Hashed password:", hashed_password)
