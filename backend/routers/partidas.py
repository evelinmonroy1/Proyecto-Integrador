import random
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import func, case, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import obtener_bd, SessionLocal
from models import Partida, Palabra, Jugador, Tablero, Deteccion, Podio, TarjetaRfid

from auth import requiere_admin
from routers.palabras import a_dict as palabra_dict
from salas import salas

router = APIRouter(prefix="/api/partidas", tags=["Partidas"])
router_avatares = APIRouter(prefix="/api/avatares", tags=["Avatares"])

# Sin 0, O, 1, I, L para evitar confusiones al dictar o escribir el código
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO_CODIGO = 6
MAX_JUGADORES = 30

# Por ahora son emojis; más adelante puedes cambiarlos por ilustraciones propias
AVATARES = {
    "colibri": "🐦",
    "conejo": "🐰",
    "venado": "🦌",
    "rana": "🐸",
    "mariposa": "🦋",
    "aguila": "🦅",
    "ardilla": "🐿️",
    "tortuga": "🐢",
}
PATRON_AVATAR = re.compile(r"^(a-[0-7]-[0-5]-[0-6]-[0-5]-[0-4]|k-[0-5](-[0-5]-[0-2]-[0-5])?)$")


class PartidaIn(BaseModel):
    filas: int = Field(ge=2, le=6)
    columnas: int = Field(ge=2, le=6)


class JugadorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=50)
    avatar: str


# ---------- Funciones de apoyo ----------
def a_dict(p: Partida):
    return {
        "id": p.id,
        "codigo": p.codigo,
        "filas": p.filas,
        "columnas": p.columnas,
        "casillas": p.filas * p.columnas,
        "estado": p.estado,
    }


def jugador_dict(j: Jugador, conectados: set = frozenset()):
    return {
        "id": j.id,
        "nombre": j.nombre,
        "avatar": j.avatar,
        "emoji": AVATARES.get(j.avatar, "❓"),
        "conectado": j.id in conectados,
    }


def generar_codigo() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(LARGO_CODIGO))


def buscar_partida(bd: Session, codigo: str) -> Partida:
    p = bd.query(Partida).filter(Partida.codigo == codigo.strip().upper()).first()
    if not p:
        raise HTTPException(404, "No existe una partida con ese código")
    return p


def lista_jugadores(bd: Session, partida: Partida):
    conectados = salas.ids_conectados(partida.codigo)
    jugadores = (
        bd.query(Jugador)
        .filter(Jugador.partida_id == partida.id)
        .order_by(Jugador.id)
        .all()
    )
    return [jugador_dict(j, conectados) for j in jugadores]


async def difundir_lista(codigo: str):
    """Manda la lista actualizada de jugadores a todos los de la sala."""
    bd = SessionLocal()
    try:
        partida = bd.query(Partida).filter(Partida.codigo == codigo).first()
        if not partida:
            return
        mensaje = {"tipo": "jugadores", "jugadores": lista_jugadores(bd, partida)}
    finally:
        bd.close()
    await salas.difundir(codigo, mensaje)


# ---------- Avatares ----------
@router_avatares.get("")
def listar_avatares():
    return [{"id": k, "emoji": v} for k, v in AVATARES.items()]


# ---------- Crear y consultar partida ----------
@router.post("", status_code=201, dependencies=[Depends(requiere_admin)])
def crear_partida(datos: PartidaIn, bd: Session = Depends(obtener_bd)):
    casillas = datos.filas * datos.columnas
    disponibles = bd.query(func.count(Palabra.id)).scalar()

    if disponibles < casillas:
        raise HTTPException(
            400,
            f"Un tablero de {datos.filas}x{datos.columnas} necesita {casillas} palabras "
            f"y solo hay {disponibles} registradas",
        )

    for _ in range(10):
        p = Partida(codigo=generar_codigo(), filas=datos.filas, columnas=datos.columnas)
        bd.add(p)
        try:
            bd.commit()
        except IntegrityError:
            bd.rollback()
            continue
        bd.refresh(p)
        return a_dict(p)

    raise HTTPException(500, "No se pudo generar un código único, intenta de nuevo")


@router.get("/{codigo}")
def obtener_partida(codigo: str, bd: Session = Depends(obtener_bd)):
    return a_dict(buscar_partida(bd, codigo))


# ---------- Jugadores ----------
@router.post("/{codigo}/jugadores", status_code=201)
async def unirse(codigo: str, datos: JugadorIn, bd: Session = Depends(obtener_bd)):
    partida = buscar_partida(bd, codigo)

    if partida.estado != "espera":
        raise HTTPException(409, "La partida ya comenzó")

    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(400, "Escribe tu nombre")
    if datos.avatar not in AVATARES and not PATRON_AVATAR.match(datos.avatar):
        raise HTTPException(400, "Avatar no válido")

    total = bd.query(func.count(Jugador.id)).filter(Jugador.partida_id == partida.id).scalar()
    if total >= MAX_JUGADORES:
        raise HTTPException(409, "La partida está llena")

    j = Jugador(partida_id=partida.id, nombre=nombre, avatar=datos.avatar)
    bd.add(j)
    try:
        bd.commit()
    except IntegrityError:
        bd.rollback()
        raise HTTPException(409, "Ese nombre ya está en uso en esta partida")
    bd.refresh(j)

    resultado = {"jugador": jugador_dict(j), "partida": a_dict(partida)}
    await difundir_lista(partida.codigo)
    return resultado


@router.get("/{codigo}/jugadores")
def listar_jugadores(codigo: str, bd: Session = Depends(obtener_bd)):
    partida = buscar_partida(bd, codigo)
    return lista_jugadores(bd, partida)


@router.delete("/{codigo}/jugadores/{jugador_id}", dependencies=[Depends(requiere_admin)])
async def expulsar(codigo: str, jugador_id: int, bd: Session = Depends(obtener_bd)):
    partida = buscar_partida(bd, codigo)
    j = bd.get(Jugador, jugador_id)
    if not j or j.partida_id != partida.id:
        raise HTTPException(404, "Jugador no encontrado en esta partida")
    if partida.estado != "espera":
        raise HTTPException(409, "No se puede expulsar una vez iniciada la partida")

    bd.delete(j)
    bd.commit()

    await salas.difundir(partida.codigo, {"tipo": "expulsado", "jugador_id": jugador_id})
    await difundir_lista(partida.codigo)
    return {"expulsado": jugador_id}

# ---------- Iniciar partida y tableros ----------
@router.post("/{codigo}/iniciar", dependencies=[Depends(requiere_admin)])
async def iniciar_partida(codigo: str, bd: Session = Depends(obtener_bd)):
    codigo = codigo.strip().upper()

    # with_for_update bloquea la fila: dos clics seguidos no generan tableros dobles
    partida = (
        bd.query(Partida).filter(Partida.codigo == codigo).with_for_update().first()
    )
    if not partida:
        raise HTTPException(404, "No existe una partida con ese código")
    if partida.estado != "espera":
        raise HTTPException(409, "La partida ya fue iniciada")

    jugadores = bd.query(Jugador).filter(Jugador.partida_id == partida.id).all()
    if not jugadores:
        raise HTTPException(400, "Aún no hay jugadores en la sala")

    casillas = partida.filas * partida.columnas
    # Solo palabras que tienen una tarjeta física vinculada
    ids_palabras = [i for (i,) in bd.query(TarjetaRfid.palabra_id).all()]
    if len(ids_palabras) < casillas:
        raise HTTPException(
            400,
            f"Se necesitan {casillas} palabras con tarjeta vinculada y solo hay {len(ids_palabras)}",
        )

    # Un tablero distinto por jugador, sin repetir palabras dentro del mismo tablero
    for j in jugadores:
        for posicion, palabra_id in enumerate(random.sample(ids_palabras, casillas)):
            bd.add(Tablero(jugador_id=j.id, palabra_id=palabra_id, posicion=posicion))

    partida.estado = "en_juego"
    partida.iniciada_en = func.now()
    bd.commit()   # todo o nada: si algo falla, no queda una partida a medias

    await salas.difundir(codigo, {"tipo": "inicio", "partida": a_dict(partida)})
    return {"iniciada": True, "jugadores": len(jugadores), "casillas": casillas}


@router.get("/{codigo}/jugadores/{jugador_id}/tablero")
def obtener_tablero(codigo: str, jugador_id: int, bd: Session = Depends(obtener_bd)):
    partida = buscar_partida(bd, codigo)
    j = bd.get(Jugador, jugador_id)
    if not j or j.partida_id != partida.id:
        raise HTTPException(404, "Jugador no encontrado en esta partida")
    if partida.estado == "espera":
        raise HTTPException(409, "La partida aún no ha comenzado")

    filas = (
        bd.query(Tablero, Palabra)
        .join(Palabra, Palabra.id == Tablero.palabra_id)
        .filter(Tablero.jugador_id == j.id)
        .order_by(Tablero.posicion)
        .all()
    )
    return {
        "jugador": jugador_dict(j),
        "filas": partida.filas,
        "columnas": partida.columnas,
        "casillas": [
            {"posicion": t.posicion, "marcada": t.marcada, **palabra_dict(p)}
            for t, p in filas
        ],
    }


# ---------- Detección de tarjetas ----------
# La partida termina cuando hay este número de ganadores que completaron su tablero
# (o cuando ya completaron todos los jugadores, si son menos).
# Ponlo en 1 si quieres que termine con el primer ganador.
GANADORES_PARA_TERMINAR = 3


class DeteccionIn(BaseModel):
    palabra_id: int


def podio_lista(bd: Session, partida: Partida):
    filas = (
        bd.query(Podio, Jugador)
        .join(Jugador, Jugador.id == Podio.jugador_id)
        .filter(Podio.partida_id == partida.id)
        .order_by(Podio.lugar)
        .all()
    )
    return [{"lugar": p.lugar, "jugador": jugador_dict(j)} for p, j in filas]


async def registrar_deteccion(bd: Session, codigo: str, palabra_id: int):
    codigo = codigo.strip().upper()

    # Bloquea la partida: dos tarjetas casi simultáneas se procesan una por una
    partida = (
        bd.query(Partida).filter(Partida.codigo == codigo).with_for_update().first()
    )
    if not partida:
        raise HTTPException(404, "No existe una partida con ese código")
    if partida.estado == "espera":
        raise HTTPException(409, "La partida aún no ha comenzado")
    if partida.estado == "finalizada":
        raise HTTPException(409, "La partida ya terminó")

    palabra = bd.get(Palabra, palabra_id)
    if not palabra:
        raise HTTPException(404, "La palabra no existe")

    ya_salio = (
        bd.query(Deteccion)
        .filter(Deteccion.partida_id == partida.id, Deteccion.palabra_id == palabra.id)
        .first()
    )
    if ya_salio:
        raise HTTPException(409, "Esa tarjeta ya salió en esta partida")

    orden = (
        bd.query(func.coalesce(func.max(Deteccion.orden), 0))
        .filter(Deteccion.partida_id == partida.id)
        .scalar()
    ) + 1
    bd.add(Deteccion(partida_id=partida.id, palabra_id=palabra.id, orden=orden))

    datos_palabra = palabra_dict(palabra)
    try:
        bd.commit()
    except IntegrityError:
        bd.rollback()
        raise HTTPException(409, "Esa tarjeta ya salió en esta partida")

    # Ya NO se marca nada solo: cada jugador marca su casilla con su frijolito
    await salas.difundir(codigo, {"tipo": "tarjeta", "orden": orden, "palabra": datos_palabra})
    return {"orden": orden, "palabra": datos_palabra}


@router.post("/{codigo}/detectar", dependencies=[Depends(requiere_admin)])
async def detectar_tarjeta(codigo: str, datos: DeteccionIn, bd: Session = Depends(obtener_bd)):
    """Simula al lector RFID indicando la palabra de la tarjeta."""
    return await registrar_deteccion(bd, codigo, datos.palabra_id)


class MarcaIn(BaseModel):
    posicion: int = Field(ge=0)
    marcada: bool = True


@router.post("/{codigo}/jugadores/{jugador_id}/marcar")
async def marcar_casilla(
    codigo: str, jugador_id: int, datos: MarcaIn, bd: Session = Depends(obtener_bd)
):
    """El jugador pone o quita su frijolito. Solo se puede marcar una tarjeta que ya salió."""
    codigo = codigo.strip().upper()
    partida = (
        bd.query(Partida).filter(Partida.codigo == codigo).with_for_update().first()
    )
    if not partida:
        raise HTTPException(404, "No existe una partida con ese código")
    if partida.estado != "en_juego":
        raise HTTPException(409, "La partida no está en juego")

    j = bd.get(Jugador, jugador_id)
    if not j or j.partida_id != partida.id:
        raise HTTPException(404, "Jugador no encontrado en esta partida")

    ya_en_podio = {
        i for (i,) in bd.query(Podio.jugador_id).filter(Podio.partida_id == partida.id).all()
    }
    if j.id in ya_en_podio:
        raise HTTPException(409, "Ya completaste tu tablero")

    casilla = (
        bd.query(Tablero)
        .filter(Tablero.jugador_id == j.id, Tablero.posicion == datos.posicion)
        .first()
    )
    if not casilla:
        raise HTTPException(404, "Esa casilla no existe")

    if datos.marcada:
        salio = (
            bd.query(Deteccion.id)
            .filter(
                Deteccion.partida_id == partida.id,
                Deteccion.palabra_id == casilla.palabra_id,
            )
            .first()
        )
        if not salio:
            raise HTTPException(409, "Esa tarjeta todavía no ha salido")

    casilla.marcada = datos.marcada
    bd.flush()

    lugar = None
    terminada = False
    if datos.marcada:
        pendientes = (
            bd.query(func.count(Tablero.id))
            .filter(Tablero.jugador_id == j.id, Tablero.marcada.is_(False))
            .scalar()
        )
        if pendientes == 0:  # hizo lotería: la partida termina ya
            lugar = 1
            terminada = True
            bd.add(Podio(partida_id=partida.id, jugador_id=j.id, lugar=1))

            # 2.º y 3.º lugar: los que llevan más casillas marcadas
            avance = (
                bd.query(
                    Jugador.id,
                    func.sum(case((Tablero.marcada.is_(True), 1), else_=0)).label("marcadas"),
                )
                .join(Tablero, Tablero.jugador_id == Jugador.id)
                .filter(Jugador.partida_id == partida.id, Jugador.id != j.id)
                .group_by(Jugador.id)
                .order_by(desc("marcadas"), Jugador.id)
                .limit(2)
                .all()
            )
            for puesto, (jid, _) in enumerate(avance, start=2):
                bd.add(Podio(partida_id=partida.id, jugador_id=jid, lugar=puesto))

            partida.estado = "finalizada"
            partida.finalizada_en = func.now()

    try:
        bd.commit()
    except IntegrityError:
        bd.rollback()
        raise HTTPException(409, "No se pudo guardar, intenta de nuevo")

    if lugar:
        podio = podio_lista(bd, partida)
        nuevo = next(g for g in podio if g["lugar"] == lugar)
        await salas.difundir(codigo, {"tipo": "ganador", **nuevo})
        if terminada:
            await salas.difundir(codigo, {"tipo": "fin", "podio": podio})

    return {
        "posicion": datos.posicion,
        "marcada": datos.marcada,
        "completo": lugar is not None,
        "lugar": lugar,
        "terminada": terminada,
    }


@router.post("/{codigo}/simular", dependencies=[Depends(requiere_admin)])
async def simular_tarjeta(codigo: str, bd: Session = Depends(obtener_bd)):
    """Saca una tarjeta al azar de las que aún no han salido (solo para pruebas)."""
    partida = buscar_partida(bd, codigo)
    if partida.estado != "en_juego":
        raise HTTPException(409, "La partida no está en juego")

    ya_salieron = bd.query(Deteccion.palabra_id).filter(Deteccion.partida_id == partida.id)
    candidatas = [
        i for (i,) in bd.query(Palabra.id).filter(~Palabra.id.in_(ya_salieron)).all()
    ]
    if not candidatas:
        raise HTTPException(409, "Ya salieron todas las tarjetas")

    bd.commit()  # cierra la lectura anterior para ver datos frescos al bloquear
    return await registrar_deteccion(bd, codigo, random.choice(candidatas))


@router.get("/{codigo}/detecciones")
def listar_detecciones(codigo: str, bd: Session = Depends(obtener_bd)):
    """Historial de tarjetas: sirve para que una pantalla recupere lo ya detectado."""
    partida = buscar_partida(bd, codigo)
    filas = (
        bd.query(Deteccion, Palabra)
        .join(Palabra, Palabra.id == Deteccion.palabra_id)
        .filter(Deteccion.partida_id == partida.id)
        .order_by(Deteccion.orden)
        .all()
    )
    return [{"orden": d.orden, "palabra": palabra_dict(p)} for d, p in filas]


@router.get("/{codigo}/podio")
def obtener_podio(codigo: str, bd: Session = Depends(obtener_bd)):
    partida = buscar_partida(bd, codigo)
    return {"estado": partida.estado, "podio": podio_lista(bd, partida)}


# ---------- WebSocket de la sala ----------
@router.websocket("/{codigo}/ws")
async def sala_ws(ws: WebSocket, codigo: str, rol: str = "jugador", jugador_id: int | None = None):
    codigo = codigo.strip().upper()

    # Valida antes de aceptar la conexión
    bd = SessionLocal()
    try:
        partida = bd.query(Partida).filter(Partida.codigo == codigo).first()
        valido = partida is not None and rol in ("admin", "jugador")
        if valido and rol == "jugador":
            j = bd.get(Jugador, jugador_id) if jugador_id else None
            valido = j is not None and j.partida_id == partida.id
    finally:
        bd.close()

    if not valido:
        await ws.close(code=4404)
        return

    await salas.conectar(codigo, ws, rol, jugador_id if rol == "jugador" else None)
    try:
        await difundir_lista(codigo)
        while True:
            await ws.receive_text()   # mantiene viva la conexión
    except WebSocketDisconnect:
        pass
    finally:
        salas.desconectar(codigo, ws)
        await difundir_lista(codigo)