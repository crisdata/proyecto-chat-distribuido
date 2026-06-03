import importlib

import pytest
from pydantic import ValidationError


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.result = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, query, params=None):
        assert params is not None
        sql = " ".join(query.upper().split())
        if "WHERE EMAIL =" in sql:
            self.result = self.conn.users_by_email.get(params[0])
        elif "INSERT INTO USUARIOS" in sql:
            usuario_id, nombre, email = params
            user = (usuario_id, nombre, None)
            self.conn.users_by_email[email] = user
            self.conn.users_by_id[usuario_id] = user
            self.conn.last_inserted = {"id": usuario_id, "nombre": nombre, "email": email}
            self.result = None
        elif "WHERE ID =" in sql:
            self.result = self.conn.users_by_id.get(params[0])
        else:
            raise AssertionError(f"Unexpected query: {query}")

    async def fetchone(self):
        return self.result


class FakeConnection:
    def __init__(self, users_by_email=None):
        self.users_by_email = users_by_email or {}
        self.users_by_id = {user[0]: user for user in self.users_by_email.values()}
        self.last_inserted = None

    def cursor(self):
        return FakeCursor(self)


@pytest.fixture
def usuarios_module(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("WORKER_SECRET", "test-worker-secret")

    import app.auth as auth
    import app.routers.usuarios as usuarios

    importlib.reload(auth)
    return importlib.reload(usuarios)


def patch_login_deps(monkeypatch, usuarios_module, conn, token="token"):
    async def fake_get_connection():
        return conn

    async def fake_release(_conn):
        return None

    async def fake_adquirir_lock(_key):
        return "lock"

    async def fake_liberar_lock(_key, _token):
        return None

    async def fake_crear_token(_usuario_id):
        return token

    async def fake_cachear_usuario(*_args):
        return None

    class FakeRedis:
        async def setex(self, *_args):
            return None

    monkeypatch.setattr(usuarios_module, "get_connection", fake_get_connection)
    monkeypatch.setattr(usuarios_module, "release_connection", fake_release)
    monkeypatch.setattr(usuarios_module, "adquirir_lock", fake_adquirir_lock)
    monkeypatch.setattr(usuarios_module, "liberar_lock", fake_liberar_lock)
    monkeypatch.setattr(usuarios_module, "crear_token", fake_crear_token)
    monkeypatch.setattr(usuarios_module, "cachear_usuario", fake_cachear_usuario)
    monkeypatch.setattr(usuarios_module, "get_redis", lambda: FakeRedis())


def test_email_se_normaliza_minusculas_y_trim():
    from app.models import UsuarioLoginRequest

    datos = UsuarioLoginRequest(email="  User@Example.COM  ")

    assert datos.email == "user@example.com"


@pytest.mark.parametrize("email", ["", "   "])
def test_email_rechaza_nulos_vacios(email):
    from app.models import UsuarioLoginRequest

    with pytest.raises(ValidationError):
        UsuarioLoginRequest(email=email)


@pytest.mark.asyncio
async def test_login_con_email_conocido_devuelve_token(usuarios_module, monkeypatch):
    from app.models import UsuarioLoginRequest

    conn = FakeConnection({"user@example.com": ("u1", "Alice", None)})
    patch_login_deps(monkeypatch, usuarios_module, conn, token="token-u1")

    respuesta = await usuarios_module.login_usuario(
        UsuarioLoginRequest(email="  USER@example.com  ")
    )

    assert respuesta == {
        "id": "u1",
        "nombre": "Alice",
        "creado_en": None,
        "token": "token-u1",
        "requiere_nombre": False,
    }
    assert "email" not in respuesta


@pytest.mark.asyncio
async def test_login_con_email_nuevo_sin_nombre_devuelve_requiere_nombre(
    usuarios_module, monkeypatch
):
    from app.models import UsuarioLoginRequest

    conn = FakeConnection()
    patch_login_deps(monkeypatch, usuarios_module, conn)

    respuesta = await usuarios_module.login_usuario(
        UsuarioLoginRequest(email="new@example.com")
    )

    assert respuesta == {
        "requiere_nombre": True,
        "mensaje": "Indica tu nombre visible para completar el registro.",
    }


@pytest.mark.asyncio
async def test_login_con_email_nuevo_con_nombre_crea_cuenta(usuarios_module, monkeypatch):
    from app.models import UsuarioLoginRequest

    conn = FakeConnection()
    patch_login_deps(monkeypatch, usuarios_module, conn, token="token-new")
    monkeypatch.setattr(usuarios_module.uuid, "uuid4", lambda: "new-id")

    respuesta = await usuarios_module.login_usuario(
        UsuarioLoginRequest(email="new@example.com", nombre="Bob Smith")
    )

    assert respuesta["id"] == "new-id"
    assert respuesta["nombre"] == "Bob Smith"
    assert respuesta["token"] == "token-new"
    assert respuesta["requiere_nombre"] is False
    assert "email" not in respuesta
    assert conn.last_inserted == {
        "id": "new-id",
        "nombre": "Bob Smith",
        "email": "new@example.com",
    }


@pytest.mark.asyncio
async def test_login_same_email_different_case_returns_existing(
    usuarios_module, monkeypatch
):
    from app.models import UsuarioLoginRequest

    conn = FakeConnection({"user@example.com": ("u1", "Alice", None)})
    patch_login_deps(monkeypatch, usuarios_module, conn, token="token-u1")

    respuesta = await usuarios_module.login_usuario(
        UsuarioLoginRequest(email="USER@example.com", nombre="Mallory")
    )

    assert respuesta["id"] == "u1"
    assert respuesta["nombre"] == "Alice"
    assert conn.last_inserted is None


@pytest.mark.parametrize("nombre", ["", "a", " " * 3, "x" * 101])
def test_login_display_name_valida_longitud(nombre):
    from app.models import UsuarioLoginRequest

    with pytest.raises(ValidationError):
        UsuarioLoginRequest(email="new@example.com", nombre=nombre)


@pytest.mark.asyncio
async def test_jwt_no_incluye_email_ni_nombre(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("WORKER_SECRET", "test-worker-secret")

    import app.auth as auth

    auth = importlib.reload(auth)
    sesiones = {}

    async def fake_guardar_sesion(usuario_id, token, ttl=3600):
        sesiones[usuario_id] = token

    async def fake_obtener_sesion(usuario_id):
        return sesiones.get(usuario_id)

    monkeypatch.setattr(auth, "guardar_sesion", fake_guardar_sesion)
    monkeypatch.setattr(auth, "obtener_sesion", fake_obtener_sesion)

    token = await auth.crear_token("u1")
    payload = await auth.validar_token(token)

    assert payload["sub"] == "u1"
    assert "email" not in payload
    assert "nombre" not in payload
