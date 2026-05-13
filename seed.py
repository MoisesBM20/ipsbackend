"""
Script de seed: crea datos iniciales en la base de datos.
Ejecutar UNA SOLA VEZ para inicializar el sistema.

Uso: python seed.py
"""
from database import SessionLocal, create_tables
from models.user import User, UserRole
from core.security import hash_password

def seed():
    create_tables()
    db = SessionLocal()

    # Verificar si ya existe el admin
    existing = db.query(User).filter(User.email == "admin@ipscuidandodeti.com").first()
    if existing:
        print("⚠️  El usuario admin ya existe. Seed omitido.")
        db.close()
        return

    # Crear usuario administrador inicial
    admin = User(
        email="admin@ipscuidandodeti.com",
        password_hash=hash_password("Admin2024!"),
        full_name="Administrador Sistema",
        document_number="0000000001",
        role=UserRole.ADMIN,
        is_active=True,
    )

    # Crear un doctor de ejemplo
    doctor = User(
        email="doctor@ipscuidandodeti.com",
        password_hash=hash_password("Doctor2024!"),
        full_name="Dr. Juan Pérez",
        document_number="12345678",
        phone="3001234567",
        role=UserRole.DOCTOR,
        specialty="Medicina General",
        registration_number="RM-001234",
        is_active=True,
    )

    # Crear una recepcionista de ejemplo
    receptionist = User(
        email="recepcion@ipscuidandodeti.com",
        password_hash=hash_password("Recepcion2024!"),
        full_name="María García",
        document_number="87654321",
        phone="3009876543",
        role=UserRole.RECEPTIONIST,
        is_active=True,
    )

    db.add_all([admin, doctor, receptionist])
    db.commit()

    print("✅ Seed completado. Usuarios creados:")
    print("   📧 admin@ipscuidandodeti.com  |  🔑 Admin2024!")
    print("   📧 doctor@ipscuidandodeti.com  |  🔑 Doctor2024!")
    print("   📧 recepcion@ipscuidandodeti.com  |  🔑 Recepcion2024!")
    print("\n⚠️  IMPORTANTE: Cambia las contraseñas al iniciar sesión por primera vez.")
    db.close()


if __name__ == "__main__":
    seed()
