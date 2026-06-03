# pyright: reportMissingImports=false
import importlib
import uuid as _uuid

import pytest
from pydantic import ValidationError


# ── Fake DB helpers ──────────────────────────────────────────────────────────

class FakeCursor:
    def __init__(self, db):
        self._db = db
        self._result = None
        self.lastrowid = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, query, params=None):
        assert params is not None
        sql = " ".join(query.upper().split())
        self._db.seen_queries.append(sql)

        if "INSERT INTO GRUPOS" in sql:
            self._group_insert(params)
        elif "INSERT INTO GRUPO_MIEMBROS" in sql:
            self._member_insert(params)
        elif "INSERT INTO MENSAJES_GRUPO" in sql:
            self._message_insert(params)
        elif "SELECT" in sql and "FROM GRUPOS" in sql:
            await self._group_select(sql, params)
        elif "SELECT" in sql and "MENSAJES_GRUPO" in sql:
            await self._message_select(sql, params)
        elif "SELECT USUARIO_ID FROM GRUPO_MIEMBROS" in sql:
            gid = params[0]
            uids = [
                [m["usuario_id"]]
                for m in self._db.miembros.values()
                if m["grupo_id"] == gid
            ]
            self._result = uids

        elif "SELECT 1 FROM GRUPO_MIEMBROS" in sql:
            await self._membership_check(params)

    # ── sync helpers ─────────────────────────────────────────────────────

    def _group_insert(self, params):
        gid, nombre, nombre_normalizado, creado_por = params
        
        # Simulate unique constraint on nombre_normalizado
        for existing in self._db.grupos.values():
            if existing["nombre_normalizado"] == nombre_normalizado:
                raise Exception("Duplicate entry for key 'nombre_normalizado'")

        self._db.grupos[gid] = {
            "id": gid,
            "nombre": nombre,
            "nombre_normalizado": nombre_normalizado,
            "creado_por": creado_por,
        }
        self._db.last_group = {"id": gid, "nombre": nombre, "creado_por": creado_por}
        self._result = None

    def _member_insert(self, params):
        gid, uid = params
        key = f"{gid}:{uid}"
        self._db.miembros[key] = {"grupo_id": gid, "usuario_id": uid, "rol": "miembro"}
        self._result = None

    def _message_insert(self, params):
        gid, uid, contenido = params
        self._db.mensajes_grupo.append(
            {"grupo_id": gid, "emisor_id": uid, "contenido": contenido}
        )
        self.lastrowid = len(self._db.mensajes_grupo)
        self._result = None

    # ── async helpers ────────────────────────────────────────────────────

    async def _group_select(self, sql, params):
        if "WHERE " in sql and "LIKE" in sql:
            q = params[0].replace("%", "").lower() if params else ""
            rows = [
                [g["id"], g["nombre"], g["creado_por"], None]
                for g in self._db.grupos.values()
                if q in g["nombre_normalizado"]
            ]
            self._result = rows if rows else []
            return

        if "WHERE ID = %S" in sql:
            gid = params[0]
            g = self._db.grupos.get(gid)
            if g:
                self._result = [[g["id"], g["nombre"], g["creado_por"], None]]
            else:
                self._result = []
            return

        if "JOIN GRUPO_MIEMBROS" in sql:
            uid = params[0] if params else ""
            rows = []
            for key, m in self._db.miembros.items():
                if m["usuario_id"] == uid:
                    gid = m["grupo_id"]
                    g = self._db.grupos.get(gid)
                    if g:
                        rows.append([g["id"], g["nombre"], g["creado_por"], None])
            self._result = rows
            return

        self._result = []

    async def _message_select(self, sql, params):
        # Two possible queries: by grupo_id or by individual message id
        if "WHERE ID = %S" in sql:
            msg_id = params[0]
            idx = msg_id - 1
            if 0 <= idx < len(self._db.mensajes_grupo):
                m = self._db.mensajes_grupo[idx]
                msgs = [
                    [idx + 1, m["grupo_id"], m["emisor_id"], m["contenido"],
                     "2026-06-03T00:00:00", None]  # noqa: E124
                ]
            else:
                msgs = []
        else:
            gid = params[0] if params else None
            msgs = [m for m in self._db.mensajes_grupo if m["grupo_id"] == gid]
            msgs = [
                [i + 1, m["grupo_id"], m["emisor_id"], m["contenido"],
                 "2026-06-03T00:00:00", None]  # noqa: E124
                for i, m in enumerate(msgs)
            ]
        self._result = msgs

    async def _membership_check(self, params):
        gid, uid = params
        key = f"{gid}:{uid}"
        self._result = [[1]] if key in self._db.miembros else []

    async def fetchone(self):
        r = self._result
        if isinstance(r, list) and len(r) > 0:
            return r[0]
        if isinstance(r, list) and len(r) == 0:
            return None
        if r is None:
            return None
        return r

    async def fetchall(self):
        r = self._result
        if r is None:
            return []
        if isinstance(r, list):
            return r
        return [r]


class FakeConnection:
    def __init__(self):
        self.grupos = {}
        self.miembros = {}
        self.mensajes_grupo = []
        self.seen_queries = []
        self.last_group = None

    def cursor(self):
        return FakeCursor(self)


class FakeRedis:
    def __init__(self):
        self.data = {}

    async def setex(self, key, ttl, value):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)

    async def incr(self, key):
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]

    async def delete(self, *keys):
        for k in keys:
            self.data.pop(k, None)

    async def exists(self, key):
        return 1 if key in self.data else 0

    async def scan(self, cursor=0, match="*", count=100):
        if cursor == 0:
            keys = [k for k in self.data.keys() if self._match(k, match)]
            return (0, keys)
        return (0, [])

    async def mget(self, *keys):
        return [str(self.data.get(k, 0)) for k in keys]

    @staticmethod
    def _match(key, pattern):
        import fnmatch
        return fnmatch.fnmatch(key, pattern)

    def pipeline(self):
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, redis):
        self._redis = redis
        self._commands = []

    def setex(self, key, ttl, value):
        self._commands.append(("setex", key, ttl, value))

    def delete(self, *keys):
        self._commands.append(("delete", *keys))

    def exists(self, key):
        self._commands.append(("exists", key))

    def get(self, key):
        self._commands.append(("get", key))

    async def execute(self):
        results = []
        for cmd in self._commands:
            if cmd[0] == "setex":
                await self._redis.setex(cmd[1], cmd[2], cmd[3])
                results.append(True)
            elif cmd[0] == "delete":
                await self._redis.delete(*cmd[1:])
                results.append(1)
            elif cmd[0] == "exists":
                results.append(1 if cmd[1] in self._redis.data else 0)
            elif cmd[0] == "get":
                results.append(self._redis.data.get(cmd[1]))
        return results


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def grupos_module(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("WORKER_SECRET", "test-worker-secret")

    import app.routers.grupos as grupos

    return importlib.reload(grupos)


def patch_grupos_deps(monkeypatch, grupos_module, conn, fake_redis=None):
    async def fake_get_connection():
        return conn

    async def fake_release(_conn):
        return None

    async def fake_adquirir_lock(_key):
        return "lock"

    async def fake_liberar_lock(_key, _token):
        return None

    if fake_redis is None:
        fake_redis = FakeRedis()

    monkeypatch.setattr(grupos_module, "get_connection", fake_get_connection)
    monkeypatch.setattr(grupos_module, "release_connection", fake_release)
    monkeypatch.setattr(grupos_module, "adquirir_lock", fake_adquirir_lock)
    monkeypatch.setattr(grupos_module, "liberar_lock", fake_liberar_lock)
    monkeypatch.setattr(grupos_module, "get_redis", lambda: fake_redis)


_id_counter = 0


def _next_id():
    global _id_counter
    _id_counter += 1
    return f"g{_id_counter}"


# ── Model validation (fast) ──────────────────────────────────────────────────

def test_grupo_nombre_requerido():
    from app.models import GrupoCreate

    with pytest.raises(ValidationError):
        GrupoCreate()


def test_grupo_nombre_vacio():
    from app.models import GrupoCreate

    with pytest.raises(ValidationError):
        GrupoCreate(nombre="")


def test_grupo_nombre_valido():
    from app.models import GrupoCreate

    g = GrupoCreate(nombre="  Programación  ")

    assert g.nombre == "Programación"


# ── RED: Endpoint tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_grupo_auto_agrega_creador(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    fake_redis = FakeRedis()
    patch_grupos_deps(monkeypatch, grupos_module, conn, fake_redis)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", _next_id)

    respuesta = await grupos_module.crear_grupo(
        GrupoCreate(nombre="Futbol"),
        payload={"sub": "u1"},
    )

    assert "id" in respuesta
    assert respuesta["nombre"] == "Futbol"
    assert respuesta["es_miembro"] is True
    assert respuesta["modo"] == "grupo_publico"
    miembro_key = f"{respuesta['id']}:u1"
    assert miembro_key in conn.miembros


@pytest.mark.asyncio
async def test_grupo_nombre_duplicado_rechazado(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_grupos_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", _next_id)

    await grupos_module.crear_grupo(GrupoCreate(nombre="Futbol"), payload={"sub": "u1"})

    with pytest.raises(Exception) as exc:
        await grupos_module.crear_grupo(
            GrupoCreate(nombre="futbol"), payload={"sub": "u2"}
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_buscar_grupos_por_nombre_parcial(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_grupos_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", _next_id)

    await grupos_module.crear_grupo(GrupoCreate(nombre="Futbol Club"), payload={"sub": "u1"})
    await grupos_module.crear_grupo(GrupoCreate(nombre="Futbol Sala"), payload={"sub": "u1"})
    await grupos_module.crear_grupo(GrupoCreate(nombre="Cine"), payload={"sub": "u1"})

    resultados = await grupos_module.buscar_grupos(
        q="futbol", payload={"sub": "u1"}
    )

    assert len(resultados) == 2
    nombres = {g["nombre"] for g in resultados}
    assert {"Futbol Club", "Futbol Sala"} <= nombres


@pytest.mark.asyncio
async def test_buscar_grupos_sin_resultados(grupos_module, monkeypatch):
    conn = FakeConnection()
    patch_grupos_deps(monkeypatch, grupos_module, conn)

    resultados = await grupos_module.buscar_grupos(
        q="zzz", payload={"sub": "u1"}
    )

    assert resultados == []


@pytest.mark.asyncio
async def test_unirse_a_grupo(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_grupos_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", _next_id)

    r = await grupos_module.crear_grupo(GrupoCreate(nombre="Fotografia"), payload={"sub": "u1"})
    gid = r["id"]

    respuesta = await grupos_module.unirse_a_grupo(
        grupo_id=gid, payload={"sub": "u2"}
    )

    assert respuesta["unido"] is True
    assert f"{gid}:u2" in conn.miembros


@pytest.mark.asyncio
async def test_unirse_ya_miembro_idempotente(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_grupos_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", _next_id)

    r = await grupos_module.crear_grupo(GrupoCreate(nombre="Fotografia"), payload={"sub": "u1"})
    gid = r["id"]

    respuesta = await grupos_module.unirse_a_grupo(grupo_id=gid, payload={"sub": "u1"})
    assert respuesta["unido"] is True


@pytest.mark.asyncio
async def test_lista_grupos_mios(grupos_module, monkeypatch):
    from app.models import GrupoCreate

    conn = FakeConnection()
    patch_grupos_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", _next_id)

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
    patch_grupos_deps(monkeypatch, grupos_module, conn)
    monkeypatch.setattr(grupos_module.uuid, "uuid4", _next_id)

    r = await grupos_module.crear_grupo(GrupoCreate(nombre="Fotografia"), payload={"sub": "u1"})
    gid = r["id"]

    msg = await grupos_module.enviar_mensaje_grupo(
        grupo_id=gid,
        datos=MensajeGrupoCreate(contenido="Hola grupo"),
        payload={"sub": "u1"},
    )

    assert msg["emisor_id"] == "u1"
    assert msg["contenido"] == "Hola grupo"
