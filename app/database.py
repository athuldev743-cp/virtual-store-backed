# app/database.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL environment variable is missing")

client: AsyncIOMotorClient | None = None
db = None

async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["real_estate_db"]
    try:
        # Test connection
        await client.admin.command("ping")
        print("MongoDB connected ✅")
    except Exception as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")

async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed ✅")
