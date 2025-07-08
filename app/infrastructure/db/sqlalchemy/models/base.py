from sqlalchemy.orm import DeclarativeBase

# SQLAlchemy uses Base.metadata to track all ORM models.
# It's required for create_all(), drop_all(), and Alembic (migration tool for SQLAlchemy) autogenerate to work correctly.
# All models must inherit from the same Base to ensure the full metadata is available.
class Base(DeclarativeBase):
    pass