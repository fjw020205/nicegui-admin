"""认证与权限。

登录态存在 NiceGUI 的加密 cookie 里（app.storage.user），
权限 = 该用户所有角色绑定的菜单/按钮 perm 集合；超管拥有全部权限。
"""
from __future__ import annotations

from typing import Iterable

import bcrypt
from nicegui import app
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.models import Menu, Role, User

PUBLIC_PATHS = {'/login', '/favicon.ico'}
PUBLIC_PREFIXES = ('/_nicegui', '/_upload', '/static')


# ---------------------------------------------------------------- 密码
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------- 登录态
def login_user(user: User) -> None:
    app.storage.user.update(
        {
            'auth': True,
            'user_id': user.id,
            'username': user.username,
            'display_name': user.display_name,
        }
    )


def logout_user() -> None:
    app.storage.user.clear()


def is_logged_in() -> bool:
    return bool(app.storage.user.get('auth'))


def current_user(session: Session) -> User | None:
    """按 cookie 里的 user_id 取当前用户；用户被删/被禁用则视为未登录。"""
    user_id = app.storage.user.get('user_id')
    if not user_id:
        return None
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


# ---------------------------------------------------------------- 权限
def permissions_of(user: User) -> set[str]:
    if user.is_superuser:
        return {'*'}
    perms: set[str] = set()
    for role in user.roles:
        for menu in role.menus:
            if menu.perm:
                perms.add(menu.perm)
    return perms


def has_perm(user: User | None, perm: str) -> bool:
    if user is None:
        return False
    perms = permissions_of(user)
    return '*' in perms or perm in perms


def has_any(user: User | None, perms: Iterable[str]) -> bool:
    return any(has_perm(user, p) for p in perms)


def visible_menus(session: Session, user: User) -> list[Menu]:
    """当前用户可见的目录/页面菜单（按钮不参与导航）。"""
    stmt = (
        select(Menu)
        .where(Menu.visible.is_(True), Menu.type.in_(('dir', 'page')))
        .order_by(Menu.sort, Menu.id)
    )
    if not user.is_superuser:
        role_ids = [r.id for r in user.roles]
        if not role_ids:
            return []
        stmt = stmt.join(Menu.roles).where(Role.id.in_(role_ids)).distinct()
    return list(session.scalars(stmt).all())


# ---------------------------------------------------------------- 中间件
class AuthMiddleware(BaseHTTPMiddleware):
    """未登录访问任何页面 → 跳转 /login，并记住原地址。"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)
        if not app.storage.user.get('auth'):
            app.storage.user['referrer_path'] = path
            return RedirectResponse('/login')
        return await call_next(request)
