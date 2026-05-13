"""
Servicio de generación de RIPS 2.0 (Resolución 2275 de 2023 - MinSalud Colombia).

Estructura JSON:
- numDocumentoIdObligado: NIT de la IPS
- usuarios[]: datos de cada paciente atendido
  - servicios.consultas[]: consultas médicas (AC)
  - servicios.procedimientos[]: procedimientos (AP)
  - servicios.otrosServicios[]: otros servicios (AT)
"""
import json
from datetime import date
from sqlalchemy.orm import Session
from models.appointment import Appointment, AppointmentStatus, AppointmentType
from models.clinical_record import ClinicalRecord, ClinicalEntry, EntryType
from models.patient import Patient
from models.rips import RIPSReport, RIPSStatus
from core.config import settings


# Mapeo de tipo de documento a código RIPS
DOCUMENT_TYPE_RIPS = {
    "CC": "CC",
    "TI": "TI",
    "CE": "CE",
    "PA": "PA",
    "RC": "RC",
    "MS": "MS",
    "AS": "AS",
    "NIT": "NIT",
}

# Mapeo de género a código RIPS
GENDER_RIPS = {
    "M": "1",  # Masculino
    "F": "2",  # Femenino
    "I": "3",  # Indeterminado
}

# Mapeo de tipo de cita a código de servicio CUPS (simplificado)
APPOINTMENT_TYPE_CUPS = {
    AppointmentType.CONSULTATION: "890201",   # Consulta médica general
    AppointmentType.NURSING: "890202",         # Consulta de enfermería
    AppointmentType.PHYSICAL_THERAPY: "890204",
    AppointmentType.NUTRITION: "890207",
    AppointmentType.PSYCHOLOGY: "890206",
    AppointmentType.POST_SURGICAL: "890299",
    AppointmentType.SEROTHERAPY: "890299",
    AppointmentType.FOLLOW_UP: "890201",
    AppointmentType.EMERGENCY: "890201",
}


def _build_consultation_entry(appointment: Appointment, entry: ClinicalEntry | None) -> dict:
    """Construye un registro de consulta RIPS 2.0."""
    return {
        "codPrestador": settings.IPS_CODIGO_HABILITACION,
        "fechaInicioAtencion": appointment.appointment_date.strftime("%Y%m%d"),
        "numAutorizacion": "",
        "codConsulta": APPOINTMENT_TYPE_CUPS.get(appointment.appointment_type, "890201"),
        "modalidadGrupoServicioTecSal": "01",      # Intramural
        "grupoServicios": "01",                     # Consulta externa
        "codServicio": "105",                       # Consulta médica
        "finalidadTecnologiaSalud": "11",           # Diagnóstico
        "causaMotivoAtencion": "26",                # Enfermedad general
        "codDiagnosticoPrincipal": entry.diagnosis_code if entry and entry.diagnosis_code else "Z00",
        "codDiagnosticoPrincipalE": "",
        "codDiagnosticoRelacionadoE1": "",
        "codDiagnosticoRelacionadoE2": "",
        "codDiagnosticoRelacionadoE3": "",
        "tipoDiagnosticoPrincipal": "01" if (entry and entry.diagnosis_type == "impresion_diagnostica") else ("02" if (entry and entry.diagnosis_type == "confirmado") else ("05" if (entry and entry.diagnosis_type == "descartado") else "01")),
        "valorPagoModerador": 0,
        "numFEVPagoModerador": "",
        "consecutivo": str(appointment.id),
        "conceptoRecaudo": "02",
        "valorNetoPagar": 0,
    }


def generate_rips_json(
    db: Session,
    period_start: date,
    period_end: date,
) -> tuple[dict, int, int, int]:
    """
    Genera el JSON RIPS 2.0 para un período dado.
    Retorna (json_dict, total_patients, total_consultations, total_procedures).
    """
    # Obtener citas completadas en el período
    appointments = db.query(Appointment).filter(
        Appointment.appointment_date >= period_start,
        Appointment.appointment_date <= period_end,
        Appointment.status == AppointmentStatus.COMPLETED,
    ).all()

    # Agrupar por paciente
    patient_map: dict[int, list[Appointment]] = {}
    for appt in appointments:
        patient_map.setdefault(appt.patient_id, []).append(appt)

    usuarios = []
    total_consultations = 0
    total_procedures = 0

    for patient_id, patient_appointments in patient_map.items():
        patient: Patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            continue

        consultas = []

        for appt in patient_appointments:
            # Buscar la entrada clínica asociada a esta cita
            clinical_record = db.query(ClinicalRecord).filter(
                ClinicalRecord.patient_id == patient_id
            ).first()

            entry = None
            if clinical_record:
                entry = db.query(ClinicalEntry).filter(
                    ClinicalEntry.clinical_record_id == clinical_record.id,
                    ClinicalEntry.appointment_id == appt.id,
                ).first()

            if appt.appointment_type in (
                AppointmentType.CONSULTATION, AppointmentType.FOLLOW_UP,
                AppointmentType.EMERGENCY, AppointmentType.NURSING,
                AppointmentType.SEROTHERAPY, AppointmentType.POST_SURGICAL,
            ):
                consultas.append(_build_consultation_entry(appt, entry))
                total_consultations += 1

        usuario = {
            "tipoDocumentoIdentificacion": DOCUMENT_TYPE_RIPS.get(patient.document_type.value, "CC"),
            "numDocumentoIdentificacion": patient.document_number,
            "codPaisResidencia": "170",
            "codMunicipioResidencia": patient.municipality_code or "76001",
            "codZonaTerritorialResidencia": "1",   # Cabecera municipal
            "incapacidad": "2",                     # No
            "codSexo": GENDER_RIPS.get(patient.gender.value, "3"),
            "fechaNacimiento": patient.birth_date.strftime("%Y%m%d"),
            "codPaisNacimiento": "170",
            "consecutivo": str(patient.id),
            "servicios": {
                "consultas": consultas,
                "procedimientos": [],
                "urgencias": [],
                "hospitalizacion": [],
                "recienNacidos": [],
                "medicamentos": [],
                "otrosServicios": [],
            }
        }
        usuarios.append(usuario)

    rips_json = {
        "numDocumentoIdObligado": settings.IPS_NIT,
        "numFolioNumberSoporteFactura": "",
        "tipoNota": "",
        "numNota": "",
        "usuarios": usuarios,
    }

    return rips_json, len(usuarios), total_consultations, total_procedures


def create_rips_report(
    db: Session,
    period_start: date,
    period_end: date,
    generated_by_id: int,
    notes: str | None = None,
) -> RIPSReport:
    """Genera y guarda un reporte RIPS en la base de datos."""
    rips_json, total_patients, total_consultations, total_procedures = generate_rips_json(
        db, period_start, period_end
    )

    report = RIPSReport(
        period_start=period_start,
        period_end=period_end,
        status=RIPSStatus.GENERATED,
        report_json=json.dumps(rips_json, ensure_ascii=False, indent=2),
        total_patients=total_patients,
        total_consultations=total_consultations,
        total_procedures=total_procedures,
        generated_by=generated_by_id,
        notes=notes,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
