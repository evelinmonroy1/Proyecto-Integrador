"""Datos iniciales: categorías, palabras y tarjetas RFID.

- exportar():  guarda lo que hay en TU base de datos en datos_iniciales.json
               (se corre una vez en tu computadora: python seed.py)
- importar_si_vacio(): al arrancar en la nube, si la base está vacía, la llena
               con ese archivo. Así no hay que copiar tablas a mano.
"""
import json
from pathlib import Path

from sqlalchemy.orm import Session

from models import Categoria, Palabra, TarjetaRfid

ARCHIVO = Path(__file__).resolve().parent / "datos_iniciales.json"


def exportar(bd: Session, ruta: Path = ARCHIVO) -> dict:
    datos = {
        "categorias": [{"id": c.id, "nombre": c.nombre} for c in bd.query(Categoria).order_by(Categoria.id)],
        "palabras": [
            {
                "id": p.id,
                "mazahua": p.mazahua,
                "espanol": p.espanol,
                "categoria_id": p.categoria_id,
                "imagen": p.imagen,
                "audio": p.audio,
            }
            for p in bd.query(Palabra).order_by(Palabra.id)
        ],
        "tarjetas_rfid": [
            {"id": t.id, "uid": t.uid, "palabra_id": t.palabra_id}
            for t in bd.query(TarjetaRfid).order_by(TarjetaRfid.id)
        ],
    }
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return {k: len(v) for k, v in datos.items()}


def _ajustar_contadores(bd: Session) -> None:
    """En PostgreSQL, al insertar con id fijo el contador (secuencia) no avanza.
    Esto lo pone al día para que las palabras nuevas no choquen con las existentes."""
    if bd.get_bind().dialect.name != "postgresql":
        return
    from sqlalchemy import text

    for tabla in ("categorias", "palabras", "tarjetas_rfid"):
        bd.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {tabla}), 0) + 1, false)"
        ))
    bd.commit()


def importar_si_vacio(bd: Session, ruta: Path = ARCHIVO) -> str:
    if not ruta.exists():
        return "sin archivo de datos iniciales"
    if bd.query(Palabra).first() or bd.query(Categoria).first():
        return "la base ya tiene datos"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    for c in datos.get("categorias", []):
        bd.add(Categoria(**c))
    bd.flush()
    for p in datos.get("palabras", []):
        bd.add(Palabra(**p))
    bd.flush()
    for t in datos.get("tarjetas_rfid", []):
        bd.add(TarjetaRfid(**t))
    bd.commit()
    _ajustar_contadores(bd)
    return f"importadas {len(datos.get('palabras', []))} palabras"


if __name__ == "__main__":
    from database import SessionLocal

    bd = SessionLocal()
    try:
        print("Exportado a", ARCHIVO.name, "->", exportar(bd))
    finally:
        bd.close()