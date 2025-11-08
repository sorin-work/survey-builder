import sqlalchemy as sa
from flask_migrate import upgrade

from survey_builder import create_app
from survey_builder.extensions import db


def test_migrations_create_every_model_table(tmp_path):
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'm.db'}"})
    with app.app_context():
        upgrade()
        tables = set(sa.inspect(db.engine).get_table_names())
    assert set(db.metadata.tables) <= tables
