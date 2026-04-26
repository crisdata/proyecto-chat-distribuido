# routers/usuarios.py
# Maneja el registro y listado de usuarios en el sistema.
# Endpoints disponibles:
#   POST /usuarios  — registrar usuario
#   GET  /usuarios  — listar todos los usuarios
#
# Flujo de registro:
#   1. Adquiere lock distribuido para evitar registros duplicados simultáneos
#   2. Verifica duplicado en Redis (por nombre) y como fallback en MariaDB
#   3. Registra en MariaDB y cachea en Redis con doble índice (id y nombre)
#   4. Libera el lock

import uuid
from fastapi import APIRouter, HTTPException
from app.models import UsuarioCreate, UsuarioResponse
from app.database import get_connection, release_connection
from app.cache import (
    adquirir_lock, liberar_lock,
    cachear_usuario, obtener_usuario_cache,
    get_redis
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("", response_model=UsuarioResponse, status_code=201)
async def registrar_usuario(datos: UsuarioCreate):
    """
    Registra un nuevo usuario en el sistema.
    El nombre debe ser único. El sistema asigna un ID automáticamente.
    Usa lock distribuido para manejar registros concurrentes de forma segura.
    """

    # Adquirir lock para evitar que dos solicitudes simultáneas
    # registren el mismo nombre al mismo tiempo
    token_lock = await adquirir_lock(f"registro:{datos.nombre.lower()}")
    if not token_lock:
        raise HTTPException(
            status_code=429,
            detail="El sistema está procesando otra solicitud con ese nombre. Intenta de nuevo."
        )

    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:

            # Verificar duplicado en base de datos
            await cursor.execute(
                "SELECT id FROM usuarios WHERE LOWER(nombre) = LOWER(%s)",
                (datos.nombre,)
            )
            existente = await cursor.fetchone()
            if existente:
                # Si el nombre ya existe, retornar ese usuario como login implícito
                await cursor.execute(
                    "SELECT id, nombre, creado_en FROM usuarios WHERE LOWER(nombre) = LOWER(%s)",
                    (datos.nombre,)
                )
                usuario = await cursor.fetchone()
                await liberar_lock(f"registro:{datos.nombre.lower()}", token_lock)
                await release_connection(conn)
                return {
                    "id": usuario[0],
                    "nombre": usuario[1],
                    "creado_en": usuario[2].isoformat() if usuario[2] else None
                }

            # Generar ID único y registrar el usuario
            nuevo_id = str(uuid.uuid4())
            await cursor.execute(
                "INSERT INTO usuarios (id, nombre) VALUES (%s, %s)",
                (nuevo_id, datos.nombre)
            )

            # Obtener el registro completo para retornarlo
            await cursor.execute(
                "SELECT id, nombre, creado_en FROM usuarios WHERE id = %s",
                (nuevo_id,)
            )
            usuario = await cursor.fetchone()

        # Cachear con doble índice:
        #   usuario:{id}     → nombre  (para validar si un ID existe)
        #   nombre:{nombre}  → id      (para verificar nombres sin tocar MariaDB)
        await cachear_usuario(nuevo_id, datos.nombre)
        redis = get_redis()
        await redis.setex(
            f"nombre:{datos.nombre.lower()}", 300, nuevo_id
        )

        return {
            "id": usuario[0],
            "nombre": usuario[1],
            "creado_en": usuario[2].isoformat() if usuario[2] else None
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