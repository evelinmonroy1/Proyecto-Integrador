from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import obtener_bd
from models import Palabra, Categoria

router = APIRouter(prefix="/api/palabras", tags=["Palabras"])

BASE = Path(__file__).resolve().parent.parent / "media"
DIR_IMG = BASE / "imagenes"
DIR_AUDIO = BASE / "audios"
DIR_IMG.mkdir(parents=True, exist_ok=True)
DIR_AUDIO.mkdir(parents=True, exist_ok=True)

EXT_IMG = {".png", ".jpg", ".jpeg", ".webp"}
EXT_AUDIO = {".mp3", ".ogg", ".wav"}


def a_dict(p: Palabra):
    return {
        "id": p.id,
        "mazahua": p.mazahua,
        "espanol": p.espanol,
        "categoria_id": p.categoria_id,
        "imagen_url": f"/media/imagenes/{p.imagen}" if p.imagen else None,
        "audio_url": f"/media/audios/{p.audio}" if p.audio else None,
    }


def validar(archivo: Optional[UploadFile], extensiones: set):
    """Revisa el formato ANTES de tocar la base de datos."""
    if archivo and archivo.filename:
        ext = Path(archivo.filename).suffix.lower()
        if ext not in extensiones:
            raise HTTPException(400, f"Formato no permitido ({ext}). Usa: {', '.join(sorted(extensiones))}")


def guardar(archivo: UploadFile, carpeta: Path, nombre_base: str) -> str:
    ext = Path(archivo.filename).suffix.lower()
    nombre = f"{nombre_base}{ext}"
    with open(carpeta / nombre, "wb") as f:
        f.write(archivo.file.read())
    return nombre


def borrar(carpeta: Path, nombre: Optional[str]):
    if nombre:
        (carpeta / nombre).unlink(missing_ok=True)


def revisar_categoria(bd: Session, categoria_id: Optional[int]):
    if categoria_id is not None and not bd.get(Categoria, categoria_id):
        raise HTTPException(400, "La categoría no existe")


def tiene_archivo(a: Optional[UploadFile]) -> bool:
    return bool(a and a.filename)


# ---------- Listar y buscar ----------
@router.get("")
def listar_palabras(
    q: Optional[str] = None,
    categoria_id: Optional[int] = None,
    bd: Session = Depends(obtener_bd),
):
    consulta = bd.query(Palabra)
    if q:
        patron = f"%{q.strip()}%"
        consulta = consulta.filter(or_(Palabra.mazahua.like(patron), Palabra.espanol.like(patron)))
    if categoria_id:
        consulta = consulta.filter(Palabra.categoria_id == categoria_id)
    return [a_dict(p) for p in consulta.order_by(Palabra.mazahua).all()]


# ---------- Obtener una ----------
@router.get("/{palabra_id}")
def obtener_palabra(palabra_id: int, bd: Session = Depends(obtener_bd)):
    p = bd.get(Palabra, palabra_id)
    if not p:
        raise HTTPException(404, "Palabra no encontrada")
    return a_dict(p)


# ---------- Crear ----------
@router.post("", status_code=201)
def crear_palabra(
    mazahua: str = Form(...),
    espanol: str = Form(...),
    categoria_id: Optional[int] = Form(None),
    imagen: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    bd: Session = Depends(obtener_bd),
):
    mazahua, espanol = mazahua.strip(), espanol.strip()
    if not mazahua or not espanol:
        raise HTTPException(400, "La palabra y su traducción son obligatorias")
    validar(imagen, EXT_IMG)
    validar(audio, EXT_AUDIO)
    revisar_categoria(bd, categoria_id)

    p = Palabra(mazahua=mazahua, espanol=espanol, categoria_id=categoria_id)
    bd.add(p)
    bd.flush()  # obtiene el id sin cerrar la transacción

    if tiene_archivo(imagen):
        p.imagen = guardar(imagen, DIR_IMG, str(p.id))
    if tiene_archivo(audio):
        p.audio = guardar(audio, DIR_AUDIO, str(p.id))

    bd.commit()
    bd.refresh(p)
    return a_dict(p)


# ---------- Editar ----------
@router.put("/{palabra_id}")
def editar_palabra(
    palabra_id: int,
    mazahua: Optional[str] = Form(None),
    espanol: Optional[str] = Form(None),
    categoria_id: Optional[int] = Form(None),
    imagen: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    bd: Session = Depends(obtener_bd),
):
    p = bd.get(Palabra, palabra_id)
    if not p:
        raise HTTPException(404, "Palabra no encontrada")
    validar(imagen, EXT_IMG)
    validar(audio, EXT_AUDIO)
    revisar_categoria(bd, categoria_id)

    if mazahua is not None and mazahua.strip():
        p.mazahua = mazahua.strip()
    if espanol is not None and espanol.strip():
        p.espanol = espanol.strip()
    if categoria_id is not None:
        p.categoria_id = categoria_id

    if tiene_archivo(imagen):
        borrar(DIR_IMG, p.imagen)
        p.imagen = guardar(imagen, DIR_IMG, str(p.id))
    if tiene_archivo(audio):
        borrar(DIR_AUDIO, p.audio)
        p.audio = guardar(audio, DIR_AUDIO, str(p.id))

    bd.commit()
    bd.refresh(p)
    return a_dict(p)

# ---------- Agregar o cambiar solo la imagen ----------
@router.post("/{palabra_id}/imagen")
def subir_imagen(
    palabra_id: int,
    imagen: UploadFile = File(...),
    bd: Session = Depends(obtener_bd),
):
    p = bd.get(Palabra, palabra_id)
    if not p:
        raise HTTPException(404, "Palabra no encontrada")
    if not tiene_archivo(imagen):
        raise HTTPException(400, "Falta la imagen")
    validar(imagen, EXT_IMG)
    borrar(DIR_IMG, p.imagen)
    p.imagen = guardar(imagen, DIR_IMG, str(p.id))
    bd.commit()
    bd.refresh(p)
    return a_dict(p)


# ---------- Agregar o cambiar solo el audio ----------
@router.post("/{palabra_id}/audio")
def subir_audio(
    palabra_id: int,
    audio: UploadFile = File(...),
    bd: Session = Depends(obtener_bd),
):
    p = bd.get(Palabra, palabra_id)
    if not p:
        raise HTTPException(404, "Palabra no encontrada")
    if not tiene_archivo(audio):
        raise HTTPException(400, "Falta el audio")
    validar(audio, EXT_AUDIO)
    borrar(DIR_AUDIO, p.audio)
    p.audio = guardar(audio, DIR_AUDIO, str(p.id))
    bd.commit()
    bd.refresh(p)
    return a_dict(p)


# ---------- Quitar solo la imagen ----------
@router.delete("/{palabra_id}/imagen")
def quitar_imagen(palabra_id: int, bd: Session = Depends(obtener_bd)):
    p = bd.get(Palabra, palabra_id)
    if not p:
        raise HTTPException(404, "Palabra no encontrada")
    borrar(DIR_IMG, p.imagen)
    p.imagen = None
    bd.commit()
    bd.refresh(p)
    return a_dict(p)


# ---------- Quitar solo el audio ----------
@router.delete("/{palabra_id}/audio")
def quitar_audio(palabra_id: int, bd: Session = Depends(obtener_bd)):
    p = bd.get(Palabra, palabra_id)
    if not p:
        raise HTTPException(404, "Palabra no encontrada")
    borrar(DIR_AUDIO, p.audio)
    p.audio = None
    bd.commit()
    bd.refresh(p)
    return a_dict(p)

# ---------- Eliminar ----------
@router.delete("/{palabra_id}")
def eliminar_palabra(palabra_id: int, bd: Session = Depends(obtener_bd)):
    p = bd.get(Palabra, palabra_id)
    if not p:
        raise HTTPException(404, "Palabra no encontrada")
    imagen, audio = p.imagen, p.audio
    try:
        bd.delete(p)
        bd.commit()
    except IntegrityError:
        bd.rollback()
        raise HTTPException(409, "No se puede eliminar: la palabra ya se usó en partidas")
    borrar(DIR_IMG, imagen)
    borrar(DIR_AUDIO, audio)
    return {"eliminada": palabra_id}