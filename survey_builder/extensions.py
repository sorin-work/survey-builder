import sqlite3

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Named constraints so Alembic batch migrations on SQLite can refer to them.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


db = SQLAlchemy(model_class=Base)
migrate = Migrate(render_as_batch=True)
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _record):
    # SQLite ignores ON DELETE CASCADE unless foreign keys are switched on.
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
