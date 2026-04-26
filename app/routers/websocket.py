# routers/websocket.py
# Gestiona las conexiones WebSocket del sistema de chat.
#
# ConnectionManager mantiene en memoria todas las conexiones activas.
# Cuando un usuario envía un mensaje, el endpoint de mensajes llama
# a manager.notify(receptor_id) para avisar al receptor en tiempo real.
#
# El cliente React maneja la reconexión automática con backoff exponencial.
# El servidor solo necesita aceptar la conexión y mantenerla viva.

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Gestiona todas las conexiones WebSocket activas en memoria.
    Cada usuario puede tener una sola conexión activa a la vez.
    Si el mismo usuario se conecta dos veces, la conexión anterior
    se reemplaza por la nueva.
    """

    def __init__(self):
        # Mapa de usuario_id → conexión WebSocket activa
        self.conexiones: Dict[str, WebSocket] = {}

    async def conectar(self, usuario_id: str, websocket: WebSocket):
        """Acepta y registra una nueva conexión WebSocket."""
        await websocket.accept()
        self.conexiones[usuario_id] = websocket

    def desconectar(self, usuario_id: str):
        """Elimina la conexión del usuario cuando se desconecta."""
        self.conexiones.pop(usuario_id, None)

    async def notify(self, usuario_id: str, evento: dict):
        """
        Envía una notificación JSON al usuario si está conectado.
        Si el usuario no está conectado o la conexión falló,
        simplemente no hace nada — el polling de respaldo lo cubre.
        """
        websocket = self.conexiones.get(usuario_id)
        if websocket:
            try:
                await websocket.send_json(evento)
            except Exception:
                # Conexión rota — limpiar y dejar que el cliente reconecte
                self.desconectar(usuario_id)

    def esta_conectado(self, usuario_id: str) -> bool:
        """Verifica si un usuario tiene conexión WebSocket activa."""
        return usuario_id in self.conexiones


# Instancia global compartida por todos los routers
# Se importa desde mensajes.py para notificar al receptor
manager = ConnectionManager()


@router.websocket("/ws/{usuario_id}")
async def websocket_endpoint(websocket: WebSocket, usuario_id: str):
    """
    Endpoint WebSocket por usuario.
    Cada usuario se conecta a /ws/{su_id} al cargar el chat.
    El servidor mantiene la conexión viva y espera desconexiones.
    Las notificaciones llegan desde mensajes.py via manager.notify().
    """
    await manager.conectar(usuario_id, websocket)
    try:
        # Mantener la conexión viva esperando mensajes del cliente.
        # El cliente envía pings periódicos para mantener el canal abierto.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # El cliente cerró la conexión — limpiar registro
        manager.desconectar(usuario_id)