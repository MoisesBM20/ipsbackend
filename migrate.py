"""
Migración manual: agrega columnas nuevas a la BD sin borrar datos.
Ejecutar cuando se actualiza el modelo y hay error de columna faltante.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ips_cuidando.db")

MIGRATIONS = [
    # (descripcion, sql)
    (
        "Agregar user_id a patients",
        "ALTER TABLE patients ADD COLUMN user_id INTEGER REFERENCES users(id)"
    ),
]

def run_migrations():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Obtener columnas actuales de cada tabla
    def columns_of(table):
        cursor.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}

    for desc, sql in MIGRATIONS:
        try:
            cursor.execute(sql)
            conn.commit()
            print(f"  OK  {desc}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print(f"  --  {desc} (ya existe, omitida)")
            else:
                print(f"  ERR {desc}: {e}")

    conn.close()
    print("\nMigración completada.")

if __name__ == "__main__":
    run_migrations()
