from alembic import context

from app.database import Base
from app import models  # noqa: F401 — register metadata for future migrations

connection = context.config.attributes["connection"]
context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
