from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite", database=str(path)),
        connect_args={"check_same_thread": False, "timeout": 15},
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")

    return engine


def migrate(engine: Engine) -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    # SQLite batch migrations rebuild referenced tables. Disable FK enforcement
    # only on this startup connection, outside a transaction, then verify all rows.
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            with connection.begin():
                # Python's SQLite legacy transaction mode does not BEGIN for
                # DDL. Start explicitly so a failed rebuild rolls back tables
                # and the Alembic revision together, including CREATE TABLE.
                connection.exec_driver_sql("BEGIN")
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                if connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                    raise RuntimeError("Foreign key validation failed after migration")
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
