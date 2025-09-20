import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URL = os.getenv("DATABASE_URL")

client = AsyncIOMotorClient(MONGO_URL)
db = client.get_default_database()  # or client['mydatabase']
