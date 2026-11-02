"""登录页。"""
from __future__ import annotations

from datetime import datetime

from nicegui import app, ui
from sqlalchemy import select

from app.auth import login_user, verify_password
from app.config import APP_NAME, APP_VERSION
from app.database import session_scope
from app.models import User
from app.theme import inject_theme


@ui.page('/login')
def login_page() -> None:
    inject_theme()
    if app.storage.user.get('auth'):
        ui.navigate.to('/')
        return

    def try_login() -> None:
        username = (username_input.value or '').strip()
        password = password_input.value or ''
        if not username or not password:
            ui.notify('请输入用户名和密码', type='warning')
            return

        with session_scope() as session:
            user = session.scalar(select(User).where(User.username == username))
            if user is None or not verify_password(password, user.password_hash):
                ui.notify('用户名或密码错误', type='negative')
                return
            if not user.is_active:
                ui.notify('该账号已被禁用，请联系管理员', type='negative')
                return
            user.last_login_at = datetime.now()

        login_user(user)
        target = app.storage.user.get('referrer_path') or '/'
        app.storage.user['referrer_path'] = None
        ui.navigate.to(target)

    with ui.column().classes('login-wrap'):
        with ui.card().classes('login-card'):
            with ui.column().classes('items-center w-full gap-1 mb-4'):
                ui.icon('hub').classes('text-5xl').style('color:#2563eb')
                ui.label(APP_NAME).classes('text-xl font-bold')
                ui.label('请使用管理员账号登录').classes('text-xs text-gray-400')

            username_input = (
                ui.input('用户名')
                .props('outlined dense autofocus')
                .classes('w-full')
            )
            password_input = (
                ui.input('密码', password=True, password_toggle_button=True)
                .props('outlined dense')
                .classes('w-full')
            )
            password_input.on('keydown.enter', try_login)

            ui.button('登 录', on_click=try_login).props('unelevated rounded').classes('w-full mt-2')
            ui.label(f'v{APP_VERSION}').classes('text-[11px] text-gray-300 w-full text-center mt-1')
