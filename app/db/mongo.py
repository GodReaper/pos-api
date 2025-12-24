from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# MongoDB client
client: AsyncIOMotorClient = None
db = None


async def connect_mongo():
    """Create MongoDB connection"""
    global client, db
    try:
        client = AsyncIOMotorClient(settings.mongodb_connection_string)
        db = client[settings.MONGODB_DB_NAME]
        # Test connection immediately
        await client.admin.command("ping")
        print("MongoDB connection established successfully")
    except Exception as e:
        # Connection failed, but don't raise - let health checks handle it
        print(f"Warning: MongoDB connection failed: {e}")
        client = None
        db = None


async def close_mongo():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()


async def ping_mongo() -> bool:
    """Ping MongoDB to check connection"""
    try:
        if client is None:
            return False
        await client.admin.command("ping")
        return True
    except Exception:
        return False


async def create_indexes():
    """Create database indexes"""
    if db is None:
        return
    
    try:
        # Create indexes for menu_categories
        await db.menu_categories.create_index("sort_order")
        
        # Create indexes for menu_items
        await db.menu_items.create_index("category_id")
        
        print("Database indexes created successfully")
    except Exception as e:
        print(f"Warning: Failed to create indexes: {e}")
