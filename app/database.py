import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

# Global client and db variables
client: AsyncIOMotorClient | None = None
db = None

async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["real_estate_db"]
    print("MongoDB connected.")

async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")
