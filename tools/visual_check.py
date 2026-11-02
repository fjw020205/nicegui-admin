"""用系统自带 Edge 的无头模式做可视化验收（截图）。

用法：
    .venv\\Scripts\\python.exe tools\\visual_check.py
输出到 tools/shots/ 目录。
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from websockets.sync.client import connect

EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
PORT = 9333
BASE = 'http://127.0.0.1:8080'
SHOTS = Path(__file__).resolve().parent / 'shots'
SHOTS.mkdir(exist_ok=True)

FILL_JS = """
([index, value]) => {
  const el = document.querySelectorAll('.q-field input')[index];
  if (!el) return false;
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(el, value);
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
  return true;
}
"""

CLICK_JS = """
(text) => {
  const btn = [...document.querySelectorAll('button')].find(b => (b.innerText || '').includes(text));
  if (!btn) return false;
  btn.click();
  return true;
}
"""


class CDP:
    def __init__(self, ws_url: str) -> None:
        self.ws = connect(ws_url, max_size=80_000_000)
        self._id = 0

    def call(self, method: str, **params):
        self._id += 1
        self.ws.send(json.dumps({'id': self._id, 'method': method, 'params': params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get('id') == self._id:
                if 'error' in message:
                    raise RuntimeError(message['error'])
                return message.get('result', {})

    def eval(self, expression: str, arg=None):
        if arg is not None:
            expression = f'({expression})({json.dumps(arg)})'
        result = self.call('Runtime.evaluate', expression=expression, returnByValue=True, awaitPromise=True)
        return result.get('result', {}).get('value')

    def wait_for(self, expression: str, timeout: float = 10.0) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.eval(expression):
                    return True
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.2)
        return False

    def viewport(self, width: int, height: int, mobile: bool = False) -> None:
        self.call('Emulation.setDeviceMetricsOverride', width=width, height=height,
                  deviceScaleFactor=1, mobile=mobile)

    def goto(self, url: str) -> None:
        self.call('Page.navigate', url=url)
        time.sleep(0.6)

    def shot(self, name: str) -> None:
        data = self.call('Page.captureScreenshot', format='png').get('data', '')
        path = SHOTS / f'{name}.png'
        path.write_bytes(base64.b64decode(data))
        print(f'  saved {path.name} ({path.stat().st_size // 1024} KB)')


def wait_devtools(timeout: float = 25.0) -> str:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list', timeout=1) as response:
                tabs = json.load(response)
            for tab in tabs:
                if tab.get('type') == 'page':
                    return tab['webSocketDebuggerUrl']
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.3)
    raise RuntimeError('Edge DevTools 没有就绪')


def main() -> None:
    attach = '--attach' in sys.argv
    if attach:
        proc = None
        cdp = CDP(wait_devtools())
    else:
        profile = tempfile.mkdtemp(prefix='edge-visual-')
        log_path = Path(tempfile.gettempdir()) / 'edge-visual.log'
        log = open(log_path, 'w', encoding='utf-8', errors='replace')  # noqa: SIM115
        proc = subprocess.Popen(
            [EDGE, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
             '--no-sandbox', '--disable-dev-shm-usage', '--disable-extensions',
             f'--user-data-dir={profile}', f'--remote-debugging-port={PORT}', 'about:blank'],
            stdout=log, stderr=log,
        )
        try:
            cdp = CDP(wait_devtools())
        except RuntimeError:
            print('Edge 退出码:', proc.poll())
            print(log_path.read_text(encoding='utf-8', errors='replace')[-2000:])
            raise
    try:
        cdp.call('Page.enable')
        cdp.call('Runtime.enable')
        cdp.call('Network.enable')
        cdp.call('Network.clearBrowserCookies')

        # ---------- 桌面端
        cdp.viewport(1440, 900)
        cdp.goto(f'{BASE}/login')
        ok = cdp.wait_for("document.querySelectorAll('.q-field input').length >= 2")
        print('login rendered:', ok)
        time.sleep(1.2)
        cdp.shot('01-login')

        cdp.eval(FILL_JS, [0, 'admin'])
        cdp.eval(FILL_JS, [1, 'admin123'])
        time.sleep(0.3)
        print('clicked:', cdp.eval(CLICK_JS, '登 录'))
        cdp.wait_for("location.pathname === '/'")
        time.sleep(1.5)
        cdp.shot('02-dashboard')

        cdp.goto(f'{BASE}/users')
        cdp.wait_for("document.body.innerText.includes('新增用户')")
        time.sleep(1.0)
        cdp.shot('03-users')

        cdp.goto(f'{BASE}/roles')
        cdp.wait_for("document.body.innerText.includes('角色列表')")
        time.sleep(0.8)
        cdp.shot('04-roles')

        cdp.goto(f'{BASE}/menus')
        cdp.wait_for("document.body.innerText.includes('菜单树')")
        time.sleep(0.8)
        cdp.shot('05-menus')

        # ---------- 手机端
        cdp.viewport(390, 844, mobile=True)
        cdp.goto(f'{BASE}/users')
        cdp.wait_for("document.body.innerText.includes('用户管理')")
        time.sleep(1.0)
        cdp.shot('06-mobile-users')

        # 打开抽屉菜单
        cdp.eval("document.querySelector('.app-header button')?.click()")
        time.sleep(0.6)
        cdp.shot('07-mobile-drawer')
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == '__main__':
    sys.exit(main())
