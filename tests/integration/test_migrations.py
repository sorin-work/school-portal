from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from school_portal.extensions import db


def test_models_match_the_migrations(app):
    """The tables built by the migrations are the tables the models describe."""
    with db.engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, db.metadata)
    assert differences == []
