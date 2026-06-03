import os

# auth.py valida estas variables al importarse.
# En tests usamos valores locales y no secretos reales.
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("WORKER_SECRET", "test-worker-secret")

# ── Fake DB helpers (compartidos entre test_groups y test_memoryless) ────────

class FakeCursor:
    """Cursor falso con routing básico por tipo de consulta."""

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
            gid, nombre, nombre_normalizado, creado_por = params
            for existing in self._db.grupos.values():
                if existing["nombre_normalizado"] == nombre_normalizado:
                    raise Exception("Duplicate entry")
            self._db.grupos[gid] = {
                "id": gid, "nombre": nombre,
                "nombre_normalizado": nombre_normalizado, "creado_por": creado_por,
            }
            self._db.last_group = {"id": gid, "nombre": nombre, "creado_por": creado_por}

        elif "INSERT INTO GRUPO_MIEMBROS" in sql:
            gid, uid = params
            self._db.miembros[f"{gid}:{uid}"] = {"grupo_id": gid, "usuario_id": uid}

        elif "INSERT INTO MENSAJES_GRUPO" in sql:
            gid, uid, contenido = params
            self._db.mensajes_grupo.append(
                {"grupo_id": gid, "emisor_id": uid, "contenido": contenido}
            )
            self.lastrowid = len(self._db.mensajes_grupo)

        elif "SELECT" in sql and "FROM GRUPOS" in sql:
            self._group_select(sql, params)

        elif "SELECT" in sql and "FROM MENSAJES_GRUPO" in sql:
            self._message_select(sql, params)

        elif "SELECT USUARIO_ID FROM GRUPO_MIEMBROS" in sql:
            gid = params[0]
            self._result = [
                [m["usuario_id"]]
                for m in self._db.miembros.values()
                if m["grupo_id"] == gid
            ]

        elif "SELECT 1 FROM GRUPO_MIEMBROS" in sql:
            gid, uid = params
            self._result = [[1]] if f"{gid}:{uid}" in self._db.miembros else []

    def _group_select(self, sql, params):
        if "LIKE" in sql:
            q = params[0].replace("%", "").lower() if params else ""
            self._result = [
                [g["id"], g["nombre"], g["creado_por"], None]
                for g in self._db.grupos.values()
                if q in g["nombre_normalizado"]
            ]
        elif "JOIN GRUPO_MIEMBROS" in sql:
            uid = params[0] if params else ""
            self._result = [
                [g["id"], g["nombre"], g["creado_por"], None]
                for g in (self._db.grupos.get(m["grupo_id"]) for m in self._db.miembros.values()
                          if m["usuario_id"] == uid) if g
            ]
        elif "WHERE ID = %S" in sql:
            g = self._db.grupos.get(params[0])
            self._result = [[g["id"], g["nombre"], g["creado_por"], None]] if g else []

    def _message_select(self, sql, params):
        if "JOIN USUARIOS" in sql and "WHERE MG.ID = %S" in sql:
            # SELECT by message id with JOIN: [id, grupo_id, emisor_id, nombre, contenido, timestamp]
            msg_id = params[0]
            idx = msg_id - 1
            if 0 <= idx < len(self._db.mensajes_grupo):
                m = self._db.mensajes_grupo[idx]
                self._result = [[idx + 1, m["grupo_id"], m["emisor_id"],
                                 "Usuario", m["contenido"], "2026-06-03T00:00:00"]]
            else:
                self._result = []
        elif "JOIN USUARIOS" in sql and "WHERE MG.GRUPO_ID" in sql:
            gid = params[0] if params else None
            msgs = [m for m in self._db.mensajes_grupo if m["grupo_id"] == gid]
            self._result = [
                [i + 1, m["grupo_id"], m["emisor_id"], "Usuario",
                 m["contenido"], "2026-06-03T00:00:00"]
                for i, m in enumerate(msgs)
            ]
        elif "WHERE ID = %S" in sql:
            idx = params[0] - 1
            if 0 <= idx < len(self._db.mensajes_grupo):
                m = self._db.mensajes_grupo[idx]
                self._result = [[idx + 1, m["grupo_id"], m["emisor_id"],
                                 m["contenido"], "2026-06-03T00:00:00", None]]
            else:
                self._result = []
        elif "WHERE MG" in sql or "WHERE M.ID" in sql:
            gid = params[0] if params else None
            msgs = [m for m in self._db.mensajes_grupo if m["grupo_id"] == gid]
            self._result = [
                [i + 1, m["grupo_id"], m["emisor_id"], m["contenido"],
                 "2026-06-03T00:00:00", None]
                for i, m in enumerate(msgs)
            ]
        else:
            gid = params[0] if params else None
            msgs = [m for m in self._db.mensajes_grupo if m["grupo_id"] == gid]
            self._result = [
                [i + 1, m["grupo_id"], m["emisor_id"], m["contenido"],
                 "2026-06-03T00:00:00", None]
                for i, m in enumerate(msgs)
            ]

    async def fetchone(self):
        r = self._result
        if isinstance(r, list) and r:
            return r[0]
        return r if r and not isinstance(r, list) else None

    async def fetchall(self):
        r = self._result
        return [] if r is None else (r if isinstance(r, list) else [r])


class FakeConnection:
    """Conexión falsa con estado en memoria para tests de grupos/cache."""

    def __init__(self):
        self.grupos = {}
        self.miembros = {}
        self.mensajes_grupo = []
        self.seen_queries = []
        self.last_group = None

    def cursor(self):
        return FakeCursor(self)


class FakeRedis:
    """Redis falso en memoria."""

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
            import fnmatch
            keys = [k for k in self.data if fnmatch.fnmatch(k, match)]
            return (0, keys)
        return (0, [])

    async def mget(self, *keys):
        return [str(self.data.get(k, 0)) for k in keys]

    def pipeline(self):
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, redis):
        self._redis = redis
        self._cmds = []

    def setex(self, *args):
        self._cmds.append(("setex", *args))

    def delete(self, *keys):
        self._cmds.append(("delete", *keys))

    def exists(self, key):
        self._cmds.append(("exists", key))

    def get(self, key):
        self._cmds.append(("get", key))

    async def execute(self):
        results = []
        for cmd in self._cmds:
            a = cmd[0]
            if a == "setex":
                await self._redis.setex(cmd[1], cmd[2], cmd[3])
                results.append(True)
            elif a == "delete":
                await self._redis.delete(*cmd[1:])
                results.append(1)
            elif a == "exists":
                results.append(1 if cmd[1] in self._redis.data else 0)
            elif a == "get":
                results.append(self._redis.data.get(cmd[1]))
        return results


def patch_deps(monkeypatch, mod, conn, fake_redis=None):
    """Monkeypatchea conexión DB, Redis, locks y uuid en un router de test."""

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

    monkeypatch.setattr(mod, "get_connection", fake_get_connection)
    monkeypatch.setattr(mod, "release_connection", fake_release)
    monkeypatch.setattr(mod, "adquirir_lock", fake_adquirir_lock)
    monkeypatch.setattr(mod, "liberar_lock", fake_liberar_lock)
    monkeypatch.setattr(mod, "get_redis", lambda: fake_redis)


_id_counter = 0


def next_test_id():
    global _id_counter
    _id_counter += 1
    return f"g{_id_counter}"
