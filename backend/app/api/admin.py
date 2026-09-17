import httpx
import psutil
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel

from backend.app.core.config import settings, BASE_DIR
from backend.app.core.database import (
    get_user_by_email,
    get_user_by_id,
    verify_password,
    update_user_last_login,
    update_user_password,
    get_admin_system_stats,
    get_all_users_with_stats,
    delete_user_and_files,
    log_activity
)
from backend.app.core.security import (
    create_access_token,
    verify_admin_ip,
    require_admin,
    get_client_ip
)
from backend.app.core.rate_limiter import auth_limiter
from backend.app.services.cleanup_service import CleanupService

router = APIRouter(prefix="/admin", tags=["admin"])

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class ManualCleanupRequest(BaseModel):
    days: Optional[float] = None
    hours: Optional[float] = None


def get_directory_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return round(total / (1024 * 1024), 2)

class ChangeAdminPasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/login")
def admin_login(req: AdminLoginRequest, request: Request):
    """
    Dedicated Admin Login Portal.
    Restricted strictly to whitelisted IP addresses and admin role accounts with anti-brute-force rate limiting.
    """
    # 1. Enforce IP Whitelist
    verify_admin_ip(request)

    # 2. Enforce Brute-Force Rate Limiting (5 failed attempts per 5 minutes)
    client_ip = get_client_ip(request)
    limit_key = f"admin_login:{client_ip}:{req.email.strip().lower()}"
    limited, retry_after = auth_limiter.is_limited(limit_key, max_requests=5, window_seconds=300)
    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed admin login attempts. Access temporarily locked for {retry_after} seconds."
        )

    # 3. Verify Credentials
    user = get_user_by_email(req.email.strip().lower())
    if not user or not verify_password(req.password, user["salt"], user["password_hash"]):
        auth_limiter.record(limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials.")

    # 4. Verify Admin Role
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User account is not authorized for Admin Portal."
        )

    # Reset failed attempts counter
    auth_limiter.reset(limit_key)
    update_user_last_login(user["id"])
    log_activity(user["id"], "admin_login", "Admin logged in via dedicated portal")

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
            "role": user["role"]
        }
    }

@router.post("/change-password")
def change_admin_password(req: ChangeAdminPasswordRequest, admin_user: dict = Depends(require_admin)):
    """Allows administrator to securely change their password."""
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters long.")

    user = get_user_by_id(admin_user["id"])
    if not user or not verify_password(req.old_password, user["salt"], user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password incorrect.")

    update_user_password(admin_user["id"], req.new_password)
    log_activity(admin_user["id"], "admin_change_password", "Admin changed account password")
    return {"status": "success", "message": "Admin password updated successfully."}

@router.get("/stats")
def get_stats(admin_user: dict = Depends(require_admin)):
    """Provides high-level system, storage, and user metrics for admin dashboard."""
    db_stats = get_admin_system_stats()
    
    # Process & VPS Memory
    mem_info = psutil.Process().memory_info()
    sys_mem = psutil.virtual_memory()
    app_ram_mb = round(mem_info.rss / (1024 * 1024), 2)
    
    # Storage breakdown
    uploads_mb = get_directory_size_mb(settings.UPLOAD_DIR)
    outputs_mb = get_directory_size_mb(settings.OUTPUT_DIR)
    total_storage_mb = round(uploads_mb + outputs_mb, 2)

    return {
        "users": {
            "total": db_stats["total_users"],
            "regular": db_stats["total_regular_users"],
            "active_24h": db_stats["active_users_24h"]
        },
        "media": {
            "active_files_count": db_stats["active_media_count"],
            "database_tracked_mb": round(db_stats["active_media_bytes"] / (1024 * 1024), 2),
            "uploads_folder_mb": uploads_mb,
            "outputs_folder_mb": outputs_mb,
            "total_disk_mb": total_storage_mb
        },
        "vps_health": {
            "app_ram_mb": app_ram_mb,
            "total_system_ram_mb": round(sys_mem.total / (1024 * 1024), 2),
            "available_system_ram_mb": round(sys_mem.available / (1024 * 1024), 2),
            "is_1gb_vps_safe": app_ram_mb < 200
        },
        "retention_policy": {
            "auto_cleanup_hours": settings.AUTO_CLEANUP_HOURS,
            "status": "ACTIVE (Checks every 1h, purges files > 3 days old)"
        }
    }

@router.get("/users")
def list_users(admin_user: dict = Depends(require_admin)):
    """Returns directory of all users with video counts and storage usage."""
    users = get_all_users_with_stats()
    result = []
    for u in users:
        result.append({
            "id": u["id"],
            "username": u["username"],
            "email": u["email"],
            "role": u["role"],
            "created_at": u["created_at"],
            "last_login": u["last_login"],
            "is_active": u["is_active"],
            "total_videos": u["total_videos"],
            "total_mb_used": round(u["total_bytes_used"] / (1024 * 1024), 2)
        })
    return {"status": "success", "users": result}

@router.post("/cleanup")
def trigger_cleanup(req: ManualCleanupRequest, admin_user: dict = Depends(require_admin)):
    """Manually triggers purging of files older than specified hours or days."""
    res = CleanupService.cleanup_expired_files(hours=req.hours, days=req.days)
    label = f"{req.hours}h" if req.hours is not None else (f"{req.days} days" if req.days is not None else f"{settings.AUTO_CLEANUP_HOURS} hours")
    return {
        "status": "success",
        "message": f"Purged {res['deleted_count']} files older than {label}.",
        "deleted_count": res["deleted_count"],
        "reclaimed_mb": res["reclaimed_mb"]
    }


@router.post("/users/{user_id}/purge")
def purge_user_data(user_id: int, admin_user: dict = Depends(require_admin)):
    """Purges all files belonging to a specific user without deleting the user account."""
    res = CleanupService.cleanup_user_files(user_id)
    return {
        "status": "success",
        "message": f"Purged files for user {user_id}.",
        "deleted_count": res["deleted_count"],
        "reclaimed_mb": res["reclaimed_mb"]
    }

@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin_user: dict = Depends(require_admin)):
    """Deletes a user account and purges all their files."""
    if user_id == admin_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")

    file_paths = delete_user_and_files(user_id)
    for p_str in file_paths:
        p = Path(p_str)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    log_activity(admin_user["id"], "admin_delete_user", f"Admin deleted user {user_id}")
    return {"status": "success", "message": f"User {user_id} and associated files permanently deleted."}

class SetGeminiKeyRequest(BaseModel):
    gemini_key: str

@router.get("/gemini-key")
def get_admin_gemini_key(admin_user: dict = Depends(require_admin)):
    """Returns status and masked representation of the global Gemini API Key."""
    key = settings.GEMINI_API_KEY
    if not key:
        return {"configured": False, "masked_key": ""}
    masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "****"
    return {"configured": True, "masked_key": masked}

@router.post("/gemini-key")
async def update_global_gemini_key(req: SetGeminiKeyRequest, admin_user: dict = Depends(require_admin)):
    """Tests, verifies, and permanently updates the global Gemini API Key."""
    key = req.gemini_key.strip()
    if not key or len(key) < 15:
        raise HTTPException(status_code=400, detail="Invalid Gemini API key format.")

    # Test key against Google API
    test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(test_url)
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Gemini key verification failed: {r.text[:120]}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not connect to Gemini API: {e}")

    # Persist to .env
    env_file = BASE_DIR / ".env"
    content = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    lines = content.splitlines()
    new_lines = []
    replaced = False
    for l in lines:
        if l.startswith("GEMINI_API_KEY="):
            new_lines.append(f"GEMINI_API_KEY={key}")
            replaced = True
        else:
            new_lines.append(l)
    if not replaced:
        new_lines.append(f"GEMINI_API_KEY={key}")
    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    settings.GEMINI_API_KEY = key
    log_activity(admin_user["id"], "update_gemini_key", "Admin updated global Gemini API Key")

    return {
        "status": "success",
        "message": "Global Gemini API Key updated, verified, and saved to server.",
        "masked_key": f"{key[:8]}...{key[-4:]}"
    }
