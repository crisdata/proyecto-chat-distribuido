import inspect

from app.routers.mensajes import consultar_conversacion_bilateral


def test_conversacion_bilateral_expone_parametros_de_paginacion():
    firma = inspect.signature(consultar_conversacion_bilateral)

    assert "limit" in firma.parameters
    assert "before_id" in firma.parameters


def test_conversacion_bilateral_limit_default_es_50():
    firma = inspect.signature(consultar_conversacion_bilateral)
    limit = firma.parameters["limit"].default

    assert limit.default == 50
