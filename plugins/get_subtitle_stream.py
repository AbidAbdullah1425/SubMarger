from plugins.ffmpeg import run_cmd



async def get_subtitle_streams(video_path: str):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "s",
        "-show_entries", "stream=index:codec_name:tags",
        "-of", "json",
        video_path
    ]
    rc, out, err = await run_cmd(cmd)
    if rc != 0:
        return []

    import json
    streams = []
    try:
        data = json.loads(out)
        for s in data.get("streams", []):
            streams.append({
                "index": str(s.get("index")),
                "codec": s.get("codec_name", "unknown"),
                "lang": s.get("tags", {}).get("language", "ᴜɴᴅ"),
                "title": s.get("tags", {}).get("title", "ᴜɴᴋɴᴏᴡɴ")
            })
    except Exception:
        return []

    return streams