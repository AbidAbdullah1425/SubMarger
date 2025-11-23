from ffmpeg import run_cmd



async def get_subtitle_streams(video_path: str):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "s",
        "-show_entries", "stream=index:stream_tags=language,title",
        "-of", "csv=p=0",
        video_path
    ]
    rc, out, err = await run_cmd(cmd)
    if rc != 0:
        return []
    streams = []
    for line in out.strip().splitlines():
        parts = line.split(',')
        if parts:
            streams.append({
                "index": parts[0],
                "lang": parts[1] if len(parts) > 1 else "ᴜɴᴅ",
                "title": parts[2] if len(parts) > 2 else "ᴜɴᴋɴᴏᴡɴ"
            })
    return streams