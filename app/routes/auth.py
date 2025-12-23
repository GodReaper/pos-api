from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.models.user import UserLogin, TokenResponse, SeedAdminRequest, User
from app.services.auth_service import login_user, seed_admin
from app.core.rbac import get_current_user
from app.core.config import settings
from app.db.redis import redis_client
from typing import Optional

router = APIRouter(prefix="/auth", tags=["authentication"])


async def rate_limit_check(
    key: str,
    limit: int,
    window_seconds: int = 60
) -> bool:
    """Check rate limit using Redis"""
    if redis_client is None:
        # If Redis is not available, allow the request
        return True
    
    try:
        current = await redis_client.get(key)
        if current is None:
            await redis_client.setex(key, window_seconds, "1")
            return True
        
        count = int(current)
        if count >= limit:
            return False
        
        await redis_client.incr(key)
        return True
    except Exception:
        # If Redis fails, allow the request
        return True


async def check_login_rate_limit(request: Request, username: Optional[str] = None):
    """Check rate limits for login endpoint"""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Check per-IP limit (10/min)
    ip_key = f"rate_limit:login:ip:{client_ip}"
    if not await rate_limit_check(ip_key, limit=10, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts from this IP. Please try again later."
        )
    
    # Check per-username limit (5/min) if username provided
    if username:
        username_key = f"rate_limit:login:username:{username}"
        if not await rate_limit_check(username_key, limit=5, window_seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts for this username. Please try again later."
            )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request
):
    """Login endpoint with rate limiting"""
    # Check rate limits
    await check_login_rate_limit(request, username=credentials.username)
    
    # Attempt login
    token_data = await login_user(credentials.username, credentials.password)
    return TokenResponse(**token_data)


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user information"""
    return current_user


@router.post("/seed-admin", response_model=User, status_code=status.HTTP_201_CREATED)
async def seed_admin_user(
    admin_data: SeedAdminRequest,
    request: Request
):
    """Seed the first admin user (protected by SEED_ADMIN_KEY)"""
    # Check if SEED_ADMIN_KEY is configured
    if not settings.SEED_ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin seeding is not configured"
        )
    
    # Check for X-Seed-Key header
    seed_key = request.headers.get("X-Seed-Key")
    if not seed_key or seed_key != settings.SEED_ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing seed key"
        )
    
    # Create admin user
    admin_user = await seed_admin(admin_data.username, admin_data.password)
    return admin_user

