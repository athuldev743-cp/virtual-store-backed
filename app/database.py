import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

# Create MongoDB client
client = AsyncIOMotorClient(MONGO_URL)

# Explicitly select the database
db = client["real_estate_db"]

# Example usage:
# await db["users"].insert_one({"name": "Test"})
