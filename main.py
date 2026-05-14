from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from core.config import settings

# Importar todos los routers
from routers import auth, users, patients, availability, appointments, clinical_records, rips, dashboard, public, patient_portal, audit, services

app = FastAPI(
    title="CUIDANDO DE TI CyE IPS SAS - API",
    version="1.0.0",
    redirect_slashes=False,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rutas ─────────────────────────────────────────────────────────────────────
# Rutas públicas (sin autenticación) — primero para mayor visibilidad en /docs
app.include_router(public.router)

# Rutas del panel administrativo (requieren JWT)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(patients.router)
app.include_router(availability.router)
app.include_router(appointments.router)
app.include_router(clinical_records.router)
app.include_router(rips.router)
app.include_router(dashboard.router)
app.include_router(patient_portal.router)
app.include_router(audit.router)
app.include_router(services.router)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """Crea las tablas en la BD al iniciar la aplicación."""
    create_tables()
    print("✅ Tablas creadas / verificadas")
    print("📋 Documentación disponible en: http://localhost:8000/docs")


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "API Panel Administrativo - CUIDANDO DE TI CyE IPS SAS",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Root"])
def health_check():
    return {"status": "ok"}
