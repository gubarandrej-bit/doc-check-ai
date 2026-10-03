"""ORM-модели базы данных."""
import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    """Пользователь системы."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=False, default="")
    role = Column(String(16), default="user")  # admin | user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    checks = relationship("CheckRun", back_populates="user")


class NtdDocument(Base):
    """Нормативно-технический документ (НТД)."""

    __tablename__ = "ntd_documents"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(64), nullable=False)
    title = Column(String(512), nullable=False)
    doc_type = Column(String(64), default="")  # ФЗ, СП, ГОСТ, ПУЭ, СНиП, СПДС
    issue_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)  # дата введения в действие
    status = Column(String(32), default="actual")  # actual | expired | superseded
    url = Column(String(512), default="")
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Project(Base):
    """Проект (набор загруженной документации)."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    files = relationship("UploadedFile", back_populates="project")
    checks = relationship("CheckRun", back_populates="project")


class UploadedFile(Base):
    """Загруженный файл исходных данных."""

    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    file_type = Column(String(16), nullable=False)  # xls, doc, pdf, dwg
    size = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    project = relationship("Project", back_populates="files")


class AiModel(Base):
    """Модель ИИ, доступная в системе (локальная или облачная)."""

    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    provider = Column(String(32), nullable=False)  # openrouter | ollama | custom
    model_id = Column(String(128), nullable=False)
    mode = Column(String(16), default="cloud")  # local | cloud
    api_key = Column(String(512), default="")
    base_url = Column(String(256), default="")
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CheckRun(Base):
    """Запуск проверки по проекту."""

    __tablename__ = "check_runs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    mode = Column(String(16), default="local")  # local | cloud | hybrid
    status = Column(String(32), default="running")  # running | completed | failed
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="checks")
    project = relationship("Project", back_populates="checks")
    items = relationship("CheckItem", back_populates="check_run")


class CheckItem(Base):
    """Отдельная проверка внутри запуска."""

    __tablename__ = "check_items"

    id = Column(Integer, primary_key=True, index=True)
    check_run_id = Column(Integer, ForeignKey("check_runs.id"), nullable=False)
    code = Column(String(64), nullable=False)  # например: CABLE_JOURNAL_SPEC
    name = Column(String(255), nullable=False)
    category = Column(String(32), default="critical")  # critical | non-critical
    status = Column(String(32), default="not_performed")  # passed | failed | not_performed
    detail = Column(Text, default="")
    ntd_refs = Column(Text, default="")  # ссылки на пункты НТД
    reason_skipped = Column(Text, default="")

    check_run = relationship("CheckRun", back_populates="items")


def init_db():
    """Создаёт таблицы и заполняет дефолтные НТД, админа и модели ИИ."""
    Base.metadata.create_all(engine)
    from seed import seed_default_admin, seed_default_models, seed_ntd

    with SessionLocal() as session:
        seed_ntd(session)
        seed_default_admin(session)
        seed_default_models(session)
        session.commit()