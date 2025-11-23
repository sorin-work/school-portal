import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from school_portal import models  # noqa: F401  (registers the tables)
from school_portal.extensions import db

config = context.config
if config.config_file_name is not None and not config.attributes.get("skip_logging"):
    fileConfig(config.config_file_name)

target_metadata = db.metadata


def database_url() -> str:
    url = config.attributes.get("url") or os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://school:school@127.0.0.1:5463/school"
    )
    return url


def run_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    engine = create_engine(database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
