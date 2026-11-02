"""数据模型：用户 / 角色 / 菜单（含按钮级权限）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# 用户 <-> 角色
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
)

# 角色 <-> 菜单（菜单里的按钮也是一种“菜单”，用于按钮级权限）
role_menus = Table(
    'role_menus',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('menu_id', Integer, ForeignKey('menus.id', ondelete='CASCADE'), primary_key=True),
)


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    nickname: Mapped[str] = mapped_column(String(64), default='')
    email: Mapped[str] = mapped_column(String(128), default='')
    phone: Mapped[str] = mapped_column(String(32), default='')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    roles: Mapped[list['Role']] = relationship(
        secondary=user_roles, back_populates='users', lazy='selectin'
    )

    @property
    def display_name(self) -> str:
        return self.nickname or self.username

    @property
    def role_names(self) -> str:
        return '、'.join(r.name for r in self.roles) or '未分配'


class Role(Base):
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(Text, default='')
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    users: Mapped[list[User]] = relationship(
        secondary=user_roles, back_populates='roles', lazy='selectin'
    )
    menus: Mapped[list['Menu']] = relationship(
        secondary=role_menus, back_populates='roles', lazy='selectin'
    )


class Menu(Base):
    """菜单树：type = dir(目录) / page(页面) / button(按钮权限)。"""

    __tablename__ = 'menus'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('menus.id', ondelete='CASCADE'), nullable=True
    )
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16), default='page')
    path: Mapped[str] = mapped_column(String(128), default='')
    icon: Mapped[str] = mapped_column(String(64), default='')
    perm: Mapped[str] = mapped_column(String(64), default='')
    sort: Mapped[int] = mapped_column(Integer, default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    roles: Mapped[list[Role]] = relationship(secondary=role_menus, back_populates='menus')
