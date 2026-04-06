# models.py
# Define la estructura de los datos que entran y salen del sistema.
# FastAPI usa estos modelos para validar automáticamente cada solicitud.

from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


# ── Usuarios ──────────────────────────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    """Datos necesarios para registrar un nuevo usuario."""
    nombre: str

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres.")
        if len(v) > 100:
            raise ValueError("El nombre no puede superar los 100 caracteres.")
        return v


class UsuarioResponse(BaseModel):
    """Datos que el sistema devuelve después de registrar un usuario."""
    id: str
    nombre: str
    # datetime permite que Pydantic serialice automáticamente
    # el objeto datetime de MariaDB a formato ISO 8601
    creado_en: Optional[datetime] = None

    class Config:
        # Permite que Pydantic lea objetos datetime directamente
        # desde los resultados de aiomysql sin conversión manual
        from_attributes = True


# ── Mensajes ──────────────────────────────────────────────────────────────────

class MensajeCreate(BaseModel):
    """Datos necesarios para enviar un mensaje privado."""
    emisor_id: str
    receptor_id: str
    contenido: str

    @field_validator("contenido")
    @classmethod
    def validar_contenido(cls, v: str) -> str:
        v = v.strip()
        if len(v) == 0:
            raise ValueError("El contenido del mensaje no puede estar vacío.")
        if len(v) > 2000:
            raise ValueError("El mensaje no puede superar los 2000 caracteres.")
        return v


class MensajeResponse(BaseModel):
    """Estructura completa de un mensaje guardado en el sistema."""
    id: Optional[int] = None
    emisor_id: str
    receptor_id: str
    contenido: str
    # datetime coherente con el campo TIMESTAMP de MariaDB
    timestamp: datetime

    class Config:
        from_attributes = True


# ── Respuestas generales ──────────────────────────────────────────────────────

class RespuestaExito(BaseModel):
    """Respuesta estándar para operaciones exitosas sin datos que retornar."""
    mensaje: str


class RespuestaError(BaseModel):
    """Respuesta estándar para errores controlados del sistema."""
    detalle: str

# ── Mensajes no leídos ──────────────────────────────────────────────────────

class NoLeidosResponse(BaseModel):
    """Retorna el contador de mensajes no leídos de un usuario."""
    usuario_id: str
    no_leidos: int