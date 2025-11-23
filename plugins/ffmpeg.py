import asyncio
import time
from config import LOGGER

log = LOGGER("FFMPEG")

async def run_cmd(cmd: list):
    log.info(f"Running command: {' '.join(cmd)}")
    start_time = time.time()

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        rc = proc.returncode
        elapsed = time.time() - start_time

        log.info(f"Command finished in {elapsed:.2f}s with return code {rc}")
        if out:
            log.debug(f"stdout: {out.decode()}")
        if err:
            log.debug(f"stderr: {err.decode()}")

        success = rc == 0
        return success, out.decode(), err.decode()

    except Exception as e:
        elapsed = time.time() - start_time
        log.error(f"Failed to run command after {elapsed:.2f}s: {e}")
        return False, "", str(e)