"""冒烟测试：登录、权限、列表数据、新增用户闭环。

运行：.venv\\Scripts\\python.exe -m pytest
"""
from __future__ import annotations

import asyncio
import uuid

from nicegui import ui
from nicegui.testing import User

from .conftest import login


def table_rows(user: User) -> list[dict]:
    """读取页面上最新的表格行数据。

    表格内容由前端渲染，只能从组件属性里取；刷新后旧元素仍留在客户端注册表里，
    所以按 id 取最新的那个。
    """
    tables = sorted(user.find(ui.table).elements, key=lambda element: element.id)
    assert tables, '页面上没有找到表格'
    return list(tables[-1].props.get('rows', []))


async def test_login_page_renders(user: User) -> None:
    await user.open('/login')
    await user.should_see('云枢后台管理')
    await user.should_see('用户名')
    await user.should_see('登 录')


async def test_wrong_password_shows_error(user: User) -> None:
    await user.open('/login')
    user.find('用户名').type('admin')
    user.find('密码').type('wrong-password')
    user.find('登 录').click()
    await user.should_see('用户名或密码错误')


async def test_admin_login_and_dashboard(user: User) -> None:
    await login(user)
    await user.should_see('账号总数')
    await user.should_see('最近登录')


async def test_users_page(user: User) -> None:
    await login(user)
    await user.open('/users')
    await user.should_see('用户管理')
    await user.should_see('新增用户')
    usernames = [r['username'] for r in table_rows(user)]
    assert 'admin' in usernames
    assert 'demo' in usernames


async def test_create_user(user: User) -> None:
    await login(user)
    await user.open('/users')
    name = f'tester_{uuid.uuid4().hex[:6]}'
    user.find('新增用户').click()
    user.find('用户名 *').type(name)
    user.find('密码 *').type('tester123')
    user.find('保存').click()
    # refresh() 是后台任务（fire-and-forget），等它执行完再断言
    await asyncio.sleep(0.2)

    usernames = [r['username'] for r in table_rows(user)]
    assert name in usernames, f'新增用户后列表里没有 {name}'


async def test_menus_page(user: User) -> None:
    await login(user)
    await user.open('/menus')
    await user.should_see('菜单树')
    names = [r['name'] for r in table_rows(user)]
    assert any('系统管理' in n for n in names)
    perms = [r['perm'] for r in table_rows(user)]
    assert 'user:create' in perms


async def test_roles_page(user: User) -> None:
    await login(user)
    await user.open('/roles')
    await user.should_see('角色列表')
    role_names = [r['name'] for r in table_rows(user)]
    assert '超级管理员' in role_names


async def test_normal_user_has_no_create_button(user: User) -> None:
    """demo 只有只读权限：能看列表，但新增按钮不应渲染。"""
    await login(user, 'demo', 'demo123')
    await user.open('/users')
    await user.should_see('用户管理')
    await user.should_not_see('新增用户')


async def test_anonymous_redirected_to_login(user: User) -> None:
    await user.open('/users')
    await user.should_see('请使用管理员账号登录')
