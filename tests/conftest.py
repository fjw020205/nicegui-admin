"""测试环境准备：使用 tests/.tmp 下的临时数据目录，避免污染开发库。"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_TMP_DIR = Path(__file__).resolve().parent / '.tmp'
shutil.rmtree(_TMP_DIR, ignore_errors=True)
(_TMP_DIR / 'data').mkdir(parents=True, exist_ok=True)

# 必须在任何 app.* 导入之前设置，config.py 在导入时就会读这个变量
os.environ['APP_DATA_DIR'] = str(_TMP_DIR / 'data')
os.environ['APP_HEADLESS'] = '1'

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 只用 User 夹具，不引入 selenium（screen 夹具需要浏览器驱动）
pytest_plugins = ['nicegui.testing.user_plugin']  # noqa: F401

from nicegui.testing import User  # noqa: E402


async def login(user: User, username: str = 'admin', password: str = 'admin123') -> None:
    await user.open('/login')
    user.find('用户名').type(username)
    user.find('密码').type(password)
    user.find('登 录').click()
    await user.should_see('仪表盘')
