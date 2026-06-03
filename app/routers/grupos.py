# routers/grupos.py
# Maneja la creación, búsqueda, membresía y mensajería de grupos públicos.

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models import (
    GrupoCreate,
    GrupoResponse,
    MensajeGrupoCreate,
    MensajeGrupoResponse,
    UnirseGrupoResponse,
)
from app.database import get_connection, release_connection
from app.cache import (
    adquirir_lock,
    liberar_lock,
    get_redis,
)
from app.auth import autenticar_usuario_actual
from app.routers.websocket import manager

router = APIRouter(prefix="/grupos", tags=["Grupos"])


async def _es_miembro(cursor, grupo_id: str, usuario_id: str) -> bool:
    await cursor.execute(
        "SELECT 1 FROM grupo_miembros WHERE grupo_id = %s AND usuario_id = %s",
        (grupo_id, usuario_id),
    )
    return await cursor.fetchone() is not None


@router.post("", response_model=GrupoResponse, status_code=201)
async def crear_grupo(
    datos: GrupoCreate,
    payload: dict = Depends(autenticar_usuario_actual),
):
    """Crea un grupo público y agrega al creador como primer miembro."""
    nombre_normalizado = datos.nombre.strip().lower()
    token_lock = await adquirir_lock(f"grupo:crear:{nombre_normalizado}")
    if not token_lock:
        raise HTTPException(status_code=429, detail="Intenta más tarde.")

    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            nuevo_id = str(uuid.uuid4())
            await cursor.execute(
                "INSERT INTO grupos (id, nombre, nombre_normalizado, creado_por) "
                "VALUES (%s, %s, %s, %s)",
                (nuevo_id, datos.nombre, nombre_normalizado, payload["sub"]),
            )
            await cursor.execute(
                "INSERT INTO grupo_miembros (grupo_id, usuario_id) VALUES (%s, %s)",
                (nuevo_id, payload["sub"]),
            )

            await cursor.execute(
                "SELECT id, nombre, creado_por, creado_en FROM grupos WHERE id = %s",
                (nuevo_id,),
            )
            g = await cursor.fetchone()

        return {
            "id": g[0],
            "nombre": g[1],
            "creado_por": g[2],
            "creado_en": g[3],
            "es_miembro": True,
            "modo": "grupo_publico",
        }
    except Exception:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un grupo con ese nombre o no se pudo crear.",
        )
    finally:
        await liberar_lock(f"grupo:crear:{nombre_normalizado}", token_lock)
        await release_connection(conn)


@router.get("/buscar", response_model=list[GrupoResponse])
async def buscar_grupos(
    q: str = Query("", min_length=1),
    payload: dict = Depends(autenticar_usuario_actual),
):
    """Busca grupos públicos por nombre (búsqueda parcial)."""
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            patron = f"%{q}%"
            await cursor.execute(
                "SELECT id, nombre, creado_por, creado_en FROM grupos "
                "WHERE nombre LIKE %s ORDER BY nombre ASC",
                (patron,),
            )
            grupos = await cursor.fetchall()

        resultado = []
        for g in grupos:
            gid, nombre, creado_por, creado_en = g[0], g[1], g[2], g[3]
            async with conn.cursor() as cursor:
                miembro = await _es_miembro(cursor, gid, payload["sub"])
            resultado.append(
                {
                    "id": gid,
                    "nombre": nombre,
                    "creado_por": creado_por,
                    "creado_en": creado_en,
                    "es_miembro": miembro,
                    "modo": "grupo_publico",
                }
            )

        return resultado
    finally:
        await release_connection(conn)


@router.get("/mios", response_model=list[GrupoResponse])
async def grupos_mios(
    payload: dict = Depends(autenticar_usuario_actual),
):
    """Retorna solo los grupos a los que el usuario se ha unido."""
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT g.id, g.nombre, g.creado_por, g.creado_en "
                "FROM grupos g "
                "JOIN grupo_miembros m ON g.id = m.grupo_id "
                "WHERE m.usuario_id = %s "
                "ORDER BY g.nombre ASC",
                (payload["sub"],),
            )
            grupos = await cursor.fetchall()

        return [
            {
                "id": g[0],
                "nombre": g[1],
                "creado_por": g[2],
                "creado_en": g[3],
                "es_miembro": True,
                "modo": "grupo_publico",
            }
            for g in grupos
        ]
    finally:
        await release_connection(conn)


@router.post("/{grupo_id}/unirse", response_model=UnirseGrupoResponse)
async def unirse_a_grupo(
    grupo_id: str,
    payload: dict = Depends(autenticar_usuario_actual),
):
    """Une un usuario a un grupo público (idempotente)."""
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            if await _es_miembro(cursor, grupo_id, payload["sub"]):
                return {"unido": True, "grupo_id": grupo_id}

            await cursor.execute(
                "INSERT INTO grupo_miembros (grupo_id, usuario_id) VALUES (%s, %s)",
                (grupo_id, payload["sub"]),
            )

        return {"unido": True, "grupo_id": grupo_id}
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="El grupo no existe o no se pudo unir.",
        )
    finally:
        await release_connection(conn)


@router.get(
    "/{grupo_id}/mensajes",
    response_model=list[MensajeGrupoResponse],
)
async def mensajes_grupo(
    grupo_id: str,
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = Query(None, ge=1),
    payload: dict = Depends(autenticar_usuario_actual),
):
    """Retorna mensajes paginados de un grupo. Solo para miembros."""
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            if not await _es_miembro(cursor, grupo_id, payload["sub"]):
                raise HTTPException(
                    status_code=403, detail="No eres miembro de este grupo."
                )

            where = ""
            params: list = [grupo_id]
            if before_id is not None:
                where = " AND mg.id < %s"
                params.append(before_id)
            params.append(limit)

            await cursor.execute(
                f"SELECT mg.id, mg.grupo_id, mg.emisor_id, u.nombre, mg.contenido, mg.timestamp "
                f"FROM mensajes_grupo mg "
                f"JOIN usuarios u ON mg.emisor_id = u.id "
                f"WHERE mg.grupo_id = %s{where} "
                f"ORDER BY mg.id DESC LIMIT %s",
                tuple(params),
            )
            filas = list(reversed(await cursor.fetchall()))

        return [
            {
                "id": f[0],
                "grupo_id": f[1],
                "emisor_id": f[2],
                "emisor_nombre": f[3],
                "contenido": f[4],
                "timestamp": f[5],
            }
            for f in filas
        ]
    finally:
        await release_connection(conn)


@router.post(
    "/{grupo_id}/mensajes",
    response_model=MensajeGrupoResponse,
    status_code=201,
)
async def enviar_mensaje_grupo(
    grupo_id: str,
    datos: MensajeGrupoCreate,
    payload: dict = Depends(autenticar_usuario_actual),
):
    """Envía un mensaje persistente a un grupo."""
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            if not await _es_miembro(cursor, grupo_id, payload["sub"]):
                raise HTTPException(
                    status_code=403, detail="No eres miembro de este grupo."
                )

            await cursor.execute(
                "INSERT INTO mensajes_grupo (grupo_id, emisor_id, contenido) "
                "VALUES (%s, %s, %s)",
                (grupo_id, payload["sub"], datos.contenido),
            )
            msg_id = cursor.lastrowid

            await cursor.execute(
                "SELECT mg.id, mg.grupo_id, mg.emisor_id, u.nombre, mg.contenido, mg.timestamp "
                "FROM mensajes_grupo mg "
                "JOIN usuarios u ON mg.emisor_id = u.id "
                "WHERE mg.id = %s",
                (msg_id,),
            )
            msg = await cursor.fetchone()

            # ── Redis: incrementar no leídos del grupo para otros miembros ──
            await cursor.execute(
                "SELECT usuario_id FROM grupo_miembros WHERE grupo_id = %s",
                (grupo_id,),
            )
            miembros = await cursor.fetchall()
            r = get_redis()
            for (uid,) in miembros:
                if uid != payload["sub"] and r is not None:
                    await r.incr(f"no_leidos_grupo:{uid}:{grupo_id}")

            # ── WebSocket: notificar a miembros conectados ──
            for (uid,) in miembros:
                if uid != payload["sub"] and manager.esta_conectado(uid):
                    await manager.notify(
                        uid,
                        {
                            "tipo": "nuevo_mensaje_grupo",
                            "grupo_id": grupo_id,
                            "emisor_id": payload["sub"],
                            "emisor_nombre": msg[3],
                            "contenido": datos.contenido,
                        },
                    )

        return {
            "id": msg[0],
            "grupo_id": msg[1],
            "emisor_id": msg[2],
            "emisor_nombre": msg[3],
            "contenido": msg[4],
            "timestamp": msg[5],
        }
    finally:
        await release_connection(conn)
