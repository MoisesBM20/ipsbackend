# API - CUIDANDO DE TI CyE IPS SAS

Backend FastAPI. Ambos proyectos dentro de `IPSCuidando/`.

```
IPSCuidando/
├── frontend/    ← Angular   (ng serve  → puerto 4200)
└── backend/     ← FastAPI   (uvicorn   → puerto 8000)
```

## Requisitos
- Python 3.11+

## Instalación y arranque

```bash
# 1. Entrar a la carpeta del backend
cd IPSCuidando/backend

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Edita .env con tus valores reales

# 5. Crear datos iniciales (SOLO la primera vez)
python seed.py

# 6. Arrancar el servidor
uvicorn main:app --reload --port 8000
```

## Credenciales iniciales

| Rol | Email | Contraseña |
|-----|-------|-----------|
| Admin | admin@ipscuidandodeti.com | Admin2024! |
| Doctor | doctor@ipscuidandodeti.com | Doctor2024! |
| Recepcionista | recepcion@ipscuidandodeti.com | Recepcion2024! |

> ⚠️ Cambia estas contraseñas en producción.

## Documentación interactiva

Con el servidor corriendo, visita:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Arquitectura

```
backend/
├── main.py                  # Punto de entrada FastAPI + CORS + routers
├── database.py              # Conexión SQLite + SQLAlchemy
├── seed.py                  # Datos iniciales
├── core/
│   ├── config.py            # Variables de entorno (pydantic-settings)
│   ├── security.py          # JWT + bcrypt
│   └── dependencies.py      # get_current_user, require_roles()
├── models/                  # Tablas SQLAlchemy
│   ├── user.py              # Empleados + enum de roles
│   ├── patient.py           # Pacientes
│   ├── availability.py      # Slots semanales + fechas bloqueadas
│   ├── appointment.py       # Citas
│   ├── clinical_record.py   # Historias clínicas + entradas
│   └── rips.py              # Reportes RIPS
├── schemas/                 # Validación Pydantic (entrada/salida)
├── routers/                 # Endpoints por módulo
│   ├── public.py            # 🌐 Agendamiento público SIN login
│   ├── auth.py              # POST /auth/login, GET /auth/me
│   ├── users.py             # CRUD empleados
│   ├── patients.py          # CRUD pacientes
│   ├── availability.py      # Configurar horarios + consultar calendario
│   ├── appointments.py      # Agendar, listar, actualizar citas
│   ├── clinical_records.py  # Abrir HC, agregar entradas
│   ├── rips.py              # Generar y descargar RIPS 2.0
│   └── dashboard.py         # Estadísticas panel
└── services/
    ├── scheduler_service.py # Lógica de slots disponibles
    └── rips_service.py      # Lógica generación RIPS 2.0 JSON
```

## Agendamiento Público (sin login)

Endpoints en `/public/` — accesibles desde el sitio web para pacientes externos:

| Endpoint | Descripción |
|----------|-------------|
| `GET /public/services` | Lista los servicios activos con sus profesionales |
| `GET /public/availability?professional_id=X&date_from=Y` | Slots disponibles por profesional y fecha |
| `POST /public/appointments` | Agenda una cita (crea el paciente si no existe) |
| `GET /public/appointments/{IPS-000001}` | Consulta el estado de una cita por código |

**Flujo de un paciente externo:**
1. El admin configura la disponibilidad de cada profesional por servicio en el panel
2. El paciente en el sitio web consulta `GET /public/services` → elige servicio + profesional
3. El sitio consulta `GET /public/availability` → muestra el calendario con slots libres
4. El paciente llena sus datos y confirma → `POST /public/appointments`
5. El sistema retorna un código tipo `IPS-000123` para seguimiento

## Roles y permisos

| Módulo | Admin | Doctor | Enfermero | Recepcionista | Auditor |
|--------|-------|--------|-----------|---------------|---------|
| Usuarios | ✅ CRUD | Solo ver propio | Solo ver propio | Solo ver propio | ❌ |
| Pacientes | ✅ | ✅ ver/editar | ✅ ver/editar | ✅ crear/ver | ✅ ver |
| Disponibilidad | ✅ todos | ✅ propia | ✅ propia | ❌ | ❌ |
| Citas | ✅ | ✅ propias | ✅ propias | ✅ crear/ver | ✅ ver |
| Historias Clínicas | ✅ | ✅ crear/escribir | ✅ notas enf. | ✅ ver | ✅ ver |
| RIPS | ✅ | ❌ | ❌ | ❌ | ✅ |
| Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |

## Flujo típico de uso

1. **Recepcionista** registra paciente → `POST /patients/`
2. **Recepcionista** agenda cita → `POST /appointments/`
   - El sistema verifica disponibilidad automáticamente
3. **Doctor** ve sus citas del día → `GET /appointments/today`
4. **Doctor** abre/accede HC → `GET /clinical-records/patients/{id}`
5. **Doctor** escribe nota de consulta → `POST /clinical-records/entries`
6. **Auditor/Admin** genera RIPS mensual → `POST /rips/generate`
7. **Auditor/Admin** descarga JSON RIPS → `GET /rips/{id}/download`

## RIPS 2.0

El sistema genera automáticamente el JSON RIPS 2.0 según la Resolución 2275 de 2023 (MinSalud).
El JSON descargado se puede cargar directamente en MIPRES/ADRES.
# ipsbackend
