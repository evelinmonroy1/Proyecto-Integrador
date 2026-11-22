import os
import re
import secrets
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import obtener_bd
from models import Palabra, TarjetaRfid, Partida
from routers.partidas import registrar_deteccion

router = APIRouter(prefix="/api/tarjetas", tags=["Tarjetas RFID"])
router_lector = APIRouter(prefix="/api/lector", tags=["Lector RFID"])

SEGUNDOS_REGISTRO = 60
PATRON_UID = re.compile(r"^[0-9A-F]{8,20}$")

# Estado en memoria (se reinicia si reinicias el servidor, y está bien así)
registro = {"palabra_id": None, "expira": 0.0, "aviso": None, "resultado": None}
ultima_lectura = {"uid": None, "hora": 0.0}


class RegistroIn(BaseModel):
    palabra_id: int


class LecturaIn(BaseModel):
    uid: str


# ---------- Funciones de apoyo ----------
def normalizar_uid(uid: str) -> str:
    """Deja el UID en mayúsculas y sin espacios, dos puntos ni guiones."""
    limpio = re.sub(r"[\s:\-]", "", uid).upper()
    if not PATRON_UID.match(limpio):
        raise HTTPException(400, "UID no válido")
    return limpio


def revisar_clave(clave: str):
    esperada = os.getenv("LECTOR_KEY", "")
    if not esperada:
        raise HTTPException(503, "Falta configurar LECTOR_KEY en el archivo .env")
    if not secrets.compare_digest(clave.encode(), esperada.encode()):
        raise HTTPException(401, "Clave del lector incorrecta")


def registro_activo() -> bool:
    return registro["palabra_id"] is not None and time.time() < registro["expira"]


def vincular(bd: Session, uid: str, tarjeta_existente):
    """Asigna el UID leído a la palabra que el administrador está registrando."""
    palabra_id = registro["palabra_id"]
    palabra = bd.get(Palabra, palabra_id)
    if not palabra:
        registro.update(palabra_id=None, aviso=None)
        raise HTTPException(404, "La palabra ya no existe")
    nombre = palabra.mazahua

    if tarjeta_existente and tarjeta_existente.palabra_id != palabra_id:
        otra = bd.get(Palabra, tarjeta_existente.palabra_id)
        registro["aviso"] = f"Esa tarjeta ya está vinculada a «{otra.mazahua}»"
        raise HTTPException(409, registro["aviso"])

    if not tarjeta_existente:
        try:
            # una palabra solo tiene una tarjeta: si ya tenía otra, se reemplaza
            bd.query(TarjetaRfid).filter(TarjetaRfid.palabra_id == palabra_id).delete()
            bd.add(TarjetaRfid(uid=uid, palabra_id=palabra_id))
            bd.commit()
        except IntegrityError:
            bd.rollback()
            raise HTTPException(409, "No se pudo vincular la tarjeta, intenta de nuevo")

    registro.update(
        palabra_id=None,
        aviso=None,
        resultado={"ok": True, "uid": uid, "palabra_id": palabra_id},
    )
    return {"registrada": True, "uid": uid, "palabra": nombre}


# ---------- Para la pantalla del administrador ----------
@router.get("")
def listar_tarjetas(bd: Session = Depends(obtener_bd)):
    return [{"palabra_id": t.palabra_id, "uid": t.uid} for t in bd.query(TarjetaRfid).all()]


@router.post("/registro")
def iniciar_registro(datos: RegistroIn, bd: Session = Depends(obtener_bd)):
    palabra = bd.get(Palabra, datos.palabra_id)
    if not palabra:
        raise HTTPException(404, "La palabra no existe")
    registro.update(
        palabra_id=palabra.id,
        expira=time.time() + SEGUNDOS_REGISTRO,
        aviso=None,
        resultado=None,
    )
    return {"palabra_id": palabra.id, "segundos": SEGUNDOS_REGISTRO}


@router.get("/registro")
def estado_registro():
    if registro["palabra_id"] is not None and time.time() >= registro["expira"]:
        registro["palabra_id"] = None  # se acabó el tiempo
    activo = registro["palabra_id"] is not None
    return {
        "activo": activo,
        "palabra_id": registro["palabra_id"],
        "restan": max(0, int(registro["expira"] - time.time())) if activo else 0,
        "aviso": registro["aviso"],
        "resultado": registro["resultado"],
    }


@router.delete("/registro")
def cancelar_registro():
    registro.update(palabra_id=None, aviso=None)
    return {"cancelado": True}


@router.get("/ultima")
def ultima(bd: Session = Depends(obtener_bd)):
    """Última tarjeta que leyó el lector. Sirve para comprobar que funciona."""
    uid = ultima_lectura["uid"]
    if not uid:
        return {"uid": None, "hace": None, "palabra": None}
    t = bd.query(TarjetaRfid).filter(TarjetaRfid.uid == uid).first()
    palabra = bd.get(Palabra, t.palabra_id) if t else None
    return {
        "uid": uid,
        "hace": int(time.time() - ultima_lectura["hora"]),
        "palabra": palabra.mazahua if palabra else None,
    }


# Esta ruta va después de las de /registro y /ultima para no confundirse con ellas
@router.delete("/{palabra_id}")
def desvincular(palabra_id: int, bd: Session = Depends(obtener_bd)):
    t = bd.query(TarjetaRfid).filter(TarjetaRfid.palabra_id == palabra_id).first()
    if not t:
        raise HTTPException(404, "Esa palabra no tiene tarjeta vinculada")
    bd.delete(t)
    bd.commit()
    return {"desvinculada": palabra_id}


# ---------- Para el lector (ESP32) ----------
@router_lector.post("/tarjeta")
async def recibir_lectura(
    datos: LecturaIn,
    x_api_key: str = Header(default=""),
    bd: Session = Depends(obtener_bd),
):
    revisar_clave(x_api_key)
    uid = normalizar_uid(datos.uid)
    ultima_lectura.update(uid=uid, hora=time.time())

    tarjeta = bd.query(TarjetaRfid).filter(TarjetaRfid.uid == uid).first()

    # Modo registro: el administrador está vinculando una tarjeta
    if registro_activo():
        return vincular(bd, uid, tarjeta)

    # Modo juego: la tarjeta se "saca" en la partida que esté en curso
    if not tarjeta:
        raise HTTPException(404, "Tarjeta no registrada")

    partida = (
        bd.query(Partida)
        .filter(Partida.estado == "en_juego")
        .order_by(Partida.id.desc())
        .first()
    )
    if not partida:
        raise HTTPException(409, "No hay una partida en juego")

    palabra_id, codigo = tarjeta.palabra_id, partida.codigo
    bd.commit()  # cierra la lectura anterior para ver datos frescos al bloquear
    return await registrar_deteccion(bd, codigo, palabra_id)