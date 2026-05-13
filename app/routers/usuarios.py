# routers/usuarios.py
# Maneja el registro y listado de usuarios en el sistema.
# Endpoints disponibles:
#   POST /usuarios     — registrar usuario y emitir token JWT
#   GET  /usuarios     — listar todos los usuarios
#   GET  /usuarios/me  — recuperar el usuario actual desde el token

import uuid
from fastapi import APIRouter, HTTPException, Depends
from app.models import UsuarioCreate, UsuarioResponse, UsuarioAutenticadoResponse
from app.database import get_connection, release_connection
from app.cache import (
    adquirir_lock, liberar_lock,
    cachear_usuario,
    get_redis
)
from app.auth import crear_token, autenticar_usuario_actual

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("", response_model=UsuarioAutenticadoResponse, status_code=201)
async def registrar_usuario(datos: UsuarioCreate):
    """
    Registra un nuevo usuario o reingresa a uno existente.
    Retorna también un token JWT para autenticación posterior.
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

            await cursor.execute(
                "SELECT id, nombre, creado_en FROM usuarios WHERE LOWER(nombre) = LOWER(%s)",
                (datos.nombre,)
            )
            existente = await cursor.fetchone()

            if existente:
                usuario_id, nombre, creado_en = existente[0], existente[1], existente[2]
                jwt_token = await crear_token(usuario_id, nombre)
                return {
                    "id": usuario_id,
                    "nombre": nombre,
                    "creado_en": creado_en.isoformat() if creado_en else None,
                    "token": jwt_token
                }

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

        await cachear_usuario(nuevo_id, datos.nombre)
        redis = get_redis()
        await redis.setex(
            f"nombre:{datos.nombre.lower()}", 300, nuevo_id
        )

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


@router.get("/me", response_model=UsuarioResponse)
async def usuario_actual(payload: dict = Depends(autenticar_usuario_actual)):
    """
    Retorna los datos del usuario autenticado actual.
    El frontend llama a este endpoint al cargar la página
    para recuperar la sesión si el token sigue siendo válido.
    Lanza 401 si el token es inválido o expiró.
    """
    usuario_id = payload["sub"]
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id, nombre, creado_en FROM usuarios WHERE id = %s",
                (usuario_id,)
            )
            usuario = await cursor.fetchone()

        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return {
            "id": usuario[0],
            "nombre": usuario[1],
            "creado_en": usuario[2].isoformat() if usuario[2] else None
        }
    finally:
        await release_connection(conn)