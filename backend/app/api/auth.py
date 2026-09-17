from typing import Optional
import re
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel

from backend.app.core.database import (
    get_user_by_email,
    get_user_by_username,
    create_user,
    verify_password,
    update_user_last_login,
    update_user_keys,
    log_activity
)
from backend.app.core.security import create_access_token, get_current_user, get_client_ip
from backend.app.core.rate_limiter import auth_limiter, register_limiter

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateKeysRequest(BaseModel):
    gemini_key: Optional[str] = None
    groq_key: Optional[str] = None

EMAIL_REGEX = r"^[^@]+@[^@]+\.[^@]+$"

@router.post("/register")
def register_user(req: RegisterRequest, request: Request):
    client_ip = get_client_ip(request)

    # Anti-abuse registration rate limiting (max 5 accounts per hour per IP)
    limited, retry_after = register_limiter.is_limited(client_ip, max_requests=5, window_seconds=3600)
    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Registration limit reached from your IP. Please try again in {retry_after} seconds."
        )

    email = req.email.strip().lower()
    username = req.username.strip()
    if not re.match(EMAIL_REGEX, email):
        raise HTTPException(status_code=400, detail="Invalid email format.")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email is already registered.")
    if get_user_by_username(username):
        raise HTTPException(status_code=400, detail="Username is already taken.")

    user = create_user(
        username=username,
        email=email,
        password=req.password,
        role="user"
    )

    register_limiter.record(client_ip)
    log_activity(user["id"], "user_registered", f"New user {user['username']}")

    token = create_access_token({
        "sub": str(user["id"]),
        "username": user["username"],
        "email": user["email"],
        "role": user["role"]
    })

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "gemini_key": user["gemini_key"],
            "groq_key": user["groq_key"]
        }
    }

@router.post("/login")
def login_user(req: LoginRequest, request: Request):
    client_ip = get_client_ip(request)
    email = req.email.strip().lower()
    limit_key = f"user_login:{client_ip}:{email}"

    # Anti-brute-force rate limiting: max 5 failed attempts per 5 minutes
    limited, retry_after = auth_limiter.is_limited(limit_key, max_requests=5, window_seconds=300)
    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Access temporarily locked for {retry_after} seconds."
        )

    user = get_user_by_email(email)
    if not user or not verify_password(req.password, user["salt"], user["password_hash"]):
        auth_limiter.record(limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    # Strict isolation: Admin accounts are not allowed to log in via public user screen
    if user["role"] == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts cannot log in through the public user portal. Please access the dedicated Admin Portal."
        )

    if user.get("is_active") != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    # Reset failed attempts counter on successful login
    auth_limiter.reset(limit_key)
    update_user_last_login(user["id"])
    log_activity(user["id"], "user_login", "User logged in via public portal")

    token = create_access_token({
        "sub": str(user["id"]),
        "username": user["username"],
        "email": user["email"],
        "role": user["role"]
    })

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "gemini_key": user["gemini_key"],
            "groq_key": user["groq_key"]
        }
    }

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "role": current_user["role"],
        "gemini_key": current_user.get("gemini_key", ""),
        "groq_key": current_user.get("groq_key", ""),
        "created_at": current_user.get("created_at")
    }

@router.post("/update-keys")
def save_keys(req: UpdateKeysRequest, current_user: dict = Depends(get_current_user)):
    update_user_keys(current_user["id"], gemini_key=req.gemini_key, groq_key=req.groq_key)
    return {"status": "success", "message": "API keys saved to account."}
