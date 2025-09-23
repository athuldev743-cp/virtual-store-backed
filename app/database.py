# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL is missing in environment")

# Global client variable
client: AsyncIOMotorClient | None = None

# -------------------------
# Connect to MongoDB
# -------------------------
async def connect_db():
    global client
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        await client.admin.command("ping")
        print("MongoDB connected ✅")
    except Exception as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")

# -------------------------
# Dependency for FastAPI
# -------------------------
def get_db() -> AsyncIOMotorDatabase:
    """Return the virtual_store database instance for FastAPI dependencies"""
    if not client:
        raise RuntimeError("Database not connected")
    return client["virtual_store"]

# -------------------------
# Close MongoDB connection
# -------------------------
async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed ✅")
