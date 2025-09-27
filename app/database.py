from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
from dotenv import load_dotenv
from typing import AsyncGenerator

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL missing in environment")

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None

async def connect_db() -> None:
    """Connect to MongoDB on startup"""
    global client, db
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client["virtual_store"]
        await db.command("ping")
        print("MongoDB connected ✅")
    except Exception as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")

async def close_db() -> None:
    """Close MongoDB connection"""
    global client
    if client is not None:  # FIXED: Changed from "if client:"
        client.close()
        print("MongoDB connection closed ✅")

# FastAPI dependency
async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Yield the database instance"""
    if db is None:  # FIXED: Changed from "if not db:"
        raise RuntimeError("Database not connected")
    yield db