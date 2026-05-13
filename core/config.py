from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Entorno
    ENVIRONMENT: str = "development"   # "production" en el VPS

    # Base de datos — DEBE venir del entorno en producción, nunca quedarse en SQLite
    DATABASE_URL: str = "sqlite:///./ips_cuidando.db"  # fallback solo para desarrollo local

    # JWT
    SECRET_KEY: str = "clave-secreta-temporal-cambiar-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas

    # Datos IPS para RIPS
    IPS_NIT: str = "900000000"
    IPS_NOMBRE: str = "CUIDANDO DE TI CyE IPS SAS"
    IPS_MUNICIPIO: str = "76001"  # Cali
    IPS_CODIGO_HABILITACION: str = "760010000000"

    # CORS — separados por coma, sin espacios
    CORS_ORIGINS: str = "http://localhost:4200,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    class Config:
        env_file = ".env"


settings = Settings()
