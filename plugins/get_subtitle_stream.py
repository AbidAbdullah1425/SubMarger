import json
from plugins.ffmpeg import run_cmd
from config import LOGGER
import time

log = LOGGER("SubtitleExtractor")

async def get_subtitle_streams(video_path: str):
    log.info(f"Starting subtitle extraction for: {video_path}")
    start_time = time.time()

    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "s",
        "-show_entries", "stream=index,codec_name,tags",
        "-of", "json",
        video_path
    ]
    log.info(f"Running ffprobe command: {' '.join(cmd)}")

    rc, out, err = await run_cmd(cmd)
    elapsed = time.time() - start_time

    if rc != 0:
        log.error(f"ffprobe failed (rc={rc}, time={elapsed:.2f}s): {err}")
        return []

    log.info(f"ffprobe completed in {elapsed:.2f}s. RAW JSON:\n{out}")

    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        log.error(f"JSON decode error: {e}\nRaw output: {out}")
        return []

    streams = []
    for s in data.get("streams", []):
        tags = s.get("tags", {}) or {}
        stream_info = {
            "index": str(s.get("index")),
            "codec": s.get("codec_name", "unknown"),
            "lang": tags.get("language", "und"),
            "title": tags.get("title", "unknown")
        }
        log.info(f"Detected subtitle stream: {stream_info}")
        streams.append(stream_info)

    if not streams:
        log.warning("No subtitle streams found in video.")

    return streams