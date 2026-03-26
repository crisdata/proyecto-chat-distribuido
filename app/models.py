# models.py
# Define la estructura de los datos que entran y salen del sistema.
# FastAPI usa estos modelos para validar automáticamente cada solicitud.

from pydantic import BaseModel
from typing import Optional

# Datos necesarios para registrar un nuevo usuario.
class UsuarioCreate(BaseModel):
    nombre: str

# Datos que el sistema devuelve después de registrar un usuario.
class UsuarioResponse(BaseModel):
    id: str
    nombre: str

# Datos necesarios para enviar un mensaje privado.
class MensajeCreate(BaseModel):
    emisor_id: str
    receptor_id: str
    contenido: str

# Estructura completa de un mensaje guardado en el sistema.
class MensajeResponse(BaseModel):
    emisor_id: str
    receptor_id: str
    contenido: str
    timestamp: str
