"""Seguridad del administrador: login con usuario y contraseña.

No necesita instalar nada nuevo: usa solo la librería estándar de Python.
- Las contraseñas se guardan con scrypt (nunca en texto).
- La sesión es un token firmado que dura SESION_HORAS horas.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import obtener_bd

SESION_HORAS = 8
MAX_INTENTOS = 5          # intentos fallidos permitidos...
VENTANA_SEG = 300         # ...en 5 minutos, por usuario + dirección IP


# ---------- Clave secreta (AUTH_SECRET en backend/.env) ----------
def _leer_env(nombre: str):
    valor = os.getenv(nombre)
    if valor:
        return valor
    ruta = Path(__file__).resolve().parent / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea.startswith(nombre + "="):
                return linea.split("=", 1)[1].strip().strip('"').strip("'")
    return None


_SECRETO = _leer_env("AUTH_SECRET")
if not _SECRETO or len(_SECRETO) < 32:
    # Sin clave en el .env se crea una al azar: funciona, pero las sesiones
    # se cierran cada vez que reinicias el servidor.
    print("[auth] AVISO: falta AUTH_SECRET (mínimo 32 caracteres) en backend/.env")
    _SECRETO = secrets.token_hex(32)
_SECRETO = _SECRETO.encode()


# ---------- Contraseñas ----------
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=sal, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${sal.hex()}${h.hex()}"


def verificar_password(password: str, guardado: str) -> bool:
    try:
        _, n, r, p, sal, h = guardado.split("$")
        calculado = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(sal), n=int(n), r=int(r), p=int(p), dklen=32
        )
        return hmac.compare_digest(calculado, bytes.fromhex(h))
    except Exception:
        return False


_HASH_FALSO = hash_password("relleno-para-igualar-tiempos")


# ---------- Tokens ----------
def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _des64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def crear_token(admin_id: int, usuario: str) -> str:
    carga = _b64(json.dumps({"id": admin_id, "u": usuario, "exp": int(time.time()) + SESION_HORAS * 3600}).encode())
    firma = _b64(hmac.new(_SECRETO, carga.encode(), hashlib.sha256).digest())
    return f"{carga}.{firma}"


def leer_token(token: str):
    try:
        carga, firma = token.split(".")
        esperada = _b64(hmac.new(_SECRETO, carga.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(firma, esperada):
            return None
        datos = json.loads(_des64(carga))
        if datos["exp"] < time.time():
            return None
        return datos
    except Exception:
        return None


# ---------- Dependencia para proteger rutas ----------
# HTTPBearer hace que /docs muestre el botón "Authorize" (pegas el token una sola vez)
_esquema_bearer = HTTPBearer(auto_error=False)


def requiere_admin(
    credenciales: HTTPAuthorizationCredentials = Depends(_esquema_bearer),
    bd: Session = Depends(obtener_bd),
):
    if not credenciales or credenciales.scheme.lower() != "bearer":
        raise HTTPException(401, "Inicia sesión como administrador")
    datos = leer_token(credenciales.credentials.strip())
    if not datos:
        raise HTTPException(401, "La sesión expiró; vuelve a iniciar sesión")
    existe = bd.execute(text("SELECT id FROM administradores WHERE id = :i"), {"i": datos["id"]}).first()
    if not existe:
        raise HTTPException(401, "Administrador no válido")
    return datos


# ---------- Rutas ----------
router = APIRouter(prefix="/api/auth", tags=["Autenticación"])
_fallos: dict[str, list[float]] = {}


class LoginIn(BaseModel):
    usuario: str
    password: str


@router.post("/login")
def login(datos: LoginIn, request: Request, bd: Session = Depends(obtener_bd)):
    clave = f"{request.client.host if request.client else '?'}|{datos.usuario.strip().lower()}"
    ahora = time.time()
    recientes = [t for t in _fallos.get(clave, []) if ahora - t < VENTANA_SEG]
    _fallos[clave] = recientes
    if len(recientes) >= MAX_INTENTOS:
        raise HTTPException(429, "Demasiados intentos. Espera unos minutos.")

    fila = bd.execute(
        text("SELECT id, password_hash FROM administradores WHERE usuario = :u"),
        {"u": datos.usuario.strip()},
    ).first()
    ok = verificar_password(datos.password, fila[1] if fila else _HASH_FALSO)
    if not fila or not ok:
        _fallos[clave].append(ahora)
        raise HTTPException(401, "Usuario o contraseña incorrectos")

    _fallos.pop(clave, None)
    return {"token": crear_token(fila[0], datos.usuario.strip()), "usuario": datos.usuario.strip(), "horas": SESION_HORAS}


@router.get("/yo")
def quien_soy(admin=Depends(requiere_admin)):
    return {"usuario": admin["u"]}