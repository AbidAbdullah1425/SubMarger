import os
import gc
import shutil
import psutil
import subprocess
from config import LOGGER, DOWNLOAD_DIR

log = LOGGER("Cleanup")

async def cleanup_system(client=None, uid=None, paths=None, remove_dirs=True):
    """
    Safe async cleanup. Params kept to avoid touching callers:
      - client, uid: kept for compatibility (not required here)
      - paths: list of files/dirs to remove
      - remove_dirs: whether to try removing DOWNLOAD_DIR (if defined)
    Returns a small dict summary (useful for tests/logs).
    """
    paths = list(paths or [])
    log.info(f"Cleanup start. uid={uid} remove_dirs={remove_dirs} paths={paths}")

    removed = {"files": [], "dirs": []}
    # 1) remove provided paths (safe)
    for p in paths:
        try:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
                removed["dirs"].append(p)
                log.info(f"Deleted directory: {p}")
            elif os.path.exists(p):
                os.remove(p)
                removed["files"].append(p)
                log.info(f"Deleted file: {p}")
        except Exception as e:
            log.error(f"Failed to delete {p}: {e}")

    # 2) optionally remove global DOWNLOAD_DIR if allowed and exists
    if remove_dirs:
        try:
            dd = globals().get("DOWNLOAD_DIR")
            # safety: don't allow accidental root deletion
            if dd and isinstance(dd, str) and dd not in ("/", "") and os.path.exists(dd):
                shutil.rmtree(dd, ignore_errors=True)
                removed["dirs"].append(dd)
                log.info(f"Deleted DOWNLOAD_DIR: {dd}")
            else:
                log.debug("DOWNLOAD_DIR not set or unsafe to remove")
        except Exception as e:
            log.error(f"Failed to delete DOWNLOAD_DIR: {e}")

    # 3) kill stray ffmpeg/ffprobe processes only (case-insensitive contains)
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if "ffmpeg" in name or "ffprobe" in name:
                proc.kill()
                log.info(f"Killed process: {name} (PID: {proc.pid})")
        except Exception as e:
            log.debug(f"Could not handle process {proc}: {e}")

    # 4) collect garbage and give a short system snapshot
    try:
        gc.collect()
        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        disk = psutil.disk_usage("/")  # total, used, free
        log.info(f"Post-cleanup: cpu={cpu}%, mem={vm.percent}%, disk={disk.percent}%")
    except Exception as e:
        log.debug(f"Sys stats failed: {e}")

    # 5) attempt to clear FS caches safely (some environments are read-only)
    try:
        subprocess.run(["sync"], check=False)
        if os.path.exists("/proc/sys/vm/drop_caches") and os.access("/proc/sys/vm/drop_caches", os.W_OK):
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3\n")
            log.info("Requested kernel to drop caches")
        else:
            log.debug("/proc/sys/vm/drop_caches unavailable or not writable - skipping")
    except Exception as e:
        log.debug(f"Failed to drop caches: {e}")

    log.info("Cleanup finished.")
    return removed