from passlib.context import CryptContext

# Same bcrypt config as your backend
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Replace this with the password you want for admin
plain_password = "AdminPassword123!"

# Truncate to 72 characters (max for bcrypt)
truncated_password = plain_password[:72]

hashed_password = pwd_context.hash(truncated_password)
print("Hashed password:", hashed_password)
