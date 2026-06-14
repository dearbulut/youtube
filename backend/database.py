from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


def _migrate_columns():
    """Idempotent additive column migrations for SQLite."""
    from sqlalchemy import text

    migrations = [
        ("user_settings", "manual_override", "BOOLEAN DEFAULT 0"),
        ("user_settings", "app_password_hash", "VARCHAR"),
        ("videos", "niche_theme", "VARCHAR"),
    ]
    with engine.connect() as conn:
        for table, column, col_def in migrations:
            try:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
                )
                conn.commit()
            except Exception:
                pass  # column already exists
