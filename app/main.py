from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.mongo import connect_mongo, close_mongo, ping_mongo
from app.db.redis import connect_redis, close_redis, ping_redis

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connections on startup"""
    await connect_mongo()
    await connect_redis()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    await close_mongo()
    await close_redis()


@app.get("/health")
def health():
    """Basic health check endpoint"""
    return {"ok": True}


@app.get("/health/redis")
async def health_redis():
    """Redis health check endpoint"""
    is_healthy = await ping_redis()
    return {"ok": is_healthy}


@app.get("/health/mongo")
async def health_mongo():
    """MongoDB health check endpoint"""
    is_healthy = await ping_mongo()
    return {"ok": is_healthy}
