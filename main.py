"""程序入口：初始化数据库 → 注册页面 → 启动本地服务。

开发运行:  python main.py
打包运行:  双击 dist/云枢后台管理/云枢后台管理.exe
"""
from __future__ import annotations

import logging
import os
import socket
import sys

from nicegui import app, ui

from app import config
from app.auth import AuthMiddleware
from app.database import init_db
from app.pages import dashboard, login, menus, roles, users  # noqa: F401  导入即注册页面
from app.seed import seed


def setup_logging(stream_redirected: bool = False) -> None:
    handlers: list[logging.Handler] = [
        logging.FileHandler(config.LOG_DIR / 'app.log', encoding='utf-8'),
    ]
    if not stream_redirected:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=handlers,
    )


def ensure_std_streams() -> bool:
    """打包成 --windowed exe 后 sys.stdout / sys.stderr 是 None。

    uvicorn、logging 等库会直接写这两个流，None 会导致启动阶段静默失败
    （进程还活着但永远不起来），所以这里兜底重定向到文件。
    返回 True 表示做了重定向。
    """
    if sys.stdout is not None and sys.stderr is not None:
        return False
    stream = open(  # noqa: SIM115  进程级常量，不需要关闭
        config.LOG_DIR / 'stdout.log', 'a', encoding='utf-8', buffering=1
    )
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    return True


def pick_port(host: str, start: int) -> int:
    """端口被占用时自动往后找，避免客户重复双击启动失败。"""
    for port in range(start, start + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f'端口 {start}-{start + 30} 都被占用，请关闭其它程序后重试')


def lan_addresses() -> list[str]:
    addresses: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith('127.') and ip not in addresses:
                addresses.append(ip)
    except OSError:
        pass
    return addresses


def main() -> None:
    redirected = ensure_std_streams()
    setup_logging(redirected)
    seed()

    app.add_middleware(AuthMiddleware)

    port = pick_port(config.HOST, config.PORT)
    local_url = f'http://127.0.0.1:{port}'

    banner = [
        '=' * 62,
        f'  {config.APP_NAME}  v{config.APP_VERSION}',
        f'  本机访问: {local_url}',
        *[f'  手机/局域网访问: http://{ip}:{port}' for ip in lan_addresses()],
        f'  数据目录: {config.DATA_DIR}',
        '  默认账号: admin / admin123  (首次登录后请立即修改)',
        '=' * 62,
    ]
    for line in banner:
        logging.info(line)
        try:
            print(line)  # 无控制台的 windowed exe 下 stdout 为 None，不能直接 print
        except Exception:  # noqa: BLE001
            pass

    ui.run(
        host=config.HOST,
        port=port,
        title=config.APP_NAME,
        favicon='🧭',
        language='zh-CN',
        storage_secret=config.STORAGE_SECRET,
        reload=False,
        show=not config.HEADLESS,
        native=os.environ.get('APP_NATIVE', '0') == '1',
        uvicorn_logging_level='warning',
    )


if __name__ in {'__main__', '__mp_main__'}:
    main()
