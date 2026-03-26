# routers/usuarios.py
# Maneja el registro de usuarios en el sistema.
# Endpoint disponible: POST /usuarios

import uuid
from fastapi import APIRouter, HTTPException
from app.models import UsuarioCreate, UsuarioResponse
from app.storage import usuarios

# El prefijo /usuarios se aplica automáticamente a todos los endpoints de este archivo.
router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("", response_model=UsuarioResponse, status_code=201)
async def registrar_usuario(datos: UsuarioCreate):
    """
    Registra un nuevo usuario en el sistema.
    El nombre debe ser único. El sistema asigna un ID automáticamente.
    """

    # Verificar que el nombre no esté siendo usado por otro usuario.
    for usuario in usuarios.values():
        if usuario["nombre"].lower() == datos.nombre.lower():
            raise HTTPException(
                status_code=400,
                detail=f"El nombre '{datos.nombre}' ya está registrado."
            )

    # Generar un identificador único para el nuevo usuario.
    nuevo_id = str(uuid.uuid4())

    # Guardar el usuario en memoria.
    usuarios[nuevo_id] = {
        "id": nuevo_id,
        "nombre": datos.nombre
    }

    return usuarios[nuevo_id]