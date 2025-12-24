from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.mongo import connect_mongo, close_mongo, ping_mongo, create_indexes
from app.db.redis import connect_redis, close_redis, ping_redis
from app.routes.auth import router as auth_router
from app.routes.menu import router as menu_router

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# Include routers
app.include_router(auth_router)
app.include_router(menu_router)

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
    await create_indexes()


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
