"""Crea (o cambia la contraseña de) un administrador.

Uso, dentro de la carpeta backend y con el entorno virtual activado:
    python crear_admin.py
"""
import getpass

from sqlalchemy import text

from auth import hash_password
from database import SessionLocal

usuario = input("Nombre de usuario: ").strip()
if len(usuario) < 3:
    raise SystemExit("El usuario debe tener al menos 3 caracteres.")

password = getpass.getpass("Contraseña (mínimo 10 caracteres): ")
if len(password) < 10:
    raise SystemExit("La contraseña es muy corta (mínimo 10 caracteres).")
if password != getpass.getpass("Repite la contraseña: "):
    raise SystemExit("Las contraseñas no coinciden.")

bd = SessionLocal()
try:
    h = hash_password(password)
    existe = bd.execute(text("SELECT id FROM administradores WHERE usuario = :u"), {"u": usuario}).first()
    if existe:
        bd.execute(text("UPDATE administradores SET password_hash = :h WHERE usuario = :u"), {"h": h, "u": usuario})
        print(f"Contraseña actualizada para «{usuario}».")
    else:
        bd.execute(text("INSERT INTO administradores (usuario, password_hash) VALUES (:u, :h)"), {"u": usuario, "h": h})
        print(f"Administrador «{usuario}» creado.")
    bd.commit()
finally:
    bd.close()