import os
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from backend.app.core.config import settings
from backend.app.core.database import (
    get_expired_media_files,
    mark_media_purged,
    purge_user_media_records,
    log_activity
)

class CleanupService:
    @staticmethod
    def cleanup_expired_files(hours: float = 12.0) -> Dict[str, Any]:
        """
        Deletes files older than `hours` (default: 12 hours) 
        from both database records and physical disk in uploads/ and outputs/.
        """
        deleted_count = 0
        reclaimed_bytes = 0
        cutoff_timestamp = time.time() - (hours * 3600)


        # 1. Check DB expired records
        expired_records = get_expired_media_files()
        purged_ids = []
        for rec in expired_records:
            purged_ids.append(rec["id"])
            file_path = Path(rec["file_path"])
            if file_path.exists():
                try:
                    reclaimed_bytes += file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"[Cleanup Error] Could not delete {file_path}: {e}")

            # Also clean companion files (mp3, srt, ass, burned) with same video_id
            vid = rec["video_id"]
            for folder in [settings.UPLOAD_DIR, settings.OUTPUT_DIR]:
                for comp_file in folder.glob(f"{vid}*"):
                    if comp_file.exists() and comp_file != file_path:
                        try:
                            reclaimed_bytes += comp_file.stat().st_size
                            comp_file.unlink()
                            deleted_count += 1
                        except Exception:
                            pass

        if purged_ids:
            mark_media_purged(purged_ids)

        # 2. File-system sweep for any orphaned files older than cutoff
        for target_dir in [settings.UPLOAD_DIR, settings.OUTPUT_DIR]:
            if not target_dir.exists():
                continue
            for entry in target_dir.rglob("*"):
                if entry.is_file() and not entry.name.startswith("demo_reel"):
                    try:
                        stat = entry.stat()
                        if stat.st_mtime < cutoff_timestamp:
                            reclaimed_bytes += stat.st_size
                            entry.unlink()
                            deleted_count += 1
                    except Exception:
                        pass

        # 3. Clean temporary HarfBuzz video slice chunks
        temp_slices_dir = settings.OUTPUT_DIR / "temp_slices"
        if temp_slices_dir.exists():
            for chunk in temp_slices_dir.glob("*.mp4"):
                try:
                    reclaimed_bytes += chunk.stat().st_size
                    chunk.unlink()
                    deleted_count += 1
                except Exception:
                    pass

        reclaimed_mb = round(reclaimed_bytes / (1024 * 1024), 2)
        log_activity(None, "auto_cleanup", f"Purged {deleted_count} files, freed {reclaimed_mb} MB")
        return {
            "deleted_count": deleted_count,
            "reclaimed_mb": reclaimed_mb
        }

    @staticmethod
    def cleanup_user_files(user_id: int) -> Dict[str, Any]:
        """Deletes all uploads, outputs, and intermediate files for a given user."""
        file_paths = purge_user_media_records(user_id)
        deleted_count = 0
        reclaimed_bytes = 0

        for p_str in file_paths:
            p = Path(p_str)
            if p.exists():
                try:
                    reclaimed_bytes += p.stat().st_size
                    p.unlink()
                    deleted_count += 1
                except Exception:
                    pass
            # Delete companions (srt, ass, burned, mp3)
            stem = p.stem.replace("_burned", "")
            for folder in [settings.UPLOAD_DIR, settings.OUTPUT_DIR]:
                for comp in folder.glob(f"{stem}*"):
                    if comp.exists() and comp != p:
                        try:
                            reclaimed_bytes += comp.stat().st_size
                            comp.unlink()
                            deleted_count += 1
                        except Exception:
                            pass

        reclaimed_mb = round(reclaimed_bytes / (1024 * 1024), 2)
        log_activity(user_id, "user_data_purge", f"Admin purged user {user_id} files, freed {reclaimed_mb} MB")
        return {
            "deleted_count": deleted_count,
            "reclaimed_mb": reclaimed_mb
        }

    @classmethod
    async def start_retention_worker(cls):
        """Background loop running every 1 hour to enforce the 12-hour file retention policy."""
        while True:
            try:
                res = cls.cleanup_expired_files(hours=float(settings.AUTO_CLEANUP_HOURS))
                if res["deleted_count"] > 0:
                    print(f"[12-Hour Retention Worker] Cleaned {res['deleted_count']} expired files, freed {res['reclaimed_mb']} MB.")
            except Exception as e:
                print(f"[12-Hour Retention Worker Error] {e}")
            # Wait 1 hour between sweeps
            await asyncio.sleep(3600)

