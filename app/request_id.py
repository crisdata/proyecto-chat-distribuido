# request_id.py
# Provee un identificador único por petición que viaja a lo largo
# de toda la cadena de procesamiento, permitiendo trazar el flujo
# completo de un mensaje en los logs.
#
# Implementación:
#   - ContextVar para que cada petición async tenga su propio valor
#     sin pisarse con peticiones simultáneas.
#   - Funciones helper para obtener y establecer el request_id desde
#     cualquier punto del código (middleware, routers, queue, etc.)

import uuid
from contextvars import ContextVar

# ContextVar: variable que vive aislada por contexto asíncrono.
# Cada petición HTTP tiene su propio "contexto" y por tanto su propio
# request_id, sin importar cuántas peticiones se procesen en paralelo.
_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """
    Retorna el request_id de la petición actual.
    Retorna "-" si se llama fuera de una petición HTTP
    (por ejemplo, durante el arranque del servidor).
    """
    return _request_id_var.get()


def set_request_id(request_id: str) -> None:
    """
    Establece el request_id para el contexto actual.
    Lo llama el middleware al inicio de cada petición HTTP.
    """
    _request_id_var.set(request_id)


def generar_request_id() -> str:
    """
    Genera un nuevo identificador único para una petición.
    Usa UUID4: aleatorio, 128 bits, prácticamente sin colisiones.
    Devolvemos solo los primeros 8 caracteres para que los logs
    sean legibles. Para producción real se usaría el UUID completo.
    """
    return str(uuid.uuid4())[:8]