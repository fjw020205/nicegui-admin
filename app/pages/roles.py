"""角色管理：角色增删改 + 菜单/按钮权限分配。"""
from __future__ import annotations

from nicegui import ui
from sqlalchemy import select

from app.auth import has_perm
from app.database import session_scope
from app.layout import ensure_perm, get_user, shell
from app.models import Menu, Role

COLUMNS = [
    {'name': 'name', 'label': '角色名称', 'field': 'name', 'align': 'left'},
    {'name': 'code', 'label': '标识', 'field': 'code', 'align': 'left'},
    {'name': 'user_count', 'label': '用户数', 'field': 'user_count', 'align': 'center'},
    {'name': 'description', 'label': '说明', 'field': 'description', 'align': 'left'},
    {'name': 'actions', 'label': '操作', 'field': 'actions', 'align': 'right'},
]


@ui.page('/roles')
def roles_page() -> None:
    me = get_user()
    with shell('角色管理', '/roles', '一个角色 = 一组菜单与按钮权限'):
        if not ensure_perm('role:view'):
            return

        can_create = has_perm(me, 'role:create')
        can_update = has_perm(me, 'role:update')
        can_delete = has_perm(me, 'role:delete')
        can_assign = has_perm(me, 'role:assign')

        editor = ui.dialog()
        assign_dialog = ui.dialog()

        def open_editor(row: dict | None = None) -> None:
            is_edit = row is not None
            with session_scope() as session:
                current = session.get(Role, row['id']) if is_edit else None

            editor.clear()
            with editor, ui.card().classes('w-[520px] max-w-full'):
                ui.label('编辑角色' if is_edit else '新增角色').classes('text-base font-semibold')
                name = ui.input('角色名称 *', value=current.name if current else '') \
                    .props('outlined dense').classes('w-full')
                code = ui.input('角色标识 *（英文，如 hr_manager）', value=current.code if current else '') \
                    .props('outlined dense').classes('w-full')
                description = ui.input('说明', value=current.description if current else '') \
                    .props('outlined dense').classes('w-full')
                sort = ui.number('排序', value=current.sort if current else 0, format='%d') \
                    .props('outlined dense').classes('w-32')

                def save() -> None:
                    name_value = (name.value or '').strip()
                    code_value = (code.value or '').strip()
                    if not name_value or not code_value:
                        ui.notify('角色名称和标识不能为空', type='warning')
                        return
                    with session_scope() as session:
                        duplicated = session.scalar(
                            select(Role).where(Role.code == code_value, Role.id != (row['id'] if is_edit else -1))
                        )
                        if duplicated:
                            ui.notify('角色标识已存在', type='negative')
                            return
                        db_role = session.get(Role, row['id']) if is_edit else Role()
                        db_role.name = name_value
                        db_role.code = code_value
                        db_role.description = (description.value or '').strip()
                        db_role.sort = int(sort.value or 0)
                        if not is_edit:
                            session.add(db_role)
                    editor.close()
                    table_area.refresh()
                    ui.notify('保存成功', type='positive')

                with ui.row().classes('w-full justify-end gap-2 mt-1'):
                    ui.button('取消', on_click=editor.close).props('flat')
                    ui.button('保存', on_click=save).props('unelevated')
            editor.open()

        def open_assign(row: dict) -> None:
            with session_scope() as session:
                role = session.get(Role, row['id'])
                selected = {m.id for m in role.menus}
                menus = session.scalars(select(Menu).order_by(Menu.sort, Menu.id)).all()
                nodes = [
                    {'id': m.id, 'parent_id': m.parent_id, 'name': m.name, 'type': m.type,
                     'perm': m.perm, 'sort': m.sort}
                    for m in menus
                ]

            children: dict[int | None, list[dict]] = {}
            for n in nodes:
                children.setdefault(n['parent_id'], []).append(n)

            assign_dialog.clear()
            boxes: dict[int, ui.checkbox] = {}

            with assign_dialog, ui.card().classes('w-[560px] max-w-full'):
                ui.label(f"分配权限：{row['name']}").classes('text-base font-semibold')
                ui.label('勾选后该角色才能看到对应菜单 / 点击对应按钮').classes('text-xs text-gray-500')

                def set_all(value: bool) -> None:
                    for box in boxes.values():
                        box.value = value

                with ui.row().classes('gap-2'):
                    ui.button('全选', on_click=lambda: set_all(True)).props('flat dense size=sm')
                    ui.button('全不选', on_click=lambda: set_all(False)).props('flat dense size=sm')

                with ui.column().classes('w-full gap-0 max-h-[55vh] overflow-auto'):
                    def render(parent_id: int | None, depth: int) -> None:
                        for node in children.get(parent_id, []):
                            with ui.row().classes('items-center w-full no-wrap').style(f'padding-left:{depth * 22}px'):
                                label = node['name']
                                if node['type'] == 'button':
                                    label = f"[按钮] {label}"
                                elif node['type'] == 'dir':
                                    label = f"[目录] {label}"
                                boxes[node['id']] = ui.checkbox(label, value=node['id'] in selected)
                                if node['perm']:
                                    ui.label(node['perm']).classes('text-[11px] text-gray-400')
                            if node['id'] in children:
                                render(node['id'], depth + 1)

                    render(None, 0)

                def save() -> None:
                    chosen = [mid for mid, box in boxes.items() if box.value]
                    with session_scope() as session:
                        db_role = session.get(Role, row['id'])
                        db_role.menus = list(
                            session.scalars(select(Menu).where(Menu.id.in_(chosen))).all()
                        ) if chosen else []
                    assign_dialog.close()
                    ui.notify('权限已保存', type='positive')

                with ui.row().classes('w-full justify-end gap-2 mt-2'):
                    ui.button('取消', on_click=assign_dialog.close).props('flat')
                    ui.button('保存', on_click=save).props('unelevated')
            assign_dialog.open()

        def open_delete(row: dict) -> None:
            with session_scope() as session:
                role = session.get(Role, row['id'])
                if role.users:
                    ui.notify(f"该角色下还有 {len(role.users)} 个用户，请先移除", type='warning')
                    return
                session.delete(role)
            table_area.refresh()
            ui.notify('已删除', type='positive')

        @ui.refreshable
        def table_area() -> None:
            with session_scope() as session:
                roles = session.scalars(select(Role).order_by(Role.sort, Role.id)).all()
                rows = [
                    {
                        'id': r.id,
                        'name': r.name,
                        'code': r.code,
                        'user_count': len(r.users),
                        'description': r.description or '-',
                    }
                    for r in roles
                ]

            buttons = []
            if can_update:
                buttons.append('<q-btn dense flat round size="sm" color="primary" icon="edit" '
                               '@click="$parent.$emit(\'row-edit\', props.row)"><q-tooltip>编辑</q-tooltip></q-btn>')
            if can_assign:
                buttons.append('<q-btn dense flat round size="sm" color="teal" icon="rule" '
                               '@click="$parent.$emit(\'row-assign\', props.row)"><q-tooltip>分配权限</q-tooltip></q-btn>')
            if can_delete:
                buttons.append('<q-btn dense flat round size="sm" color="negative" icon="delete" '
                               '@click="$parent.$emit(\'row-delete\', props.row)"><q-tooltip>删除</q-tooltip></q-btn>')

            table = ui.table(columns=COLUMNS, rows=rows, row_key='id', pagination=10).classes('w-full')
            table.props('flat bordered')
            table.add_slot('body-cell-actions', '<q-td :props="props" class="text-right">' + ''.join(buttons) + '</q-td>')
            table.on('row-edit', lambda e: open_editor(e.args))
            table.on('row-assign', lambda e: open_assign(e.args))
            table.on('row-delete', lambda e: open_delete(e.args))

        with ui.card().classes('soft-card w-full mt-4 p-4'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('角色列表').classes('text-base font-semibold')
                if can_create:
                    ui.button('新增角色', icon='add', on_click=lambda: open_editor(None)).props('unelevated rounded')
            ui.separator().classes('my-2')
            table_area()
