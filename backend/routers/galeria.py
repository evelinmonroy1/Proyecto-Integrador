"""Galería pública: solo LECTURA de las palabras y sus imágenes.

No necesita sesión de administrador y no modifica nada de la base de datos,
así que no afecta al juego. La usan las páginas /galeria y /lengua.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import obtener_bd
from models import Palabra, Categoria

router = APIRouter(prefix="/api/galeria", tags=["Galería (pública)"])


@router.get("")
def galeria(bd: Session = Depends(obtener_bd)):
    categorias = bd.query(Categoria).order_by(Categoria.id).all()
    palabras = bd.query(Palabra).order_by(Palabra.id).all()
    return {
        "categorias": [{"id": c.id, "nombre": c.nombre} for c in categorias],
        "palabras": [
            {
                "id": p.id,
                "mazahua": p.mazahua,
                "espanol": p.espanol,
                "categoria_id": p.categoria_id,
                "imagen_url": f"/media/imagenes/{p.imagen}" if p.imagen else None,
                "audio_url": f"/media/audios/{p.audio}" if p.audio else None,
            }
            for p in palabras
        ],
    }
