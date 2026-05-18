"""
Database — MongoDB Connection
================================
Async MongoDB client using motor.
Connection string loaded from .env as MONGODB_URI.
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGODB_DB", "finchat")

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    """Called at app startup — creates the MongoDB connection."""
    global client, db
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    print(f"[DB] Connected to MongoDB — database: '{DATABASE_NAME}'")


async def close_db():
    """Called at app shutdown — closes the MongoDB connection."""
    global client
    if client:
        client.close()
        print("[DB] MongoDB connection closed.")


async def get_db():
    """FastAPI dependency — yields the live database instance."""
    from api.database import db as _db
    yield _db
