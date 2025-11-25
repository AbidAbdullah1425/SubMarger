import json
from plugins.ffmpeg import run_cmd
from config import LOGGER
import time

log = LOGGER("get_subtitle_stream.py")

async def get_subtitle_streams(video_path):
    log.info(f"[GET_SUBS] Checking: {video_path}")

    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "s",
        video_path
    ]
    log.info(f"[FFPROBE CMD] {' '.join(cmd)}")

    ok, out, err = await run_cmd(cmd)

    if not ok:
        log.error(f"[FFPROBE ERROR] {err}")
        return []

    # Log raw ffprobe result (important)
    log.info(f"[FFPROBE RAW] {out}")

    try:
        data = json.loads(out)
    except Exception as e:
        log.error(f"[JSON ERROR] {e}")
        return []

    streams = data.get("streams", [])
    log.info(f"[STREAMS FOUND] {len(streams)}")

    subs = []
    for s in streams:
        log.info(f"[STREAM META] {s}")  # full metadata for debugging

        subs.append({
            "index": str(len(subs)),
            "codec": s.get("codec_name", "unknown"),
            "lang": s.get("tags", {}).get("language", "und"),
            "title": s.get("tags", {}).get("title", "unknown")
        })

    log.info(f"[SUB RESULT] {subs}")
    return subs