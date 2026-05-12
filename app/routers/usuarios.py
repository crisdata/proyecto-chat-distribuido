# routers/usuarios.py
# Maneja el registro y listado de usuarios en el sistema.
# Endpoints disponibles:
#   POST /usuarios  — registrar usuario y emitir token JWT
#   GET  /usuarios  — listar todos los usuarios

import uuid
from fastapi import APIRouter, HTTPException
from app.models import UsuarioCreate, UsuarioResponse, UsuarioAutenticadoResponse
from app.database import get_connection, release_connection
from app.cache import (
    adquirir_lock, liberar_lock,
    cachear_usuario,
    get_redis
)
from app.auth import crear_token

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("", response_model=UsuarioAutenticadoResponse, status_code=201)
async def registrar_usuario(datos: UsuarioCreate):
    """
    Registra un nuevo usuario en el sistema o reingresa a uno existente.
    El nombre debe ser único. El sistema asigna un ID automáticamente.
    Usa lock distribuido para manejar registros concurrentes de forma segura.

    Retorna también un token JWT que el cliente debe usar para autenticar
    sus llamadas posteriores (mensajes y conexión WebSocket).
    """

    token_lock = await adquirir_lock(f"registro:{datos.nombre.lower()}")
    if not token_lock:
        raise HTTPException(
            status_code=429,
            detail="El sistema está procesando otra solicitud con ese nombre. Intenta de nuevo."
        )

    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:

            # Verificar si el usuario ya existe (login implícito)
            await cursor.execute(
                "SELECT id, nombre, creado_en FROM usuarios WHERE LOWER(nombre) = LOWER(%s)",
                (datos.nombre,)
            )
            existente = await cursor.fetchone()

            if existente:
                # Usuario ya existe — emitir nuevo token
                usuario_id, nombre, creado_en = existente[0], existente[1], existente[2]
                jwt_token = await crear_token(usuario_id, nombre)
                return {
                    "id": usuario_id,
                    "nombre": nombre,
                    "creado_en": creado_en.isoformat() if creado_en else None,
                    "token": jwt_token
                }

            # Usuario nuevo — crear y emitir token
            nuevo_id = str(uuid.uuid4())
            await cursor.execute(
                "INSERT INTO usuarios (id, nombre) VALUES (%s, %s)",
                (nuevo_id, datos.nombre)
            )

            await cursor.execute(
                "SELECT id, nombre, creado_en FROM usuarios WHERE id = %s",
                (nuevo_id,)
            )
            usuario = await cursor.fetchone()

        # Cachear con doble índice
        await cachear_usuario(nuevo_id, datos.nombre)
        redis = get_redis()
        await redis.setex(
            f"nombre:{datos.nombre.lower()}", 300, nuevo_id
        )

        # Emitir token JWT para el nuevo usuario
        jwt_token = await crear_token(nuevo_id, datos.nombre)

        return {
            "id": usuario[0],
            "nombre": usuario[1],
            "creado_en": usuario[2].isoformat() if usuario[2] else None,
            "token": jwt_token
        }

    finally:
        await liberar_lock(f"registro:{datos.nombre.lower()}", token_lock)
        await release_connection(conn)


@router.get("", response_model=list[UsuarioResponse])
async def listar_usuarios():
    """
    Retorna la lista de todos los usuarios registrados en orden alfabético.
    Útil para que el frontend muestre los contactos disponibles.
    """
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id, nombre, creado_en FROM usuarios ORDER BY nombre ASC"
            )
            usuarios = await cursor.fetchall()

        return [
            {
                "id": u[0],
                "nombre": u[1],
                "creado_en": u[2].isoformat() if u[2] else None
            }
            for u in usuarios
        ]
    finally:
        await release_connection(conn)