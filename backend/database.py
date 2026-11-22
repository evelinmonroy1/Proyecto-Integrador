import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()


def _crear_motor():
    """Se conecta a la base de datos.

    - En tu computadora usa MySQL/MariaDB con DB_USER, DB_PASSWORD, DB_HOST, DB_PORT y DB_NAME (archivo .env).
    - En la nube se usa una sola variable DATABASE_URL. Sirve para MySQL o para
      PostgreSQL (por ejemplo Neon: postgresql://usuario:clave@host/neondb?sslmode=require).
    - Si una base MySQL exige conexión segura (SSL), pon DB_SSL=true.
    """
    argumentos = {}
    url = os.getenv("DATABASE_URL", "").strip()

    if url:
        if url.startswith("mysql://"):
            url = "mysql+pymysql://" + url[len("mysql://"):]
        # PostgreSQL (Neon, Render, etc.)
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        if url.startswith("sqlite"):
            argumentos["check_same_thread"] = False
    else:
        url = URL.create(
            "mysql+pymysql",
            username=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT") or 3306),
            database=os.getenv("DB_NAME"),
            query={"charset": "utf8mb4"},
        )

    es_mysql = str(url).startswith("mysql")
    if es_mysql and os.getenv("DB_SSL", "").strip().lower() in ("1", "true", "si", "sí", "yes"):
        argumentos["ssl"] = {"ca": os.getenv("DB_SSL_CA", "/etc/ssl/certs/ca-certificates.crt")}

    return create_engine(
        url,
        pool_pre_ping=True,   # revisa que la conexión siga viva antes de usarla
        pool_recycle=280,     # las bases gratuitas cierran conexiones inactivas
        connect_args=argumentos,
    )


engine = _crear_motor()

# SQLite (modo sencillo, sin MySQL) no respeta los borrados en cascada si no se le pide
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _activar_llaves(conexion, _registro):
        conexion.execute("PRAGMA foreign_keys=ON")
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def obtener_bd():
    bd = SessionLocal()
    try:
        yield bd
    finally:
        bd.close()