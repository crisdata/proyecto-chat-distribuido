# logging_config.py
# Configuración central de logging para toda la aplicación.
# Se llama una vez al arrancar desde main.py, antes de cualquier
# otra inicialización, para que todos los módulos hereden el formato.
#
# Incluye un filtro que inyecta automáticamente el request_id de la
# petición actual en cada línea de log, sin necesidad de pasarlo
# manualmente en cada llamada al logger.

import logging
import sys

from app.request_id import get_request_id


class RequestIdFilter(logging.Filter):
    """
    Filtro que añade el request_id de la petición actual a cada
    LogRecord, permitiendo que aparezca automáticamente en el formato.
    Si se llama fuera de una petición HTTP (por ejemplo durante el
    arranque), aparece "-" como valor.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configurar_logging(nivel: int = logging.INFO):
    """
    Configura el logger raíz con formato consistente.
    Formato: timestamp - nivel - [componente] [request_id] mensaje
    """
    logging.basicConfig(
        level=nivel,
        format='%(asctime)s - %(levelname)s - [%(name)s] [%(request_id)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout,
        force=True,
    )

    # Aplicar el filtro de request_id al handler raíz
    root_logger = logging.getLogger()
    request_filter = RequestIdFilter()
    for handler in root_logger.handlers:
        handler.addFilter(request_filter)

    # Reducir el ruido de librerías de terceros
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)