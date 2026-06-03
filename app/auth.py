# auth.py
# Módulo central de autenticación.
# Encapsula la creación, firma y validación de tokens JWT
# y la autenticación del worker mediante secreto compartido.

import logging
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Header

from app.cache import guardar_sesion, obtener_sesion

log = logging.getLogger("auth")

JWT_SECRET = os.getenv("JWT_SECRET")
WORKER_SECRET = os.getenv("WORKER_SECRET")

if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET no está definido en las variables de entorno. "
        "Genera uno con: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )

if not WORKER_SECRET:
    raise RuntimeError(
        "WORKER_SECRET no está definido en las variables de entorno. "
        "Genera uno con: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )

JWT_SECRET_ACTIVO: str = JWT_SECRET
WORKER_SECRET_ACTIVO: str = WORKER_SECRET

JWT_ALGORITMO = "HS256"
JWT_TTL_SEGUNDOS = 3600  # 1 hora


async def crear_token(usuario_id: str) -> str:
    """
    Crea un JWT firmado para el usuario y lo registra en Redis.
    Doble validación: la firma garantiza autenticidad, y Redis
    permite invalidar la sesión antes del TTL natural del token.

    El token solo transporta el identificador opaco del usuario. No incluye
    email ni nombre visible para preservar privacidad en clientes/logs.
    """
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": usuario_id,
        "iat": ahora,
        "exp": ahora + timedelta(seconds=JWT_TTL_SEGUNDOS)
    }
    token = jwt.encode(payload, JWT_SECRET_ACTIVO, algorithm=JWT_ALGORITMO)
    await guardar_sesion(usuario_id, token, ttl=JWT_TTL_SEGUNDOS)
    log.info(f"Token emitido para usuario id={usuario_id}")
    return token


async def validar_token(token: str) -> dict:
    """
    Valida un JWT y verifica que la sesión siga activa en Redis.
    Retorna el payload decodificado si es válido.
    Lanza HTTPException 401 si el token es inválido, expiró o fue revocado.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_ACTIVO,
            algorithms=[JWT_ALGORITMO]
        )
    except jwt.ExpiredSignatureError:
        log.warning("Intento de uso de token expirado")
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        log.warning("Intento de uso de token inválido")
        raise HTTPException(status_code=401, detail="Token inválido")

    usuario_id = payload.get("sub")
    if not usuario_id:
        log.warning("Token sin campo 'sub'")
        raise HTTPException(status_code=401, detail="Token sin sujeto")

    sesion_activa = await obtener_sesion(usuario_id)
    if sesion_activa != token:
        log.warning(f"Sesión revocada para usuario {usuario_id}")
        raise HTTPException(
            status_code=401,
            detail="Sesión revocada. Inicia sesión de nuevo."
        )

    return payload


async def autenticar_usuario_actual(
    authorization: str = Header(None)
) -> dict:
    """
    Dependencia de FastAPI para extraer y validar el token de un
    header 'Authorization: Bearer <token>'.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Falta header Authorization: Bearer <token>"
        )

    token = authorization[7:]
    return await validar_token(token)


def autenticar_worker(
    x_worker_secret: str = Header(None)
) -> None:
    """
    Dependencia de FastAPI para validar que un request viene del worker
    mediante un secreto compartido en el header X-Worker-Secret.
    """
    if x_worker_secret != WORKER_SECRET_ACTIVO:
        log.warning("Intento de acceso al endpoint interno sin secreto válido")
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado"
        )