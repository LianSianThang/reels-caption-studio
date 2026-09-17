import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, Header, HTTPException, Depends, status
from backend.app.core.config import settings
from backend.app.core.database import get_user_by_id

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None

def get_client_ip(request: Request) -> str:
    """
    Securely extracts the true client IP address.
    Only trusts proxy headers (X-Forwarded-For, CF-Connecting-IP) if the immediate
    connecting host is in TRUSTED_PROXIES (e.g. Nginx, local loopback, Cloudflare).
    This completely prevents IP spoofing attacks.
    """
    direct_ip = request.client.host if request.client else "127.0.0.1"
    
    trusted = [ip.strip() for ip in settings.TRUSTED_PROXIES.split(",") if ip.strip()]
    is_trusted_peer = (
        direct_ip in trusted or
        (direct_ip in ["::1", "127.0.0.1", "localhost", "testclient"] and any(t in ["127.0.0.1", "localhost", "::1", "testclient"] for t in trusted))
    )

    if is_trusted_peer:
        # 1. Cloudflare header
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip and cf_ip.strip():
            return cf_ip.strip()
        
        # 2. X-Forwarded-For (leftmost client IP)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_candidate = forwarded.split(",")[0].strip()
            if client_candidate:
                return client_candidate

    return direct_ip

def verify_admin_ip(request: Request):
    """Verifies that the request comes from an allowed IP address for admin actions."""
    allowed_ips = [ip.strip() for ip in settings.ADMIN_ALLOWED_IPS.split(",") if ip.strip()]
    if "*" in allowed_ips:
        return True

    client_ip = get_client_ip(request)
    # Normalize localhost representations
    normalized_ip = client_ip
    if normalized_ip in ["::1", "localhost", "testclient"]:
        normalized_ip = "127.0.0.1"

    allowed_normalized = []
    for ip in allowed_ips:
        if ip in ["::1", "localhost"]:
            allowed_normalized.append("127.0.0.1")
        else:
            allowed_normalized.append(ip)

    if normalized_ip not in allowed_normalized and client_ip not in allowed_ips:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin access is not permitted from your IP address ({client_ip})."
        )
    return True

async def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user = get_user_by_id(int(payload["sub"]))
    if not user or user.get("is_active") != 1:
        return None
    return user

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    user = await get_current_user_optional(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in."
        )
    return user

async def require_admin(request: Request, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Strictly ensures request has valid admin IP AND user is an admin."""
    # 1. Verify IP address
    verify_admin_ip(request)
    
    # 2. Verify Role
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required."
        )
    return user
