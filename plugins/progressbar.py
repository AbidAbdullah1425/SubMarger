import time
from pyromod.listen import Client


# progress bar function
LAST_UPDATE_TIME = 0 # ignore 
async def progress_bar(current, total, start_time, message, status):
  global LAST_UPDATE_TIME
  CURRENT_TIME = time.time()
  DELAY = 3

  #add a delay to prevent flood wait
  if CURRENT_TIME - LAST_UPDATE_TIME < DELAY:
    return 
  LAST_UPDATE_TIME = CURRENT_TIME

  elapsed = time.time() - start_time 
  percent = (current / total) * 100 if total else 0 

  bar_length = 10 # EDIT TO CHANGE BAR NUMBERS
  filled_bar = int(bar_length * percent / 100) 

  bar = "▣" * filled_bar + "▢" * (bar_length - filled_bar) 

  speed = current / elapsed if elapsed > 0 else 0 # bytes per sec
  speed_in_mb = speed / (1024 * 1024) # mb per sec 

  eta = (total - current) / speed if speed > 0 else 0

  downloaded_in_mb = current / (1024 * 1024) # bytes to mb
  total_in_mb = total / (1024 * 1024) # bytes to mb 

  prog_text = (
        f"┌• {status} ~ {int(elapsed)}s\n"
        f"├• {bar}\n{percent:.2f}%\n"
        f"├• SIZE: {downloaded_in_mb:.2f} MB of {total_in_mb:.2f} MB\n"
        f"├• SPEED: {speed_in_mb:.2f} MB/s\n"
        f"└• ETA: {int(eta)}s"
    )
  await message.edit_text(prog_text)