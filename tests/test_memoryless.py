# pyright: reportMissingImports=false
import importlib

import pytest
from pydantic import ValidationError

from tests.conftest import FakeConnection


@pytest.fixture
def mensajes_module(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("WORKER_SECRET", "test-worker-secret")

    import app.routers.mensajes as mensajes

    return importlib.reload(mensajes)


def _patch_memoryless(monkeypatch, mod, conn, conectados=None):
    async def fake_get_connection():
        return conn

    async def fake_release(_conn):
        return None

    async def fake_validar_usuario(_uid, _conn):
        return "Usuario"

    monkeypatch.setattr(mod, "get_connection", fake_get_connection)
    monkeypatch.setattr(mod, "release_connection", fake_release)
    monkeypatch.setattr(mod, "validar_usuario", fake_validar_usuario)

    if conectados is None:
        conectados = set()

    class FakeManager:
        def esta_conectado(self, uid):
            return uid in conectados

        async def notify(self, uid, evento):
            pass

    fm = FakeManager()
    monkeypatch.setattr(mod, "manager", fm)
    monkeypatch.setattr(mod, "publicar", lambda *a: None)


def test_mensaje_sin_memoria_modelo_valido():
    from app.models import MensajeSinMemoriaCreate

    m = MensajeSinMemoriaCreate(emisor_id="u1", receptor_id="u2", contenido="Hola")

    assert m.contenido == "Hola"
    assert m.emisor_id == "u1"


def test_mensaje_sin_memoria_rechaza_vacio():
    from app.models import MensajeSinMemoriaCreate

    with pytest.raises(ValidationError):
        MensajeSinMemoriaCreate(emisor_id="u1", receptor_id="u2", contenido="")


# ── Endpoint tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sin_memoria_online_entrega(mensajes_module, monkeypatch):
    from app.models import MensajeSinMemoriaCreate

    entregados = []

    class FM:
        def esta_conectado(self, uid):
            return uid == "u2"

        async def notify(self, uid, evento):
            entregados.append((uid, evento))

    conn = FakeConnection()

    async def fake_get_connection():
        return conn

    async def fake_release(_conn):
        return None

    async def fake_validar_usuario(_uid, _conn):
        return "Usuario"

    monkeypatch.setattr(mensajes_module, "get_connection", fake_get_connection)
    monkeypatch.setattr(mensajes_module, "release_connection", fake_release)
    monkeypatch.setattr(mensajes_module, "validar_usuario", fake_validar_usuario)
    monkeypatch.setattr(mensajes_module, "manager", FM())
    monkeypatch.setattr(mensajes_module, "publicar", lambda *a: None)

    respuesta = await mensajes_module.enviar_mensaje_sin_memoria(
        MensajeSinMemoriaCreate(emisor_id="u1", receptor_id="u2", contenido="Hola"),
        payload={"sub": "u1"},
    )

    assert respuesta["entregado"] is True
    assert respuesta["modo"] == "sin_memoria"
    assert len(entregados) == 1
    assert entregados[0][0] == "u2"
    assert entregados[0][1]["contenido"] == "Hola"


@pytest.mark.asyncio
async def test_sin_memoria_offline_no_entrega(mensajes_module, monkeypatch):
    from app.models import MensajeSinMemoriaCreate

    conn = FakeConnection()
    _patch_memoryless(monkeypatch, mensajes_module, conn, conectados=set())

    respuesta = await mensajes_module.enviar_mensaje_sin_memoria(
        MensajeSinMemoriaCreate(emisor_id="u1", receptor_id="u2", contenido="Hola"),
        payload={"sub": "u1"},
    )

    assert respuesta["entregado"] is False
    assert respuesta["modo"] == "sin_memoria"
    assert "No se guarda historial" in respuesta["mensaje"]


@pytest.mark.asyncio
async def test_sin_memoria_no_persiste_en_db(mensajes_module, monkeypatch):
    from app.models import MensajeSinMemoriaCreate

    conn = FakeConnection()
    _patch_memoryless(monkeypatch, mensajes_module, conn, conectados={"u2"})

    await mensajes_module.enviar_mensaje_sin_memoria(
        MensajeSinMemoriaCreate(emisor_id="u1", receptor_id="u2", contenido="Hola"),
        payload={"sub": "u1"},
    )

    assert not conn.seen_queries
