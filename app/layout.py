"""统一布局：顶栏 + 侧边菜单 + 内容区，以及权限校验辅助。"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from nicegui import ui

from app.auth import current_user, hash_password, has_perm, logout_user, verify_password, visible_menus
from app.config import APP_NAME, APP_VERSION
from app.database import session_scope
from app.models import Menu, User
from app.theme import inject_theme


def get_user() -> User | None:
    with session_scope() as session:
        return current_user(session)


def forbid(message: str = '你没有访问该页面的权限') -> None:
    """403 提示，替代直接抛异常。"""
    with ui.column().classes('app-content items-center justify-center').style('min-height:60vh'):
        ui.icon('block').classes('text-6xl text-gray-300')
        ui.label(message).classes('text-lg text-gray-500 mt-2')
        ui.button('返回首页', on_click=lambda: ui.navigate.to('/')).props('unelevated rounded')


def _nav_items(menus: list[Menu], active: str) -> None:
    children: dict[int | None, list[Menu]] = {}
    for m in menus:
        children.setdefault(m.parent_id, []).append(m)

    for root in children.get(None, []):
        subs = children.get(root.id, [])
        if subs:
            with ui.expansion(root.name, icon=root.icon or 'folder', value=True).classes('nav-group w-full'):
                for sub in subs:
                    cls = 'nav-link active' if sub.path == active else 'nav-link'
                    with ui.row().classes(f'{cls} items-center gap-2 w-full no-wrap').on(
                        'click', lambda p=sub.path: ui.navigate.to(p)
                    ):
                        if sub.icon:
                            ui.icon(sub.icon).classes('text-[18px]')
                        ui.label(sub.name).classes('text-sm')
        else:
            with ui.row().classes(f"{'nav-link active' if root.path == active else 'nav-link'} items-center gap-2 w-full no-wrap").on(
                'click', lambda p=root.path: ui.navigate.to(p)
            ):
                if root.icon:
                    ui.icon(root.icon).classes('text-[19px]')
                ui.label(root.name).classes('text-sm')


def _change_password_dialog(user: User) -> None:
    with ui.dialog() as dialog, ui.card().classes('w-96 max-w-full'):
        ui.label('修改密码').classes('text-base font-semibold')
        old = ui.input('当前密码', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')
        new = ui.input('新密码（至少 6 位）', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')
        confirm = ui.input('确认新密码', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')

        def submit() -> None:
            if not verify_password(old.value or '', user.password_hash):
                ui.notify('当前密码不正确', type='negative')
                return
            if len(new.value or '') < 6:
                ui.notify('新密码至少 6 位', type='warning')
                return
            if new.value != confirm.value:
                ui.notify('两次输入的新密码不一致', type='warning')
                return
            with session_scope() as session:
                db_user = session.get(User, user.id)
                db_user.password_hash = hash_password(new.value)
            ui.notify('密码已修改', type='positive')
            dialog.close()

        with ui.row().classes('w-full justify-end gap-2 mt-2'):
            ui.button('取消', on_click=dialog.close).props('flat')
            ui.button('确定', on_click=submit).props('unelevated')
    dialog.open()


@contextmanager
def shell(title: str = '', active: str = '', subtitle: str = '') -> Iterator[None]:
    """页面外壳。用法：

    with shell('用户管理', '/users'):
        ...页面内容...
    """
    inject_theme()
    with session_scope() as session:
        user = current_user(session)
        menus = visible_menus(session, user) if user else []

    if user is None:
        ui.navigate.to('/login')
        return

    def toggle_drawer() -> None:
        if 'open' in drawer.classes:
            drawer.classes(remove='open')
        else:
            drawer.classes(add='open')

    def do_logout() -> None:
        logout_user()
        ui.navigate.to('/login')

    with ui.left_drawer(value=True).classes('app-drawer') as drawer:
        _nav_items(menus, active)
        ui.element('div').classes('flex-grow')
        with ui.column().classes('w-full px-2 pb-1 gap-0'):
            ui.label(f'v{APP_VERSION}').classes('text-[11px] text-gray-400')

    with ui.header().classes('app-header'):
        ui.button(icon='menu', on_click=toggle_drawer).props('flat round dense color=white').classes('nav-toggle')
        ui.label(APP_NAME).classes('brand')
        ui.space()
        with ui.row().classes('items-center gap-1 no-wrap'):
            ui.icon('account_circle').classes('text-2xl')
            ui.label(user.display_name).classes('text-sm header-user-name')
            with ui.button(icon='expand_more').props('flat round dense color=white'):
                with ui.menu():
                    ui.menu_item('修改密码', on_click=lambda: _change_password_dialog(user))
                    ui.separator()
                    ui.menu_item('退出登录', on_click=do_logout)

    with ui.column().classes('app-content'):
        if title:
            with ui.row().classes('w-full items-end justify-between'):
                with ui.column().classes('gap-0'):
                    ui.label(title).classes('page-title')
                    if subtitle:
                        ui.label(subtitle).classes('page-sub')
        yield


def ensure_perm(perm: str, silent: bool = False) -> bool:
    """无权限时渲染 403 并返回 False。"""
    user = get_user()
    if has_perm(user, perm):
        return True
    if not silent:
        forbid()
    return False
