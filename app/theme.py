"""全局样式。所有资源本地化，不依赖任何 CDN（客户内网/断网也能用）。"""
from __future__ import annotations

from nicegui import ui

CSS = """
:root {
  --brand-1: #1e3a8a;
  --brand-2: #2563eb;
  --bg: #f4f6fb;
  --card-radius: 14px;
  --text-1: #1f2937;
  --text-2: #6b7280;
}
body {
  background: var(--bg);
  color: var(--text-1);
  font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
}
.nicegui-content { padding: 0 !important; }

/* ---------- 顶部栏 ---------- */
.app-header {
  background: linear-gradient(90deg, var(--brand-1), var(--brand-2));
  color: #fff;
  height: 58px;
  padding: 0 18px;
  box-shadow: 0 2px 10px rgba(37, 99, 235, .22);
}
.app-header .brand { font-size: 17px; font-weight: 700; letter-spacing: .5px; }

/* ---------- 侧边栏 ---------- */
.app-drawer {
  background: #fff !important;
  border-right: 1px solid #e8edf5;
  padding: 10px 8px;
  width: 222px !important;
}
.nav-link {
  border-radius: 10px;
  padding: 9px 12px;
  margin: 2px 0;
  color: #374151;
  cursor: pointer;
  transition: all .15s;
  font-size: 14px;
}
.nav-link:hover { background: #eef4ff; color: var(--brand-2); }
.nav-link.active {
  background: linear-gradient(90deg, #e8f0ff, #f3f7ff);
  color: var(--brand-2);
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--brand-2);
}
.nav-group { width: 100%; }
.nav-group .q-expansion-item__container { padding: 0; }
.nav-group .q-item { min-height: 38px; border-radius: 10px; }

/* ---------- 内容区 ---------- */
.app-content { padding: 18px; width: 100%; }
.page-title { font-size: 19px; font-weight: 700; margin-bottom: 2px; }
.page-sub { color: var(--text-2); font-size: 13px; }

/* ---------- 卡片 ---------- */
.soft-card {
  background: #fff;
  border-radius: var(--card-radius);
  box-shadow: 0 1px 3px rgba(16, 24, 40, .06), 0 1px 2px rgba(16, 24, 40, .04);
  border: 1px solid #eef1f6;
}
.stat-card { padding: 16px 18px; min-width: 170px; flex: 1 1 170px; }
.stat-value { font-size: 27px; font-weight: 700; line-height: 1.2; }
.stat-label { color: var(--text-2); font-size: 13px; }

/* ---------- 登录页 ---------- */
.login-wrap {
  min-height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #38bdf8 100%);
  padding: 16px;
}
.login-card {
  width: 380px;
  max-width: 100%;
  padding: 30px 28px;
  border-radius: 18px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, .28);
}

/* ---------- 表格：小屏横向滚动，不裁切列 ---------- */
.q-table__middle { overflow-x: auto; }

/* ---------- 响应式显隐 ----------
   注意：不要用 .mobile-only / .desktop-only 这两个类名，Quasar 自带同名类
   且断点是 600px，会和我们的 1024px 断点打架 */
.nav-toggle { display: none !important; }
.header-user-name { display: inline; }

/* ---------- 移动端 ---------- */
@media (max-width: 1023.98px) {
  /* Quasar 在小屏会把 q-drawer 变成带遮罩的浮层，这里改成纯 CSS 控制：
     不显示遮罩，未加 .open 时整个抽屉隐藏，由顶栏按钮切换 */
  .nav-toggle { display: inline-flex !important; }
  .header-user-name { display: none !important; }
  .q-drawer__backdrop { display: none !important; }
  .q-drawer--mobile:has(.app-drawer:not(.open)) { display: none !important; }
  .q-drawer--mobile:has(.app-drawer.open) {
    top: 58px !important;
    height: auto !important;
    box-shadow: 6px 0 24px rgba(15, 23, 42, .12);
  }
  .app-drawer { width: 240px !important; }
  .app-drawer:not(.open) { display: none !important; }
  .app-content { padding: 12px; }
  .stat-card { min-width: 130px; }
  .stat-value { font-size: 22px; }
}
"""


def inject_theme() -> None:
    ui.add_head_html(f'<style>{CSS}</style>')
    ui.colors(
        primary='#2563eb',
        secondary='#1e3a8a',
        accent='#0ea5e9',
        positive='#16a34a',
        negative='#dc2626',
        warning='#f59e0b',
        info='#0284c7',
    )
