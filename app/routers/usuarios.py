# routers/usuarios.py
# Maneja el registro y listado de usuarios en el sistema.
# Endpoints disponibles:
#   POST /usuarios     — registrar usuario y emitir token JWT
#   GET  /usuarios     — listar todos los usuarios
#   GET  /usuarios/me  — recuperar el usuario actual desde el token

import uuid
from fastapi import APIRouter, HTTPException, Depends
from app.models import (
    UsuarioCreate, UsuarioLoginRequest, UsuarioResponse, UsuarioAutenticadoResponse,
    PresenciaResponse, PresenciaBulkRequest
)
from app.database import get_connection, release_connection
from app.cache import (
    adquirir_lock, liberar_lock,
    cachear_usuario,
    get_redis,
    obtener_presencia, obtener_presencia_bulk
)
from app.auth import crear_token, autenticar_usuario_actual

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/login", status_code=200)
async def login_usuario(datos: UsuarioLoginRequest):
    """
    Login demo por email normalizado.

    Si el correo existe, inicia sesión. Si no existe y no se envía nombre,
    pide completar el registro. Si no existe y se envía nombre, crea la cuenta.
    El email nunca se devuelve al cliente.
    """
    token_lock = await adquirir_lock(f"login:{datos.email}")
    if not token_lock:
        raise HTTPException(
            status_code=429,
            detail="El sistema está procesando otra solicitud con ese correo. Intenta de nuevo."
        )

    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id, nombre, creado_en FROM usuarios WHERE email = %s",
                (datos.email,)
            )
            existente = await cursor.fetchone()

            if existente:
                usuario_id, nombre, creado_en = existente[0], existente[1], existente[2]
                jwt_token = await crear_token(usuario_id)
                return {
                    "id": usuario_id,
                    "nombre": nombre,
                    "creado_en": creado_en.isoformat() if creado_en else None,
                    "token": jwt_token,
                    "requiere_nombre": False,
                }

            if datos.nombre is None:
                return {
                    "requiere_nombre": True,
                    "mensaje": "Indica tu nombre visible para completar el registro.",
                }

            nuevo_id = str(uuid.uuid4())
            await cursor.execute(
                "INSERT INTO usuarios (id, nombre, email) VALUES (%s, %s, %s)",
                (nuevo_id, datos.nombre, datos.email)
            )

            await cursor.execute(
                "SELECT id, nombre, creado_en FROM usuarios WHERE id = %s",
                (nuevo_id,)
            )
            usuario = await cursor.fetchone()

        await cachear_usuario(nuevo_id, datos.nombre)
        redis = get_redis()
        await redis.setex(f"nombre:{datos.nombre.lower()}", 300, nuevo_id)

        jwt_token = await crear_token(nuevo_id)

        return {
            "id": usuario[0],
            "nombre": usuario[1],
            "creado_en": usuario[2].isoformat() if usuario[2] else None,
            "token": jwt_token,
            "requiere_nombre": False,
        }

    finally:
        await liberar_lock(f"login:{datos.email}", token_lock)
        await release_connection(conn)


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
                jwt_token = await crear_token(usuario_id)
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

        jwt_token = await crear_token(nuevo_id)

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

# ── Presencia ────────────────────────────────────────────────────────────────

@router.get("/{usuario_id}/presencia", response_model=PresenciaResponse)
async def consultar_presencia(usuario_id: str):
    """
    Retorna el estado de presencia de un usuario específico.
    Para usuarios humanos: depende de su conexión WebSocket.
    Para Lumi: depende de si Ollama está respondiendo.
    """
    # Importación local para evitar dependencia circular
    from app.routers.ia import obtener_id_ia, verificar_ollama_disponible

    # Caso especial: si es Lumi, su presencia depende de Ollama
    ia_id = await obtener_id_ia()
    if usuario_id == ia_id:
        ollama_ok = await verificar_ollama_disponible()
        return {
            "usuario_id": usuario_id,
            "estado": "online" if ollama_ok else "reposando",
            "ultima_actividad": None
        }

    # Caso normal: usuario humano
    presencia = await obtener_presencia(usuario_id)
    return {
        "usuario_id": usuario_id,
        "estado": presencia["estado"],
        "ultima_actividad": presencia["ultima_actividad"]
    }


@router.post("/presencia/bulk", response_model=list[PresenciaResponse])
async def consultar_presencia_bulk(datos: PresenciaBulkRequest):
    """
    Retorna el estado de presencia de varios usuarios en una sola petición.
    Optimizado para la lista de contactos: una sola llamada cada 10s
    devuelve el estado de todos los contactos a la vez.

    Lumi se trata especialmente: su presencia depende del estado de Ollama,
    no del WebSocket. Se reporta "online" si Ollama responde, "reposando" si no.
    """
    from app.routers.ia import obtener_id_ia, verificar_ollama_disponible

    ia_id = await obtener_id_ia()

    # Separar Lumi del resto para procesarla aparte
    ids_humanos = [uid for uid in datos.usuario_ids if uid != ia_id]
    incluye_lumi = ia_id in datos.usuario_ids

    # Consultar presencia de humanos en bulk (operación rápida)
    presencias_humanos = await obtener_presencia_bulk(ids_humanos)
    resultado = [
        {
            "usuario_id": uid,
            "estado": p["estado"],
            "ultima_actividad": p["ultima_actividad"]
        }
        for uid, p in presencias_humanos.items()
    ]

    # Si Lumi estaba en la lista, consultar Ollama y añadirla
    if incluye_lumi:
        ollama_ok = await verificar_ollama_disponible()
        resultado.append({
            "usuario_id": ia_id,
            "estado": "online" if ollama_ok else "reposando",
            "ultima_actividad": None
        })

    return resultado