import json

import pytest

from app import worker


class FakeExchange:
    def __init__(self):
        self.publicaciones = []

    async def publish(self, mensaje, routing_key):
        self.publicaciones.append((mensaje, routing_key))


class FakeChannel:
    def __init__(self):
        self.default_exchange = FakeExchange()


@pytest.mark.asyncio
async def test_publicar_en_dlq_usa_cola_de_fallos():
    canal = FakeChannel()
    evento = {
        "receptor_id": "u2",
        "emisor_id": "u1",
        "emisor_nombre": "Cris",
    }

    await worker.publicar_en_dlq(canal, evento, "reintentos_agotados", 3)

    mensaje, routing_key = canal.default_exchange.publicaciones[0]
    payload = json.loads(mensaje.body.decode())

    assert routing_key == worker.COLA_MENSAJES_FALLIDOS
    assert payload["receptor_id"] == "u2"
    assert payload["error"]["razon"] == "reintentos_agotados"
    assert payload["error"]["reintentos"] == 3
    assert mensaje.headers["x-error-razon"] == "reintentos_agotados"
