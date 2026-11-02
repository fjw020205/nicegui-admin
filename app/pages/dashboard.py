"""仪表盘：概览数字 + 最近登录。"""
from __future__ import annotations

from nicegui import ui
from sqlalchemy import func, select

from app.database import session_scope
from app.layout import ensure_perm, shell
from app.models import Menu, Role, User


@ui.page('/')
def dashboard_page() -> None:
    with shell('仪表盘', '/', '系统运行概览'):
        if not ensure_perm('dashboard:view'):
            return

        with session_scope() as session:
            user_count = session.scalar(select(func.count(User.id))) or 0
            role_count = session.scalar(select(func.count(Role.id))) or 0
            menu_count = session.scalar(select(func.count(Menu.id))) or 0
            active_count = session.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
            recent = session.scalars(
                select(User).order_by(User.last_login_at.desc().nullslast(), User.id).limit(8)
            ).all()
            recent_rows = [
                {
                    'id': u.id,
                    'username': u.username,
                    'nickname': u.display_name,
                    'roles': u.role_names,
                    'last_login': u.last_login_at.strftime('%Y-%m-%d %H:%M') if u.last_login_at else '从未登录',
                }
                for u in recent
            ]

        stats = [
            ('账号总数', user_count, 'group', '#2563eb'),
            ('启用账号', active_count, 'check_circle', '#16a34a'),
            ('角色数量', role_count, 'manage_accounts', '#f59e0b'),
            ('菜单/权限项', menu_count, 'account_tree', '#8b5cf6'),
        ]
        with ui.row().classes('w-full gap-3 mt-4'):
            for label, value, icon, color in stats:
                with ui.card().classes('soft-card stat-card'):
                    with ui.row().classes('w-full items-center justify-between no-wrap'):
                        with ui.column().classes('gap-0'):
                            ui.label(label).classes('stat-label')
                            ui.label(str(value)).classes('stat-value').style(f'color:{color}')
                        ui.icon(icon).classes('text-3xl').style(f'color:{color};opacity:.22')

        with ui.card().classes('soft-card w-full mt-4 p-4'):
            ui.label('最近登录').classes('text-base font-semibold mb-2')
            ui.table(
                columns=[
                    {'name': 'username', 'label': '用户名', 'field': 'username', 'align': 'left'},
                    {'name': 'nickname', 'label': '昵称', 'field': 'nickname', 'align': 'left'},
                    {'name': 'roles', 'label': '角色', 'field': 'roles', 'align': 'left'},
                    {'name': 'last_login', 'label': '最后登录', 'field': 'last_login', 'align': 'left'},
                ],
                rows=recent_rows,
                row_key='id',
                pagination=8,
            ).classes('w-full').props('flat')
