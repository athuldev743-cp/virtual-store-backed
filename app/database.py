# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL is missing in environment")

client: AsyncIOMotorClient | None = None

async def connect_db():
    global client
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        await client.admin.command("ping")
        print("MongoDB connected ✅")
    except Exception as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")

def get_db():
    if not client:
        raise RuntimeError("Database not connected")
    return client["virtual_store"]

async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed ✅")
