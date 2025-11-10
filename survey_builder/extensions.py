from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
migrate = Migrate(render_as_batch=True)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
