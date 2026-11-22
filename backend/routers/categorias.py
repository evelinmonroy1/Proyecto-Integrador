from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import obtener_bd
from models import Categoria

router = APIRouter(prefix="/api/categorias", tags=["Categorías"])


@router.get("")
def listar_categorias(bd: Session = Depends(obtener_bd)):
    categorias = bd.query(Categoria).order_by(Categoria.nombre).all()
    return [{"id": c.id, "nombre": c.nombre} for c in categorias]


@router.post("", status_code=201)
def crear_categoria(nombre: str, bd: Session = Depends(obtener_bd)):
    nombre = nombre.strip()
    if not nombre:
        raise HTTPException(400, "El nombre no puede estar vacío")
    if bd.query(Categoria).filter(Categoria.nombre == nombre).first():
        raise HTTPException(409, "Esa categoría ya existe")
    c = Categoria(nombre=nombre)
    bd.add(c)
    bd.commit()
    bd.refresh(c)
    return {"id": c.id, "nombre": c.nombre}