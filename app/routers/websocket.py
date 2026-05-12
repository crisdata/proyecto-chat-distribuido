# routers/websocket.py
# Gestiona las conexiones WebSocket del sistema de chat.
#
# El cliente debe pasar un token JWT como query parameter:
#   ws://host/ws/{usuario_id}?token=<jwt>
#
# El servidor valida que el token sea válido y que el 'sub' del token
# coincida con el usuario_id de la URL. Si no, cierra la conexión
# con código 4001 (autenticación fallida) sin aceptarla.

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict
from app.auth import validar_token
from fastapi import HTTPException

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Gestiona todas las conexiones WebSocket activas en memoria.
    Cada usuario puede tener una sola conexión activa a la vez.
    """

    def __init__(self):
        self.conexiones: Dict[str, WebSocket] = {}

    async def conectar(self, usuario_id: str, websocket: WebSocket):
        """
        Acepta y registra una nueva conexión WebSocket.
        Si el usuario ya tenía una conexión activa, la cierra primero.
        """
        anterior = self.conexiones.get(usuario_id)
        if anterior is not None:
            try:
                await anterior.close(
                    code=1000,
                    reason="Reemplazada por nueva conexión"
                )
            except Exception:
                pass

        await websocket.accept()
        self.conexiones[usuario_id] = websocket

    def desconectar(self, usuario_id: str, websocket: WebSocket = None):
        """
        Elimina la conexión solo si la que se desconecta es la registrada.
        """
        actual = self.conexiones.get(usuario_id)
        if actual is None:
            return
        if websocket is not None and actual is not websocket:
            return
        self.conexiones.pop(usuario_id, None)

    async def notify(self, usuario_id: str, evento: dict):
        """Envía una notificación JSON al usuario si está conectado."""
        websocket = self.conexiones.get(usuario_id)
        if websocket:
            try:
                await websocket.send_json(evento)
            except Exception:
                self.desconectar(usuario_id, websocket)

    def esta_conectado(self, usuario_id: str) -> bool:
        return usuario_id in self.conexiones


manager = ConnectionManager()


@router.websocket("/ws/{usuario_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    usuario_id: str,
    token: str = Query(None)
):
    """
    Endpoint WebSocket por usuario.
    Requiere un token JWT válido como query parameter.
    El 'sub' del token debe coincidir con el usuario_id de la URL.

    Códigos de cierre personalizados:
      4001 — token faltante o inválido
      4003 — el token pertenece a otro usuario
    """
    # Validar presencia del token
    if not token:
        await websocket.close(code=4001, reason="Token faltante")
        return

    # Validar firma y vigencia del token
    try:
        payload = await validar_token(token)
    except HTTPException:
        await websocket.close(code=4001, reason="Token inválido")
        return

    # Verificar que el token pertenece al usuario que dice ser
    if payload.get("sub") != usuario_id:
        await websocket.close(code=4003, reason="Token pertenece a otro usuario")
        return

    # Token válido — conectar
    await manager.conectar(usuario_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.desconectar(usuario_id, websocket)
    except Exception:
        manager.desconectar(usuario_id, websocket)