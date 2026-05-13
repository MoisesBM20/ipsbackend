"""
Reactiva todas las cuentas de usuario desactivadas.
Uso: python reactivate.py
"""
from database import SessionLocal
# Importar todos los modelos para que SQLAlchemy resuelva las relaciones
import models.user
import models.patient
import models.appointment
import models.availability
import models.clinical_record
import models.rips
from models.user import User

def reactivate():
    db = SessionLocal()
    users = db.query(User).all()

    if not users:
        print("No hay usuarios en la base de datos.")
        db.close()
        return

    updated = 0
    for u in users:
        print(f"  {'ACTIVO  ' if u.is_active else 'INACTIVO'}  {u.email}  ({u.role.value})")
        if not u.is_active:
            u.is_active = True
            updated += 1

    if updated:
        db.commit()
        print(f"\nSe reactivaron {updated} cuenta(s).")
    else:
        print("\nTodas las cuentas ya estaban activas.")

    db.close()

if __name__ == "__main__":
    reactivate()
