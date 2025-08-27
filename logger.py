import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

# 自定义日志路径：logs/YYYY-MM/DD.log
def get_log_path():
    now = datetime.now()
    folder = now.strftime("logs/%Y-%m")   # 按月份建文件夹
    os.makedirs(folder, exist_ok=True)
    file = now.strftime("%d.log")         # 按日存文件
    return os.path.join(folder, file)

log_path = get_log_path()

# 设置 handler（每天一个文件）
handler = TimedRotatingFileHandler(
    filename=log_path,
    when="midnight",  # 每天切分
    interval=1,
    backupCount=7,    # 保留多少天的日志
    encoding="utf-8"
)

# 设置日志格式
formatter = logging.Formatter(
    fmt="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

# 配置 root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)
