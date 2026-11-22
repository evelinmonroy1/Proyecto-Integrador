from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Enum, Boolean, func
from database import Base


class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), nullable=False, unique=True)


class Palabra(Base):
    __tablename__ = "palabras"
    id = Column(Integer, primary_key=True)
    mazahua = Column(String(100), nullable=False)
    espanol = Column(String(100), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)
    imagen = Column(String(255))
    audio = Column(String(255))
    creado_en = Column(TIMESTAMP, server_default=func.now())

class Partida(Base):
    __tablename__ = "partidas"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(8), nullable=False, unique=True)
    filas = Column(Integer, nullable=False)
    columnas = Column(Integer, nullable=False)
    estado = Column(Enum("espera", "en_juego", "finalizada", name="estado_partida"), nullable=False, default="espera")
    creada_en = Column(TIMESTAMP, server_default=func.now())
    iniciada_en = Column(TIMESTAMP, nullable=True)
    finalizada_en = Column(TIMESTAMP, nullable=True)

class Jugador(Base):
    __tablename__ = "jugadores"
    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(50), nullable=False)
    avatar = Column(String(50), nullable=False)
    unido_en = Column(TIMESTAMP, server_default=func.now())


class Tablero(Base):
    __tablename__ = "tableros"
    id = Column(Integer, primary_key=True)
    jugador_id = Column(Integer, ForeignKey("jugadores.id", ondelete="CASCADE"), nullable=False)
    palabra_id = Column(Integer, ForeignKey("palabras.id"), nullable=False)
    posicion = Column(Integer, nullable=False)
    marcada = Column(Boolean, nullable=False, default=False)


class Deteccion(Base):
    __tablename__ = "detecciones"
    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id", ondelete="CASCADE"), nullable=False)
    palabra_id = Column(Integer, ForeignKey("palabras.id"), nullable=False)
    orden = Column(Integer, nullable=False)
    detectada_en = Column(TIMESTAMP, server_default=func.now())


class Podio(Base):
    __tablename__ = "podio"
    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id", ondelete="CASCADE"), nullable=False)
    jugador_id = Column(Integer, ForeignKey("jugadores.id", ondelete="CASCADE"), nullable=False)
    lugar = Column(Integer, nullable=False)
    completado_en = Column(TIMESTAMP, server_default=func.now())

class TarjetaRfid(Base):
    __tablename__ = "tarjetas_rfid"
    id = Column(Integer, primary_key=True)
    uid = Column(String(32), nullable=False, unique=True)
    palabra_id = Column(
        Integer, ForeignKey("palabras.id", ondelete="CASCADE"), nullable=False, unique=True
    )


class Administrador(Base):
    __tablename__ = "administradores"
    id = Column(Integer, primary_key=True)
    usuario = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
