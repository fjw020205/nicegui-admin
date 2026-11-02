"""用户管理：增删改查、分配角色、重置密码、启用/禁用。"""
from __future__ import annotations

from nicegui import ui
from sqlalchemy import or_, select

from app.auth import hash_password, has_perm
from app.database import session_scope
from app.layout import ensure_perm, get_user, shell
from app.models import Role, User

COLUMNS = [
    {'name': 'username', 'label': '用户名', 'field': 'username', 'align': 'left', 'sortable': True},
    {'name': 'nickname', 'label': '昵称', 'field': 'nickname', 'align': 'left'},
    {'name': 'roles', 'label': '角色', 'field': 'roles', 'align': 'left'},
    {'name': 'phone', 'label': '手机号', 'field': 'phone', 'align': 'left'},
    {'name': 'status', 'label': '状态', 'field': 'status', 'align': 'center'},
    {'name': 'last_login', 'label': '最后登录', 'field': 'last_login', 'align': 'left'},
    {'name': 'actions', 'label': '操作', 'field': 'actions', 'align': 'right'},
]


def _slot(can_update: bool, can_delete: bool, can_reset: bool) -> str:
    buttons = []
    if can_update:
        buttons.append(
            '<q-btn dense flat round size="sm" color="primary" icon="edit" '
            '@click="$parent.$emit(\'row-edit\', props.row)"><q-tooltip>编辑</q-tooltip></q-btn>'
        )
    if can_reset:
        buttons.append(
            '<q-btn dense flat round size="sm" color="orange" icon="key" '
            '@click="$parent.$emit(\'row-reset\', props.row)"><q-tooltip>重置密码</q-tooltip></q-btn>'
        )
    if can_delete:
        buttons.append(
            '<q-btn dense flat round size="sm" color="negative" icon="delete" '
            '@click="$parent.$emit(\'row-delete\', props.row)"><q-tooltip>删除</q-tooltip></q-btn>'
        )
    return '<q-td :props="props" class="text-right">' + ''.join(buttons) + '</q-td>'


@ui.page('/users')
def users_page() -> None:
    me = get_user()
    with shell('用户管理', '/users', '维护系统账号、所属角色与启用状态'):
        if not ensure_perm('user:view'):
            return

        can_create = has_perm(me, 'user:create')
        can_update = has_perm(me, 'user:update')
        can_delete = has_perm(me, 'user:delete')
        can_reset = has_perm(me, 'user:reset')

        # ---------------- 弹窗（复用，避免事件里反复创建元素）
        editor = ui.dialog()
        reset_dialog = ui.dialog()
        confirm_dialog = ui.dialog()

        def open_editor(row: dict | None = None) -> None:
            is_edit = row is not None
            with session_scope() as session:
                roles = session.scalars(select(Role).order_by(Role.sort, Role.id)).all()
                role_options = {r.id: f'{r.name}（{r.code}）' for r in roles}
                current = session.get(User, row['id']) if is_edit else None
                current_roles = [r.id for r in current.roles] if current else []

            editor.clear()
            with editor, ui.card().classes('w-[560px] max-w-full'):
                ui.label('编辑用户' if is_edit else '新增用户').classes('text-base font-semibold')
                username = (
                    ui.input('用户名 *', value=current.username if current else '')
                    .props('outlined dense')
                    .classes('w-full')
                )
                if is_edit:
                    username.props('readonly')
                nickname = (
                    ui.input('昵称', value=current.nickname if current else '')
                    .props('outlined dense')
                    .classes('w-full')
                )
                password = ui.input(
                    '密码' + ('' if is_edit else ' *'),
                    password=True,
                    password_toggle_button=True,
                    placeholder='留空则不修改' if is_edit else '至少 6 位',
                ).props('outlined dense').classes('w-full')
                with ui.row().classes('w-full gap-2 no-wrap'):
                    phone = (
                        ui.input('手机号', value=current.phone if current else '')
                        .props('outlined dense')
                        .classes('w-full')
                    )
                    email = (
                        ui.input('邮箱', value=current.email if current else '')
                        .props('outlined dense')
                        .classes('w-full')
                    )
                role_select = (
                    ui.select(role_options, label='角色', multiple=True, value=current_roles)
                    .props('outlined dense use-chips')
                    .classes('w-full')
                )
                remark = (
                    ui.input('备注', value=current.remark if current else '')
                    .props('outlined dense')
                    .classes('w-full')
                )
                active = ui.switch('启用账号', value=current.is_active if current else True)

                def save() -> None:
                    name = (username.value or '').strip()
                    pwd = password.value or ''
                    if not name:
                        ui.notify('用户名不能为空', type='warning')
                        return
                    if not is_edit and len(pwd) < 6:
                        ui.notify('新增用户必须设置至少 6 位密码', type='warning')
                        return
                    if is_edit and pwd and len(pwd) < 6:
                        ui.notify('密码至少 6 位', type='warning')
                        return

                    with session_scope() as session:
                        if is_edit:
                            db_user = session.get(User, row['id'])
                        else:
                            exists = session.scalar(select(User).where(User.username == name))
                            if exists:
                                ui.notify('用户名已存在', type='negative')
                                return
                            db_user = User(username=name, password_hash=hash_password(pwd))
                            session.add(db_user)
                        db_user.nickname = (nickname.value or '').strip()
                        db_user.phone = (phone.value or '').strip()
                        db_user.email = (email.value or '').strip()
                        db_user.remark = (remark.value or '').strip()
                        db_user.is_active = bool(active.value)
                        if pwd:
                            db_user.password_hash = hash_password(pwd)
                        selected = role_select.value or []
                        db_user.roles = list(
                            session.scalars(select(Role).where(Role.id.in_(selected))).all()
                        ) if selected else []

                    editor.close()
                    table_area.refresh()
                    ui.notify('保存成功', type='positive')

                with ui.row().classes('w-full justify-end gap-2 mt-1'):
                    ui.button('取消', on_click=editor.close).props('flat')
                    ui.button('保存', on_click=save).props('unelevated')
            editor.open()

        def open_reset(row: dict) -> None:
            reset_dialog.clear()
            with reset_dialog, ui.card().classes('w-96 max-w-full'):
                ui.label(f"重置密码：{row['username']}").classes('text-base font-semibold')
                pwd = ui.input('新密码（至少 6 位）', password=True, password_toggle_button=True) \
                    .props('outlined dense').classes('w-full')

                def do_reset() -> None:
                    value = pwd.value or ''
                    if len(value) < 6:
                        ui.notify('密码至少 6 位', type='warning')
                        return
                    with session_scope() as session:
                        db_user = session.get(User, row['id'])
                        db_user.password_hash = hash_password(value)
                    reset_dialog.close()
                    ui.notify('密码已重置', type='positive')

                with ui.row().classes('w-full justify-end gap-2 mt-2'):
                    ui.button('取消', on_click=reset_dialog.close).props('flat')
                    ui.button('确定', on_click=do_reset).props('unelevated')
            reset_dialog.open()

        def open_delete(row: dict) -> None:
            confirm_dialog.clear()
            with confirm_dialog, ui.card().classes('w-96 max-w-full'):
                ui.label('删除确认').classes('text-base font-semibold')
                ui.label(f"确定删除用户「{row['username']}」吗？该操作不可恢复。").classes('text-sm text-gray-600')

                def do_delete() -> None:
                    if row['id'] == me.id:
                        ui.notify('不能删除当前登录账号', type='warning')
                        return
                    with session_scope() as session:
                        db_user = session.get(User, row['id'])
                        if db_user and db_user.is_superuser:
                            total = len(session.scalars(select(User).where(User.is_superuser.is_(True))).all())
                            if total <= 1:
                                ui.notify('至少保留一个超级管理员', type='warning')
                                return
                        session.delete(db_user)
                    confirm_dialog.close()
                    table_area.refresh()
                    ui.notify('已删除', type='positive')

                with ui.row().classes('w-full justify-end gap-2 mt-2'):
                    ui.button('取消', on_click=confirm_dialog.close).props('flat')
                    ui.button('删除', on_click=do_delete).props('unelevated color=negative')
            confirm_dialog.open()

        # ---------------- 列表
        @ui.refreshable
        def table_area() -> None:
            keyword = (search.value or '').strip()
            with session_scope() as session:
                stmt = select(User)
                if keyword:
                    like = f'%{keyword}%'
                    stmt = stmt.where(
                        or_(User.username.like(like), User.nickname.like(like), User.phone.like(like))
                    )
                users = session.scalars(stmt.order_by(User.id)).all()
                rows = [
                    {
                        'id': u.id,
                        'username': u.username,
                        'nickname': u.nickname,
                        'roles': u.role_names,
                        'phone': u.phone or '-',
                        'status': '启用' if u.is_active else '禁用',
                        'is_active': u.is_active,
                        'last_login': u.last_login_at.strftime('%Y-%m-%d %H:%M') if u.last_login_at else '从未登录',
                    }
                    for u in users
                ]

            table = ui.table(columns=COLUMNS, rows=rows, row_key='id', pagination=10).classes('w-full')
            table.props('flat bordered')
            table.add_slot('body-cell-status', '''
                <q-td :props="props" class="text-center">
                    <q-badge :color="props.row.is_active ? 'green-6' : 'grey-5'">{{ props.row.status }}</q-badge>
                </q-td>
            ''')
            table.add_slot('body-cell-actions', _slot(can_update, can_delete, can_reset))
            table.on('row-edit', lambda e: open_editor(e.args))
            table.on('row-reset', lambda e: open_reset(e.args))
            table.on('row-delete', lambda e: open_delete(e.args))

        with ui.card().classes('soft-card w-full mt-4 p-4'):
            with ui.row().classes('w-full items-center justify-between gap-2 flex-wrap'):
                search = (
                    ui.input(placeholder='搜索用户名 / 昵称 / 手机号')
                    .props('outlined dense clearable')
                    .classes('w-64 max-w-full')
                )
                search.on('keydown.enter', lambda: table_area.refresh())
                search.on('blur', lambda: table_area.refresh())
                if can_create:
                    ui.button('新增用户', icon='add', on_click=lambda: open_editor(None)).props('unelevated rounded')
            ui.separator().classes('my-2')
            table_area()
