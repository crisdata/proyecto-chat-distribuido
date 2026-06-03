# pyright: reportMissingImports=false, reportCallIssue=false
# models.py
# Define la estructura de los datos que entran y salen del sistema.
# FastAPI usa estos modelos para validar automáticamente cada solicitud.

from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import field_validator
from datetime import datetime
from typing import Optional


# ── Usuarios ──────────────────────────────────────────────────────────────────

def validar_nombre_visible(v: str) -> str:
    v = v.strip()
    if len(v) < 2:
        raise ValueError("El nombre debe tener al menos 2 caracteres.")
    if len(v) > 100:
        raise ValueError("El nombre no puede superar los 100 caracteres.")
    return v


class UsuarioCreate(BaseModel):
    """Datos necesarios para registrar un nuevo usuario."""
    nombre: str

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        return validar_nombre_visible(v)


class UsuarioLoginRequest(BaseModel):
    """Datos del login demo por email.

    El email se usa como identidad privada y no debe exponerse en respuestas.
    El nombre solo se requiere la primera vez que el email no existe.
    """
    email: str
    nombre: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("El correo no puede estar vacío.")
        if "@" not in v or v.startswith("@") or v.endswith("@"):
            raise ValueError("Ingresa un correo válido.")
        return v

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validar_nombre_visible(v)


class UsuarioResponse(BaseModel):
    """Datos que el sistema devuelve después de registrar un usuario."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    creado_en: Optional[datetime] = None


class UsuarioAutenticadoResponse(BaseModel):
    """
    Respuesta del endpoint de registro/login.
    Incluye el token JWT que el cliente debe usar para autenticar
    sus llamadas posteriores y la conexión WebSocket.
    """
    id: str
    nombre: str
    creado_en: Optional[datetime] = None
    token: str


# ── Mensajes ──────────────────────────────────────────────────────────────────

class MensajeCreate(BaseModel):
    """Datos necesarios para enviar un mensaje privado."""
    emisor_id: str
    receptor_id: str
    contenido: str
    expira_en: int | None = None  # segundos para autodestrucción (None = normal)

    @field_validator("expira_en")
    @classmethod
    def validar_expira_en(cls, v: int | None) -> int | None:
        if v is None:
            return None
        if v < 5:
            raise ValueError("La autodestrucción mínima es de 5 segundos.")
        if v > 300:
            raise ValueError("La autodestrucción máxima es de 300 segundos (5 min).")
        return v

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
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    emisor_id: str
    receptor_id: str
    contenido: str
    timestamp: datetime
    expira_en: Optional[datetime] = None


# ── Grupos ────────────────────────────────────────────────────────────────────

class GrupoCreate(BaseModel):
    """Datos necesarios para crear un grupo público."""
    nombre: str

    @field_validator("nombre")
    @classmethod
    def validar_nombre_grupo(cls, v: str) -> str:
        return validar_nombre_visible(v)


class GrupoResponse(BaseModel):
    """Datos que se devuelven al consultar un grupo."""
    id: str
    nombre: str
    creado_por: str
    creado_en: Optional[datetime] = None
    es_miembro: bool = False
    modo: str = "grupo_publico"


class MensajeGrupoCreate(BaseModel):
    """Datos para enviar un mensaje a un grupo."""
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


class MensajeGrupoResponse(BaseModel):
    """Estructura de un mensaje de grupo."""
    id: Optional[int] = None
    grupo_id: Optional[str] = None
    emisor_id: str
    contenido: str
    timestamp: Optional[datetime] = None


class UnirseGrupoResponse(BaseModel):
    """Respuesta al unirse a un grupo."""
    unido: bool
    grupo_id: str


class MensajeSinMemoriaCreate(BaseModel):
    """Datos para enviar un mensaje sin memoria."""
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


class MensajeSinMemoriaResponse(BaseModel):
    """Respuesta al envío de un mensaje sin memoria."""
    entregado: bool
    modo: str = "sin_memoria"
    mensaje: str = ""


class MensajeIARequest(BaseModel):
    """Datos para enviar un mensaje a Lumi.

    Extiende MensajeCreate con un campo modo opcional para memoria/sin memoria.
    """
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


class IAModoRequest(BaseModel):
    """Petición a Lumi con selector de modo."""
    emisor_id: str
    receptor_id: str
    contenido: str
    modo: str = "con_memoria"  # "con_memoria" | "sin_memoria"

    @field_validator("contenido")
    @classmethod
    def validar_contenido(cls, v: str) -> str:
        v = v.strip()
        if len(v) == 0:
            raise ValueError("El contenido del mensaje no puede estar vacío.")
        if len(v) > 2000:
            raise ValueError("El mensaje no puede superar los 2000 caracteres.")
        return v


# ── Respuestas generales ──────────────────────────────────────────────────────

class RespuestaExito(BaseModel):
    """Respuesta estándar para operaciones exitosas sin datos que retornar."""
    mensaje: str


class RespuestaError(BaseModel):
    """Respuesta estándar para errores controlados del sistema."""
    detalle: str


# ── Mensajes no leídos ──────────────────────────────────────────────────────

class NoLeidosResponse(BaseModel):
    """Respuesta del endpoint de no leídos.
    Incluye el total global y el desglose por contacto."""
    usuario_id: str
    no_leidos: int
    por_contacto: dict[str, int] = {}

# ── Presencia ────────────────────────────────────────────────────────────────

class PresenciaResponse(BaseModel):
    """Estado de presencia de un usuario."""
    usuario_id: str
    estado: str  # "online" | "offline"
    ultima_actividad: Optional[str] = None


class PresenciaBulkRequest(BaseModel):
    """Request para consultar la presencia de varios usuarios a la vez."""
    usuario_ids: list[str]