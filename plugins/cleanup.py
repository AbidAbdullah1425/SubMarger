import os
import gc
import shutil
import psutil
import subprocess
from config import LOGGER

log = LOGGER("Cleanup")

async def cleanup_system(client=None, uid=None, paths=None, remove_dirs=True):
    """Clean files, kill stray ffmpeg, free RAM."""
    paths = paths or []
    log.info(f"Starting cleanup. Remove dirs: {remove_dirs}, paths: {paths}")

    # Remove files/folders
    for p in paths:
        try:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
                log.info(f"Deleted directory: {p}")
            elif os.path.exists(p):
                os.remove(p)
                log.info(f"Deleted file: {p}")
        except Exception as e:
            log.error(f"Failed to delete {p}: {e}")

    # Remove download dirs by default
    if remove_dirs:
        try:
            if 'DOWNLOAD_DIR' in globals() and os.path.exists(DOWNLOAD_DIR):
                shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
                log.info(f"Deleted DOWNLOAD_DIR: {DOWNLOAD_DIR}")
            else:
                log.warning("DOWNLOAD_DIR not defined or does not exist")
        except Exception as e:
            log.error(f"Failed to delete DOWNLOAD_DIR: {e}")

    # Kill orphan ffmpeg/ffprobe processes
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"].lower()
            if "ffmpeg" in name or "ffprobe" in name:
                proc.kill()
                log.info(f"Killed process: {name} (PID: {proc.pid})")
        except Exception as e:
            log.error(f"Failed to kill process {proc}: {e}")

    # Force garbage collection
    gc.collect()
    log.info("Garbage collection done.")

    # Clear filesystem caches
    try:
        subprocess.run(["sync"], check=False)
        if os.path.exists("/proc/sys/vm/drop_caches"):
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3\n")
            log.info("Cleared filesystem caches")
    except Exception as e:
        log.error(f"Failed to clear filesystem caches: {e}")