# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
from dotenv import load_dotenv
import certifi

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL environment variable is missing")

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None

async def connect_db():
    global client, db
    try:
        client = AsyncIOMotorClient(
            MONGO_URL,
            tls=True,                   # enable TLS/SSL
            tlsCAFile=certifi.where()   # ensure proper certificates
        )
        # Test connection
        await client.admin.command("ping")
        db = client.get_default_database()  # auto from URI
        print("MongoDB connected ✅")
    except Exception as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")

def get_db() -> AsyncIOMotorDatabase:
    if not db:
        raise RuntimeError("Database not connected")
    return db

async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed ✅")
