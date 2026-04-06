# cache.py
# Gestiona la conexión a Redis.
# Redis cumple dos roles en este sistema:
#   1. Control de concurrencia mediante locks distribuidos
#   2. Caché de usuarios activos para evitar consultas repetidas a MariaDB
#
# Corte 3 — estructuras preparadas:
#   - Caché de tokens JWT para autenticación
#   - Lock mejorado con token único para alta concurrencia

import redis.asyncio as aioredis
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

# Cliente Redis compartido por toda la aplicación
cliente_redis = None


async def conectar_redis():
    """Crea la conexión a Redis al iniciar la aplicación."""
    global cliente_redis
    cliente_redis = aioredis.from_url(
        f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}",
        encoding="utf-8",
        decode_responses=True,
    )


async def desconectar_redis():
    """Cierra la conexión a Redis al apagar la aplicación."""
    global cliente_redis
    if cliente_redis:
        await cliente_redis.aclose()


def get_redis():
    """Retorna el cliente Redis activo."""
    return cliente_redis


# ── Locks distribuidos ────────────────────────────────────────────────────────

async def adquirir_lock(nombre: str, tiempo_expiracion: int = 5) -> str | None:
    """
    Intenta adquirir un lock distribuido para una operación crítica.
    Retorna un token único si lo adquirió, None si otro proceso ya lo tiene.

    El token garantiza que solo quien adquirió el lock puede liberarlo,
    evitando que un proceso libere el lock de otro en condiciones de
    alta latencia o timeouts.
    """
    token = str(uuid.uuid4())
    resultado = await cliente_redis.set(
        f"lock:{nombre}",
        token,
        nx=True,
        ex=tiempo_expiracion
    )
    return token if resultado else None


async def liberar_lock(nombre: str, token: str):
    """
    Libera un lock distribuido solo si el token coincide con el
    que lo adquirió. Previene que un proceso libere el lock de otro.
    """
    valor_actual = await cliente_redis.get(f"lock:{nombre}")
    if valor_actual == token:
        await cliente_redis.delete(f"lock:{nombre}")


# ── Caché de usuarios ─────────────────────────────────────────────────────────

async def cachear_usuario(usuario_id: str, nombre: str, ttl: int = 300):
    """
    Guarda un usuario en caché por 5 minutos.
    Evita consultar MariaDB cada vez que se valida un usuario.
    """
    await cliente_redis.setex(f"usuario:{usuario_id}", ttl, nombre)


async def obtener_usuario_cache(usuario_id: str) -> str | None:
    """
    Busca un usuario en caché por su ID.
    Retorna el nombre si existe, None si no está en caché.
    El llamador decide si consulta MariaDB como fallback.
    """
    return await cliente_redis.get(f"usuario:{usuario_id}")


async def invalidar_cache_usuario(usuario_id: str):
    """Elimina un usuario del caché cuando sus datos cambian."""
    await cliente_redis.delete(f"usuario:{usuario_id}")


# ── Contadores de mensajes ────────────────────────────────────────────────────

async def incrementar_mensajes_no_leidos(usuario_id: str):
    """
    Incrementa el contador de mensajes no leídos de un usuario.
    Se llama cada vez que alguien le envía un mensaje.
    """
    await cliente_redis.incr(f"no_leidos:{usuario_id}")


async def obtener_mensajes_no_leidos(usuario_id: str) -> int:
    """
    Retorna el número de mensajes no leídos de un usuario.
    Retorna 0 si no hay contador activo.
    """
    valor = await cliente_redis.get(f"no_leidos:{usuario_id}")
    return int(valor) if valor else 0


async def resetear_mensajes_no_leidos(usuario_id: str):
    """
    Resetea el contador cuando el usuario consulta su conversación.
    """
    await cliente_redis.delete(f"no_leidos:{usuario_id}")


# ── Caché de sesiones JWT (Corte 3) ───────────────────────────────────────────

async def guardar_sesion(usuario_id: str, token: str, ttl: int = 3600):
    """
    Guarda el token JWT de una sesión activa por 1 hora.
    Permite invalidar sesiones sin esperar a que el token expire.
    Se activa en el Corte 3 cuando se implemente autenticación JWT.
    """
    await cliente_redis.setex(f"sesion:{usuario_id}", ttl, token)


async def obtener_sesion(usuario_id: str) -> str | None:
    """
    Verifica si existe una sesión activa para un usuario.
    Retorna el token si existe, None si la sesión expiró o fue cerrada.
    """
    return await cliente_redis.get(f"sesion:{usuario_id}")


async def cerrar_sesion(usuario_id: str):
    """
    Invalida la sesión de un usuario de forma inmediata.
    Útil para logout o para forzar re-autenticación por seguridad.
    """
    await cliente_redis.delete(f"sesion:{usuario_id}")

