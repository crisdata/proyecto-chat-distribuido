import inspect

from app.routers import mensajes
from app.routers.mensajes import consultar_conversacion


def test_endpoint_conversacion_legacy_esta_deprecado():
    rutas = [ruta for ruta in mensajes.router.routes if getattr(ruta, "path", None) == "/conversacion/{usuario_id}"]

    assert rutas
    assert getattr(rutas[0], "deprecated", False) is True


def test_endpoint_conversacion_legacy_expone_parametros_de_paginacion():
    firma = inspect.signature(consultar_conversacion)

    assert "limit" in firma.parameters
    assert "before_id" in firma.parameters
    assert firma.parameters["limit"].default.default == 50


def test_endpoint_conversacion_legacy_no_resetea_todos_los_no_leidos():
    fuente = inspect.getsource(consultar_conversacion)

    assert "resetear_todos_no_leidos" not in fuente
