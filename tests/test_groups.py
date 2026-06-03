# pyright: reportMissingImports=false
import importlib

import pytest
from pydantic import ValidationError

from tests.conftest import FakeConnection, FakeRedis, patch_deps, next_test_id


@pytest.fixture
def grupos_module(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("WORKER_SECRET", "test-worker-secret")

    import app.routers.grupos as grupos

    return importlib.reload(grupos)


# ── Model validation ─────────────────────────────────────────────────────────

def test_grupo_nombre_requerido():
    from app.models import GrupoCreate

    with pytest.raises(ValidationError):
        GrupoCreate()  # pyright: ignore[reportCallIssue]


def test_grupo_nombre_vacio():
    from app.models import GrupoCreate

    with pytest.raises(ValidationError):
        GrupoCreate(nombre="")


def test_grupo_nombre_valido():
    from app.models import GrupoCreate

    g = GrupoCreate(nombre="  Programación  ")

    assert g.nombre == "Programación"


# ── Endpoint tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_grupo_auto_agrega_creador(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_deps(monkeypatch, grupos_module, conn, FakeRedis())
    monkeypatch.setattr(grupos_module.uuid, "uuid4", next_test_id)

    respuesta = await grupos_module.crear_grupo(
        GrupoCreate(nombre="Futbol"), payload={"sub": "u1"}
    )

    assert respuesta["nombre"] == "Futbol"
    assert respuesta["es_miembro"] is True
    assert respuesta["modo"] == "grupo_publico"
    assert f"{respuesta['id']}:u1" in conn.miembros


@pytest.mark.asyncio
async def test_grupo_nombre_duplicado_rechazado(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", next_test_id)

    await grupos_module.crear_grupo(GrupoCreate(nombre="Futbol"), payload={"sub": "u1"})

    with pytest.raises(Exception) as exc:
        await grupos_module.crear_grupo(
            GrupoCreate(nombre="futbol"), payload={"sub": "u2"}
        )

    assert exc.value.status_code == 409  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.asyncio
async def test_buscar_grupos_por_nombre_parcial(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", next_test_id)

    await grupos_module.crear_grupo(GrupoCreate(nombre="Futbol Club"), payload={"sub": "u1"})
    await grupos_module.crear_grupo(GrupoCreate(nombre="Futbol Sala"), payload={"sub": "u1"})
    await grupos_module.crear_grupo(GrupoCreate(nombre="Cine"), payload={"sub": "u1"})

    resultados = await grupos_module.buscar_grupos(q="futbol", payload={"sub": "u1"})

    assert len(resultados) == 2
    nombres = {g["nombre"] for g in resultados}
    assert {"Futbol Club", "Futbol Sala"} <= nombres


@pytest.mark.asyncio
async def test_buscar_grupos_sin_resultados(grupos_module, monkeypatch):
    conn = FakeConnection()
    patch_deps(monkeypatch, grupos_module, conn)

    resultados = await grupos_module.buscar_grupos(q="zzz", payload={"sub": "u1"})
    assert resultados == []


@pytest.mark.asyncio
async def test_unirse_a_grupo(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", next_test_id)

    r = await grupos_module.crear_grupo(GrupoCreate(nombre="Fotografia"), payload={"sub": "u1"})

    respuesta = await grupos_module.unirse_a_grupo(grupo_id=r["id"], payload={"sub": "u2"})

    assert respuesta["unido"] is True
    assert f"{r['id']}:u2" in conn.miembros


@pytest.mark.asyncio
async def test_unirse_ya_miembro_idempotente(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", next_test_id)

    r = await grupos_module.crear_grupo(GrupoCreate(nombre="Fotografia"), payload={"sub": "u1"})

    respuesta = await grupos_module.unirse_a_grupo(grupo_id=r["id"], payload={"sub": "u1"})
    assert respuesta["unido"] is True


@pytest.mark.asyncio
async def test_lista_grupos_mios(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", next_test_id)

    g1 = await grupos_module.crear_grupo(GrupoCreate(nombre="Fotografia"), payload={"sub": "u1"})
    g2 = await grupos_module.crear_grupo(GrupoCreate(nombre="Musica"), payload={"sub": "u1"})
    await grupos_module.unirse_a_grupo(grupo_id=g2["id"], payload={"sub": "u2"})

    mios = await grupos_module.grupos_mios(payload={"sub": "u2"})

    assert len(mios) == 1
    assert mios[0]["id"] == g2["id"]


@pytest.mark.asyncio
async def test_enviar_mensaje_grupo(grupos_module, monkeypatch):
    from app.models import GrupoCreate, MensajeGrupoCreate

    conn = FakeConnection()
    patch_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", next_test_id)

    r = await grupos_module.crear_grupo(GrupoCreate(nombre="Fotografia"), payload={"sub": "u1"})

    msg = await grupos_module.enviar_mensaje_grupo(
        grupo_id=r["id"],
        datos=MensajeGrupoCreate(contenido="Hola grupo"),
        payload={"sub": "u1"},
    )

    assert msg["emisor_id"] == "u1"
    assert msg["contenido"] == "Hola grupo"
