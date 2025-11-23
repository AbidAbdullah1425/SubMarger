import asyncio

async def run_cmd(cmd: list):
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    success = proc.returncode == 0
    return success, out.decode(), err.decode()






