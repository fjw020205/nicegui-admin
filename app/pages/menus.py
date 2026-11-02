"""菜单管理：目录 / 页面 / 按钮三级，菜单即权限来源。"""
from __future__ import annotations

from nicegui import ui
from sqlalchemy import func, select

from app.auth import has_perm
from app.database import session_scope
from app.layout import ensure_perm, get_user, shell
from app.models import Menu

TYPE_LABEL = {'dir': '目录', 'page': '页面', 'button': '按钮'}
TYPE_COLOR = {'dir': 'purple', 'page': 'blue', 'button': 'teal'}

COLUMNS = [
    {'name': 'name', 'label': '菜单名称', 'field': 'name', 'align': 'left'},
    {'name': 'type', 'label': '类型', 'field': 'type', 'align': 'center'},
    {'name': 'path', 'label': '路由 / 路径', 'field': 'path', 'align': 'left'},
    {'name': 'perm', 'label': '权限标识', 'field': 'perm', 'align': 'left'},
    {'name': 'sort', 'label': '排序', 'field': 'sort', 'align': 'center'},
    {'name': 'visible', 'label': '显示', 'field': 'visible', 'align': 'center'},
    {'name': 'actions', 'label': '操作', 'field': 'actions', 'align': 'right'},
]


@ui.page('/menus')
def menus_page() -> None:
    me = get_user()
    with shell('菜单管理', '/menus', '菜单决定侧边导航，按钮项决定按钮级权限'):
        if not ensure_perm('menu:view'):
            return

        can_create = has_perm(me, 'menu:create')
        can_update = has_perm(me, 'menu:update')
        can_delete = has_perm(me, 'menu:delete')

        editor = ui.dialog()

        def open_editor(row: dict | None = None, parent_id: int | None = None) -> None:
            is_edit = row is not None
            with session_scope() as session:
                all_menus = session.scalars(select(Menu).order_by(Menu.sort, Menu.id)).all()
                current = session.get(Menu, row['id']) if is_edit else None
                parent_options = {0: '顶级菜单'}
                for m in all_menus:
                    if m.type == 'button':
                        continue
                    if is_edit and m.id == current.id:
                        continue
                    parent_options[m.id] = ('　' * (1 if m.parent_id else 0)) + m.name

            editor.clear()
            with editor, ui.card().classes('w-[560px] max-w-full'):
                ui.label('编辑菜单' if is_edit else '新增菜单').classes('text-base font-semibold')
                parent_select = (
                    ui.select(parent_options, label='上级菜单',
                              value=(current.parent_id or 0) if is_edit else (parent_id or 0))
                    .props('outlined dense').classes('w-full')
                )
                name = ui.input('名称 *', value=current.name if current else '') \
                    .props('outlined dense').classes('w-full')
                type_select = (
                    ui.select({k: v for k, v in TYPE_LABEL.items()}, label='类型',
                              value=current.type if current else 'page')
                    .props('outlined dense').classes('w-full')
                )
                path = ui.input('路由路径（页面类型必填，如 /orders）', value=current.path if current else '') \
                    .props('outlined dense').classes('w-full')
                icon = ui.input('图标（Material 图标名，如 dashboard）', value=current.icon if current else '') \
                    .props('outlined dense').classes('w-full')
                perm = ui.input('权限标识（如 order:create）', value=current.perm if current else '') \
                    .props('outlined dense').classes('w-full')
                with ui.row().classes('w-full gap-2 items-center no-wrap'):
                    sort = ui.number('排序', value=current.sort if current else 0, format='%d') \
                        .props('outlined dense').classes('w-32')
                    visible = ui.switch('在导航中显示', value=current.visible if current else True)

                def save() -> None:
                    name_value = (name.value or '').strip()
                    if not name_value:
                        ui.notify('名称不能为空', type='warning')
                        return
                    menu_type = type_select.value or 'page'
                    if menu_type == 'page' and not (path.value or '').strip():
                        ui.notify('页面类型必须填写路由路径', type='warning')
                        return
                    with session_scope() as session:
                        db_menu = session.get(Menu, row['id']) if is_edit else Menu()
                        db_menu.parent_id = (parent_select.value or 0) or None
                        db_menu.name = name_value
                        db_menu.type = menu_type
                        db_menu.path = (path.value or '').strip()
                        db_menu.icon = (icon.value or '').strip()
                        db_menu.perm = (perm.value or '').strip()
                        db_menu.sort = int(sort.value or 0)
                        db_menu.visible = bool(visible.value)
                        if not is_edit:
                            session.add(db_menu)
                    editor.close()
                    table_area.refresh()
                    ui.notify('保存成功', type='positive')

                with ui.row().classes('w-full justify-end gap-2 mt-1'):
                    ui.button('取消', on_click=editor.close).props('flat')
                    ui.button('保存', on_click=save).props('unelevated')
            editor.open()

        def open_delete(row: dict) -> None:
            with session_scope() as session:
                children = session.scalar(select(func.count(Menu.id)).where(Menu.parent_id == row['id'])) or 0
                if children:
                    ui.notify('请先删除下级菜单', type='warning')
                    return
                session.delete(session.get(Menu, row['id']))
            table_area.refresh()
            ui.notify('已删除', type='positive')

        @ui.refreshable
        def table_area() -> None:
            with session_scope() as session:
                menus = session.scalars(select(Menu).order_by(Menu.sort, Menu.id)).all()
                nodes = [
                    {'id': m.id, 'parent_id': m.parent_id, 'name': m.name, 'type': m.type,
                     'path': m.path, 'perm': m.perm, 'sort': m.sort, 'visible': m.visible}
                    for m in menus
                ]

            grouped: dict[int | None, list[dict]] = {}
            for n in nodes:
                grouped.setdefault(n['parent_id'], []).append(n)

            rows: list[dict] = []

            def walk(parent_id: int | None, depth: int) -> None:
                for node in grouped.get(parent_id, []):
                    rows.append(
                        {
                            'id': node['id'],
                            'name': '　' * depth + ('└ ' if depth else '') + node['name'],
                            'type': node['type'],
                            'type_label': TYPE_LABEL.get(node['type'], node['type']),
                            'path': node['path'] or '-',
                            'perm': node['perm'] or '-',
                            'sort': node['sort'],
                            'visible': '是' if node['visible'] else '隐藏',
                            'is_visible': node['visible'],
                        }
                    )
                    walk(node['id'], depth + 1)

            walk(None, 0)

            buttons = []
            if can_create:
                buttons.append('<q-btn dense flat round size="sm" color="teal" icon="add" '
                               '@click="$parent.$emit(\'row-add\', props.row)"><q-tooltip>新增子项</q-tooltip></q-btn>')
            if can_update:
                buttons.append('<q-btn dense flat round size="sm" color="primary" icon="edit" '
                               '@click="$parent.$emit(\'row-edit\', props.row)"><q-tooltip>编辑</q-tooltip></q-btn>')
            if can_delete:
                buttons.append('<q-btn dense flat round size="sm" color="negative" icon="delete" '
                               '@click="$parent.$emit(\'row-delete\', props.row)"><q-tooltip>删除</q-tooltip></q-btn>')

            table = ui.table(columns=COLUMNS, rows=rows, row_key='id', pagination=0).classes('w-full')
            table.props('flat bordered')
            table.add_slot('body-cell-type', '''
                <q-td :props="props" class="text-center">
                    <q-badge :color="props.row.type === 'dir' ? 'purple' : (props.row.type === 'page' ? 'blue' : 'teal')">
                        {{ props.row.type_label }}
                    </q-badge>
                </q-td>
            ''')
            table.add_slot('body-cell-visible', '''
                <q-td :props="props" class="text-center">
                    <span :class="props.row.is_visible ? 'text-green-6' : 'text-gray-400'">{{ props.row.visible }}</span>
                </q-td>
            ''')
            table.add_slot('body-cell-actions', '<q-td :props="props" class="text-right">' + ''.join(buttons) + '</q-td>')
            table.on('row-add', lambda e: open_editor(None, e.args['id']))
            table.on('row-edit', lambda e: open_editor(e.args))
            table.on('row-delete', lambda e: open_delete(e.args))

        with ui.card().classes('soft-card w-full mt-4 p-4'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('菜单树').classes('text-base font-semibold')
                if can_create:
                    ui.button('新增菜单', icon='add', on_click=lambda: open_editor(None, None)).props('unelevated rounded')
            ui.separator().classes('my-2')
            table_area()
