import json
from plugins.ffmpeg import run_cmd
from config import LOGGER

log = LOGGER("SubtitleExtractor")


async def get_subtitle_streams(video_path: str):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "s",
        "-show_entries", "stream=index,codec_name,tags",
        "-of", "json",
        video_path
    ]

    rc, out, err = await run_cmd(cmd)

    if rc != 0:
        log.error(f"ffprobe failed: {err}")
        return []

    log.info(f"ffprobe RAW JSON:\n{out}")

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        log.error("Invalid JSON output from ffprobe")
        return []

    streams = []
    for s in data.get("streams", []):
        tags = s.get("tags", {}) or {}
        streams.append({
            "index": str(s.get("index")),
            "codec": s.get("codec_name", "unknown"),
            "lang": tags.get("language", "und"),
            "title": tags.get("title", "unknown")
        })

    return streams