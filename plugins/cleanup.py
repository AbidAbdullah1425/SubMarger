import os, gc, shutil, psutil, subprocess

def cleanup_system(paths=None):
    """Clean files, kill stray ffmpeg, free RAM."""
    paths = paths or []
   
    for p in paths:
      try:
        if os.path.isdir(p):
          shutil.rmtree(p, ignore_errors=True)
          elif os.path.exists(p):
            os.remove(p)
        except Exception:
          pass

    # kill orphan ffmpeg/ffprobe
    for proc in psutil.process_iter(["name"]):
      try:
        name = proc.info["name"].lower()
          if "ffmpeg" in name or "ffprobe" in name:
            proc.kill()
        except Exception:
            pass

    gc.collect()

    try:
      subprocess.run(["sync"], check=False)
      if os.path.exists("/proc/sys/vm/drop_caches"):
        with open("/proc/sys/vm/drop_caches", "w") as f:
          f.write("3\n")
    except Exception:
      pass

