# cache.py
# Gestiona la conexión a Redis.
# Redis cumple dos roles en este sistema:
#   1. Control de concurrencia mediante locks distribuidos
#   2. Caché de usuarios activos para evitar consultas repetidas a MariaDB
#
# Corte 3 — estructuras preparadas:
#   - Caché de tokens JWT para autenticación
#   - Lock mejorado con token único y liberación atómica via Lua

import asyncio
import logging
import redis.asyncio as aioredis
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("cache")

# Cliente Redis compartido por toda la aplicación
cliente_redis = None

# Script Lua para liberación atómica del lock.
# Redis garantiza que los scripts Lua se ejecutan sin interrupción,
# evitando la condición de carrera entre GET y DELETE.
# Retorna 1 si liberó el lock, 0 si el token no coincidía
# (lo que indica que el lock ya había expirado y fue tomado por otro).
LUA_LIBERAR_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


async def conectar_redis():
    """
    Crea la conexión a Redis al iniciar la aplicación.

    Si REDIS_PASSWORD está definida y no está vacía, construye una URL
    autenticada: redis://:password@host:port/0.
    Incluye reintentos para tolerar arranques lentos del contenedor.
    """
    global cliente_redis

    host = os.getenv("REDIS_HOST", "redis")
    port = os.getenv("REDIS_PORT", "6379")
    password = os.getenv("REDIS_PASSWORD", "")

    if password:
        url = f"redis://:{password}@{host}:{port}/0"
    else:
        url = f"redis://{host}:{port}/0"

    intentos_maximos = 10
    espera_entre_intentos = 3  # segundos

    for intento in range(1, intentos_maximos + 1):
        try:
            log.info(f"Intento {intento}/{intentos_maximos} de conexión a Redis...")
            cliente_redis = aioredis.from_url(
                url,
                encoding="utf-8",
                decode_responses=True,
            )
            # ping() confirma que la conexión es real, no solo que el objeto fue creado
            await cliente_redis.ping()
            log.info("Conexión a Redis establecida correctamente")
            return
        except Exception as e:
            if intento == intentos_maximos:
                log.error(
                    f"Imposible conectar a Redis tras "
                    f"{intentos_maximos} intentos. Último error: {e}"
                )
                raise RuntimeError(
                    f"No se pudo conectar a Redis tras {intentos_maximos} intentos."
                ) from e
            log.warning(
                f"Intento {intento} falló ({type(e).__name__}: {e}). "
                f"Reintentando en {espera_entre_intentos}s..."
            )
            await asyncio.sleep(espera_entre_intentos)


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


async def liberar_lock(nombre: str, token: str) -> bool:
    """
    Libera un lock distribuido de forma atómica usando un script Lua.
    Solo libera si el token coincide con el que adquirió el lock,
    previniendo que un proceso libere el lock de otro.

    Retorna True si liberó el lock correctamente.
    Retorna False si el lock ya había expirado o pertenecía a otro proceso
    (esto puede indicar que la operación crítica tardó más que el TTL del lock).
    """
    resultado = await cliente_redis.eval(
        LUA_LIBERAR_LOCK,
        1,                    # número de KEYS
        f"lock:{nombre}",     # KEYS[1]
        token                 # ARGV[1]
    )
    return resultado == 1


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


# ── Contadores de mensajes no leídos (Bloque 5) ──────────────────────────────
#
# Sistema de contadores POR CONTACTO en lugar de global.
# Estructura en Redis:
#   no_leidos:<receptor_id>:<emisor_id>  → N (entero)
#
# Cada mensaje incrementa el contador específico de la pareja receptor+emisor.
# Cuando el receptor abre el chat con ese emisor, ese contador específico
# se borra. El total se calcula sumando todos los contadores del receptor.
#
# Ventajas vs sistema global:
#   - El badge en la lista muestra "Carlos (3)" en lugar de solo "5" total
#   - El usuario sabe a quién responder primero sin entrar a cada chat
#   - Al abrir un chat, solo se borra ese contador específico
#
# Compatibilidad: las funciones antiguas se mantienen como alias
# por si algún código aún las llama, pero internamente delegan al sistema
# por contacto.

async def incrementar_no_leidos_de(receptor_id: str, emisor_id: str):
    """
    Incrementa el contador de mensajes no leídos que el receptor
    tiene con un emisor específico.
    Se llama cada vez que el worker recibe un evento de mensaje nuevo.
    """
    await cliente_redis.incr(f"no_leidos:{receptor_id}:{emisor_id}")


async def obtener_no_leidos_por_contacto(receptor_id: str) -> dict[str, int]:
    """
    Retorna un diccionario {emisor_id: cantidad} con todos los
    contadores no leídos del receptor.

    Usa SCAN para encontrar todas las claves del patrón
    no_leidos:<receptor_id>:*, luego MGET para leer sus valores
    en una sola ida y vuelta a Redis.
    """
    patron = f"no_leidos:{receptor_id}:*"
    prefijo_len = len(f"no_leidos:{receptor_id}:")

    # SCAN es preferible a KEYS en producción porque no bloquea Redis
    cursor = 0
    claves = []
    while True:
        cursor, batch = await cliente_redis.scan(
            cursor=cursor, match=patron, count=100
        )
        claves.extend(batch)
        if cursor == 0:
            break

    if not claves:
        return {}

    # Leer todos los valores en una sola operación
    valores = await cliente_redis.mget(*claves)

    resultado = {}
    for clave, valor in zip(claves, valores):
        if valor is None:
            continue
        emisor_id = clave[prefijo_len:]
        try:
            resultado[emisor_id] = int(valor)
        except (ValueError, TypeError):
            continue

    return resultado


async def resetear_no_leidos_con(receptor_id: str, emisor_id: str):
    """
    Borra el contador de no leídos que el receptor tenía con un emisor
    específico. Se llama cuando el receptor abre el chat con ese emisor.
    """
    await cliente_redis.delete(f"no_leidos:{receptor_id}:{emisor_id}")


async def resetear_todos_no_leidos(receptor_id: str):
    """
    Borra TODOS los contadores no leídos de un receptor.
    Útil para 'marcar todo como leído' (no se usa actualmente
    pero queda disponible).
    """
    patron = f"no_leidos:{receptor_id}:*"
    cursor = 0
    while True:
        cursor, claves = await cliente_redis.scan(
            cursor=cursor, match=patron, count=100
        )
        if claves:
            await cliente_redis.delete(*claves)
        if cursor == 0:
            break


# Alias de compatibilidad con código antiguo.
# Mantienen las firmas viejas pero ya no se usan internamente.
# Marcadas como deprecadas para limpieza futura.

async def incrementar_mensajes_no_leidos(usuario_id: str):
    """DEPRECADO: usa incrementar_no_leidos_de(receptor, emisor) en su lugar."""
    pass  # Ya no hace nada — sistema migrado a contadores por contacto


async def obtener_mensajes_no_leidos(usuario_id: str) -> int:
    """
    Retorna el TOTAL de mensajes no leídos sumando todos los contadores
    por contacto del usuario.
    """
    por_contacto = await obtener_no_leidos_por_contacto(usuario_id)
    return sum(por_contacto.values())


async def resetear_mensajes_no_leidos(usuario_id: str):
    """DEPRECADO: usa resetear_no_leidos_con(receptor, emisor) en su lugar."""
    await resetear_todos_no_leidos(usuario_id)


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

# ── Presencia de usuarios (Bloque 4) ──────────────────────────────────────────
#
# Gestiona el estado online/offline de los usuarios en tiempo real.
# Cada usuario tiene dos claves en Redis:
#   - presencia:<uuid>         → "online" con TTL 60s (existe = online)
#   - ultima_actividad:<uuid>  → timestamp ISO con TTL 7 días
#
# El WebSocket llama a marcar_presencia al conectar y cada ping (30s).
# Si el WebSocket se cierra o cae, el TTL caduca y el usuario queda offline
# automáticamente, sin necesidad de cleanup explícito.

from datetime import datetime, timezone

# TTL de la marca de presencia. Más largo que el intervalo de ping (30s)
# para tolerar retrasos sin marcar al usuario offline incorrectamente.
TTL_PRESENCIA_SEGUNDOS = 60

# TTL del registro de última actividad. Mantenemos histórico durante 7 días
# para mostrar "Activo hace X días" sin que la BD crezca indefinidamente.
TTL_ULTIMA_ACTIVIDAD_SEGUNDOS = 7 * 24 * 3600  # 7 días


async def marcar_presencia(usuario_id: str):
    """
    Marca un usuario como online y actualiza su última actividad.
    Se llama al conectar el WebSocket y en cada ping de keepalive.
    Idempotente: llamarla N veces seguidas tiene el mismo efecto que una.
    """
    ahora = datetime.now(timezone.utc).isoformat()
    # Usamos pipeline para enviar ambos comandos en una sola ida y vuelta a Redis
    pipe = cliente_redis.pipeline()
    pipe.setex(f"presencia:{usuario_id}", TTL_PRESENCIA_SEGUNDOS, "online")
    pipe.setex(f"ultima_actividad:{usuario_id}", TTL_ULTIMA_ACTIVIDAD_SEGUNDOS, ahora)
    await pipe.execute()


async def quitar_presencia(usuario_id: str):
    """
    Marca un usuario como offline explícitamente (al desconectar el WebSocket).
    Actualiza última actividad para reflejar el momento exacto de la desconexión.
    Si no se llama, el TTL natural se encarga.
    """
    ahora = datetime.now(timezone.utc).isoformat()
    pipe = cliente_redis.pipeline()
    pipe.delete(f"presencia:{usuario_id}")
    pipe.setex(f"ultima_actividad:{usuario_id}", TTL_ULTIMA_ACTIVIDAD_SEGUNDOS, ahora)
    await pipe.execute()


async def obtener_presencia(usuario_id: str) -> dict:
    """
    Retorna el estado de presencia de un usuario.
    Estructura:
      {
        "estado": "online" | "offline",
        "ultima_actividad": "2026-05-20T15:30:00+00:00" | None
      }
    """
    pipe = cliente_redis.pipeline()
    pipe.exists(f"presencia:{usuario_id}")
    pipe.get(f"ultima_actividad:{usuario_id}")
    resultados = await pipe.execute()

    return {
        "estado": "online" if resultados[0] else "offline",
        "ultima_actividad": resultados[1]
    }


async def obtener_presencia_bulk(usuario_ids: list[str]) -> dict:
    """
    Versión optimizada que retorna la presencia de N usuarios en una sola
    operación a Redis. Usa pipeline para enviar todas las consultas juntas.

    Retorna un diccionario {usuario_id: {estado, ultima_actividad}}.

    Para 30 usuarios consulta 60 claves en una sola ida y vuelta,
    muchísimo más eficiente que llamar obtener_presencia 30 veces.
    """
    if not usuario_ids:
        return {}

    pipe = cliente_redis.pipeline()
    for uid in usuario_ids:
        pipe.exists(f"presencia:{uid}")
        pipe.get(f"ultima_actividad:{uid}")

    resultados = await pipe.execute()

    # resultados viene como lista plana: [exists_1, ultima_1, exists_2, ultima_2, ...]
    # Lo reagrupamos por usuario.
    presencias = {}
    for i, uid in enumerate(usuario_ids):
        exists_idx = i * 2
        ultima_idx = i * 2 + 1
        presencias[uid] = {
            "estado": "online" if resultados[exists_idx] else "offline",
            "ultima_actividad": resultados[ultima_idx]
        }

    return presencias