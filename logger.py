import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import shutil

os.makedirs("logs", exist_ok=True)

handler = TimedRotatingFileHandler(
    filename="logs/app.log",
    when="midnight",
    encoding="utf-8",
)

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    "%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

def namer(default_name: str) -> str:
    # default_name: logs/app.log.YYYY-MM-DD
    date_str = default_name.rsplit(".", 1)[-1]  # YYYY-MM-DD
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return os.path.join("logs", dt.strftime("%Y-%m"), dt.strftime("%d.log"))

def rotator(source: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(source, dest)

handler.namer = namer
handler.rotator = rotator

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)
