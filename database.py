from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from core.config import settings

# Motor de base de datos
engine = create_engine(
    settings.DATABASE_URL,
    # connect_args solo necesario para SQLite (manejo de hilos)
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

# Fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""
    pass


def get_db():
    """Dependencia FastAPI: provee una sesión de BD y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Crea todas las tablas definidas en los modelos."""
    # Importar todos los modelos para que SQLAlchemy los registre
    from models import user, patient, availability, appointment, clinical_record, rips, audit_log  # noqa: F401
    Base.metadata.create_all(bind=engine)
