import inspect

from app.routers import mensajes
from app.routers.mensajes import consultar_conversacion


def test_endpoint_conversacion_legacy_esta_deprecado():
    rutas = [ruta for ruta in mensajes.router.routes if getattr(ruta, "path", None) == "/conversacion/{usuario_id}"]

    assert rutas
    assert getattr(rutas[0], "deprecated", False) is True


def test_endpoint_conversacion_legacy_no_resetea_todos_los_no_leidos():
    fuente = inspect.getsource(consultar_conversacion)

    assert "resetear_todos_no_leidos" not in fuente
