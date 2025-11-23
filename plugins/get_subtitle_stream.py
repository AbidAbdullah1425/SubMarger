import json
from plugins.ffmpeg import run_cmd


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
        return []

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []

    streams = []
    for s in data.get("streams", []):
        streams.append({
            "index": str(s.get("index")),
            "codec": s.get("codec_name", "unknown"),
            "lang": s.get("tags", {}).get("language", "und"),
            "title": s.get("tags", {}).get("title", "unknown")
        })

    return streams