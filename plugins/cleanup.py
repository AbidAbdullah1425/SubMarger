import os
import gc
import shutil
import psutil
import subprocess


    
def cleanup_system(paths=None, remove_dirs=True):
    """Clean files, kill stray ffmpeg, free RAM."""
    paths = paths or []

    # Remove files/folders
    for p in paths:
        try:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    # Remove download dirs by default
    if remove_dirs:
        try:
            shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
        except Exception:
            pass

    # Kill orphan ffmpeg/ffprobe processes
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"].lower()
            if "ffmpeg" in name or "ffprobe" in name:
                proc.kill()
        except Exception:
            pass

    # Force garbage collection
    gc.collect()

    # Clear filesystem caches
    try:
        subprocess.run(["sync"], check=False)
        if os.path.exists("/proc/sys/vm/drop_caches"):
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3\n")
    except Exception:
        pass