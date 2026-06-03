import importlib

import pytest
from fastapi import HTTPException


@pytest.fixture
def auth_module(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("WORKER_SECRET", "test-worker-secret")

    import app.auth as auth

    return importlib.reload(auth)


@pytest.mark.asyncio
async def test_crear_y_validar_token_activo(auth_module, monkeypatch):
    sesiones = {}

    async def fake_guardar_sesion(usuario_id, token, ttl=3600):
        sesiones[usuario_id] = token

    async def fake_obtener_sesion(usuario_id):
        return sesiones.get(usuario_id)

    monkeypatch.setattr(auth_module, "guardar_sesion", fake_guardar_sesion)
    monkeypatch.setattr(auth_module, "obtener_sesion", fake_obtener_sesion)

    token = await auth_module.crear_token("u1", "Cris")
    payload = await auth_module.validar_token(token)

    assert payload["sub"] == "u1"
    assert payload["nombre"] == "Cris"


@pytest.mark.asyncio
async def test_validar_token_rechaza_sesion_revocada(auth_module, monkeypatch):
    async def fake_obtener_sesion(usuario_id):
        return None

    monkeypatch.setattr(auth_module, "obtener_sesion", fake_obtener_sesion)

    token = auth_module.jwt.encode(
        {"sub": "u1", "nombre": "Cris"},
        auth_module.JWT_SECRET,
        algorithm=auth_module.JWT_ALGORITMO,
    )

    with pytest.raises(HTTPException) as exc:
        await auth_module.validar_token(token)

    assert exc.value.status_code == 401
    assert "Sesión revocada" in exc.value.detail


@pytest.mark.asyncio
async def test_autenticar_usuario_actual_exige_bearer(auth_module):
    with pytest.raises(HTTPException) as exc:
        await auth_module.autenticar_usuario_actual(authorization="token-invalido")

    assert exc.value.status_code == 401
