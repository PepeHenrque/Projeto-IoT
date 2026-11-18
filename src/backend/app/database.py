"""Camada de banco de dados relacional (MySQL / SQLite Fallback) do CampusSmart."""
import os
import logging
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    Float,
    DateTime,
    Enum,
    ForeignKey,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

logger = logging.getLogger("campussmart.database")

Base = declarative_base()


class SalaDB(Base):
    __tablename__ = "salas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    modo_operacao = Column(Enum("AUTO", "ON", "OFF", name="modo_operacao_enum"), default="AUTO")
    status_ocupado = Column(Boolean, default=False)

    avisos = relationship("AvisoOledDB", back_populates="sala", cascade="all, delete-orphan")
    telemetrias = relationship("TelemetriaDB", back_populates="sala", cascade="all, delete-orphan")


class AvisoOledDB(Base):
    __tablename__ = "avisos_oled"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    sala_id = Column(Integer, ForeignKey("salas.id", ondelete="CASCADE"), nullable=False, index=True)
    mensagem = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    sala = relationship("SalaDB", back_populates="avisos")


class TelemetriaDB(Base):
    __tablename__ = "telemetrias"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    sala_id = Column(Integer, ForeignKey("salas.id", ondelete="CASCADE"), nullable=False, index=True)
    ocupado = Column(Boolean, nullable=False)
    potencia_w = Column(Float, nullable=False)
    corrente_ma = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    sala = relationship("SalaDB", back_populates="telemetrias")


def get_database_url() -> str:
    # 1. URL explícita via variável de ambiente
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # 2. Configurações individuais do MySQL
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "root")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "sistema_iot")

    if password:
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    return f"mysql+pymysql://{user}@{host}:{port}/{database}"


def build_engine():
    mysql_url = get_database_url()
    try:
        engine = create_engine(mysql_url, pool_pre_ping=True, connect_args={"connect_timeout": 2})
        with engine.connect():
            print(f"[DB] Conexão bem-sucedida ao MySQL: {mysql_url.split('@')[-1]}")
            return engine, "mysql"
    except Exception as e:
        # Fallback resiliente para SQLite local
        sqlite_file = os.path.join(os.path.dirname(__file__), "..", "sistema_iot.db")
        sqlite_url = f"sqlite:///{os.path.abspath(sqlite_file)}"
        print(f"[DB] MySQL não disponível ({e}). Utilizando SQLite local com schema oficial: {sqlite_file}")
        engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        return engine, "sqlite"


engine, DB_DIALECT = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        count = session.query(SalaDB).count()
        if count == 0:
            initial_salas = [
                SalaDB(id=101, nome="Sala 101", modo_operacao="AUTO", status_ocupado=False),  # única sala monitorada (ESP32)
            ]
            session.add_all(initial_salas)
            session.commit()
            print(f"[DB] Carga inicial de {len(initial_salas)} salas inserida no banco.")
    except Exception as e:
        session.rollback()
        print(f"[DB] Erro ao inicializar carga inicial: {e}")
    finally:
        session.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
