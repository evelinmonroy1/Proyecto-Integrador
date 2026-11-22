import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

import models  # noqa: F401  (registra las tablas)
from auth import router as auth_router, requiere_admin, hash_password
from database import obtener_bd, engine, Base, SessionLocal
from models import Administrador
from routers import palabras, categorias, partidas, tarjetas, galeria
from seed import importar_si_vacio


def preparar_base_de_datos():
    """Al arrancar: crea las tablas que falten, carga los datos iniciales y el administrador."""
    Base.metadata.create_all(engine)
    bd = SessionLocal()
    try:
        print("[arranque] datos iniciales:", importar_si_vacio(bd))

        usuario = os.getenv("ADMIN_USER", "").strip()
        clave = os.getenv("ADMIN_PASSWORD", "")
        if usuario and clave:
            existe = bd.query(Administrador).filter(Administrador.usuario == usuario).first()
            if not existe:
                if len(clave) < 10:
                    print("[arranque] ADMIN_PASSWORD es muy corta (mínimo 10): no se creó el administrador")
                else:
                    bd.add(Administrador(usuario=usuario, password_hash=hash_password(clave)))
                    bd.commit()
                    print(f"[arranque] administrador «{usuario}» creado")
    finally:
        bd.close()


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    try:
        preparar_base_de_datos()
    except Exception as e:  # no tumbar el servidor: /api/salud/bd mostrará el problema
        print("[arranque] ERROR preparando la base de datos:", repr(e))
    yield


app = FastAPI(title="Lotería Mazahua", lifespan=ciclo_de_vida)

# Solo hace falta cuando la página corre aparte (npm run dev, puerto 4321).
# En la nube la página y la API salen del mismo servidor y no hay CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+):4321",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Archivos subidos (imágenes y audios)
MEDIA = Path(__file__).resolve().parent / "media"
MEDIA.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA), name="media")

# Login del administrador
app.include_router(auth_router)

# Solo administrador: exigen sesión
app.include_router(palabras.router, dependencies=[Depends(requiere_admin)])
app.include_router(categorias.router, dependencies=[Depends(requiere_admin)])
app.include_router(tarjetas.router, dependencies=[Depends(requiere_admin)])

# Jugadores (abiertas; las de administrador van protegidas dentro de partidas.py)
app.include_router(partidas.router)
app.include_router(partidas.router_avatares)

# Galería pública (solo lectura: imágenes y audios de las palabras)
app.include_router(galeria.router)

# Lector RFID (ESP32): NO usa sesión, se identifica con su propia clave
app.include_router(tarjetas.router_lector)


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}


@app.get("/api/salud/bd")
def salud_bd(bd: Session = Depends(obtener_bd)):
    total = bd.execute(text("SELECT COUNT(*) FROM palabras")).scalar()
    return {"bd": "conectada", "palabras": total}


# ---------- La página (Astro compilada) ----------
# Si existe la carpeta dist (npm run build), este mismo servidor la entrega.
# Debe ir al final, después de todas las rutas de la API.
FRONTEND = Path(os.getenv("FRONTEND_DIR", Path(__file__).resolve().parent.parent / "dist"))
if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="web")
