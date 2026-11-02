"""全局配置：路径、密钥、运行参数。

打包成 exe 后 BASE_DIR 指向 exe 所在目录，数据文件写在 exe 同级的 data/ 下，
绝对不能写进 sys._MEIPASS（PyInstaller 的临时解压目录，只读且每次启动都会变）。
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

APP_NAME = '云枢后台管理'
APP_VERSION = '0.1.0'
APP_DESCRIPTION = '基于 NiceGUI 的本地化后台管理系统'

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


BASE_DIR = base_dir()

DATA_DIR = Path(os.environ.get('APP_DATA_DIR') or (BASE_DIR / 'data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / 'app.db'
LOG_DIR = DATA_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _load_secret() -> str:
    """会话密钥：优先环境变量，其次 data/secret.key，没有就生成一份。

    必须持久化，否则每次重启所有登录态都会失效。
    """
    env = os.environ.get('APP_SECRET')
    if env:
        return env
    key_file = DATA_DIR / 'secret.key'
    if key_file.exists():
        value = key_file.read_text(encoding='utf-8').strip()
        if value:
            return value
    value = secrets.token_hex(32)
    key_file.write_text(value, encoding='utf-8')
    return value


STORAGE_SECRET = _load_secret()

HOST = os.environ.get('APP_HOST', '0.0.0.0')
PORT = int(os.environ.get('APP_PORT', '8080'))
# 1 = 不自动打开浏览器（局域网部署/服务器常驻时用）
HEADLESS = os.environ.get('APP_HEADLESS', '0') == '1'

DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'
