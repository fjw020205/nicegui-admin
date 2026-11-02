"""首次启动时初始化：默认角色、菜单树、管理员账号、演示账号。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from app.database import init_db, session_scope
from app.models import Menu, Role, User

# (name, type, path, icon, perm, sort, children)
DEFAULT_MENUS = [
    ('仪表盘', 'page', '/', 'dashboard', 'dashboard:view', 1, []),
    (
        '系统管理', 'dir', '', 'settings', '', 10,
        [
            (
                '用户管理', 'page', '/users', 'group', 'user:view', 11,
                [
                    ('新增用户', 'button', '', '', 'user:create', 1, []),
                    ('编辑用户', 'button', '', '', 'user:update', 2, []),
                    ('删除用户', 'button', '', '', 'user:delete', 3, []),
                    ('重置密码', 'button', '', '', 'user:reset', 4, []),
                ],
            ),
            (
                '角色管理', 'page', '/roles', 'manage_accounts', 'role:view', 12,
                [
                    ('新增角色', 'button', '', '', 'role:create', 1, []),
                    ('编辑角色', 'button', '', '', 'role:update', 2, []),
                    ('删除角色', 'button', '', '', 'role:delete', 3, []),
                    ('分配菜单', 'button', '', '', 'role:assign', 4, []),
                ],
            ),
            (
                '菜单管理', 'page', '/menus', 'account_tree', 'menu:view', 13,
                [
                    ('新增菜单', 'button', '', '', 'menu:create', 1, []),
                    ('编辑菜单', 'button', '', '', 'menu:update', 2, []),
                    ('删除菜单', 'button', '', '', 'menu:delete', 3, []),
                ],
            ),
        ],
    ),
]


def _build_menus(session: Session, nodes, parent_id: int | None = None) -> list[Menu]:
    created: list[Menu] = []
    for name, mtype, path, icon, perm, sort, children in nodes:
        menu = Menu(
            parent_id=parent_id,
            name=name,
            type=mtype,
            path=path,
            icon=icon,
            perm=perm,
            sort=sort,
            visible=True,
        )
        session.add(menu)
        session.flush()  # 拿到自增 id 给子节点用
        created.append(menu)
        if children:
            created.extend(_build_menus(session, children, menu.id))
    return created


def seed() -> None:
    init_db()
    with session_scope() as session:
        if session.scalar(select(func.count(User.id))):
            return  # 已经初始化过

        all_menus = _build_menus(session, DEFAULT_MENUS)

        admin_role = Role(name='超级管理员', code='admin', description='拥有系统全部权限', sort=1)
        user_role = Role(name='普通用户', code='user', description='只读演示角色', sort=2)
        session.add_all([admin_role, user_role])
        session.flush()

        admin_role.menus = list(all_menus)

        # 普通用户：仪表盘 + 用户管理（只读）
        allowed = {'dashboard:view', 'user:view'}
        user_menus = [m for m in all_menus if m.perm in allowed]
        # 把“系统管理”这个父目录也带上，否则导航里出不来
        parent_ids = {m.parent_id for m in user_menus if m.parent_id}
        user_menus += [m for m in all_menus if m.id in parent_ids and m not in user_menus]
        user_role.menus = user_menus

        admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            nickname='系统管理员',
            is_active=True,
            is_superuser=True,
            remark='内置超级管理员，请尽快修改密码',
        )
        admin.roles = [admin_role]

        demo = User(
            username='demo',
            password_hash=hash_password('demo123'),
            nickname='演示账号',
            is_active=True,
            remark='普通用户，只有只读权限',
        )
        demo.roles = [user_role]

        session.add_all([admin, demo])
