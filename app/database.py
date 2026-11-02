"""SQLite 连接管理（WAL 模式，适合单机 / 小团队局域网）。"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import DB_PATH
from app.models import Base

engine = create_engine(
    f'sqlite:///{DB_PATH}',
    connect_args={'check_same_thread': False, 'timeout': 15},
    future=True,
)


@event.listens_for(engine, 'connect')
def _sqlite_pragma(dbapi_connection, _record):  # noqa: ANN001
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.execute('PRAGMA journal_mode=WAL')   # 读写并发更友好
    cursor.execute('PRAGMA synchronous=NORMAL')
    cursor.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """提交 / 回滚 / 关闭一把梭，业务代码里直接用 with。"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def backup_to(target_path: Path) -> None:
    """备份数据库（VACUUM INTO，写入过程中也能拿到一致快照）。

    注意：VACUUM INTO 不支持参数绑定，文件名必须转义后内联。
    """
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    escaped = str(target_path).replace("'", "''")
    with engine.connect() as conn:
        conn.exec_driver_sql(f"VACUUM INTO '{escaped}'")
