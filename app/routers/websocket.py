# routers/websocket.py
# Gestiona las conexiones WebSocket del sistema de chat.

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Dict

from app.auth import validar_token
from app.cache import marcar_presencia, quitar_presencia

router = APIRouter(tags=["WebSocket"])
log = logging.getLogger("websocket")

INTERVALO_REFRESCO_PRESENCIA = 30


class ConnectionManager:
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
        log.info(f"WebSocket aceptado para usuario {usuario_id}")

    async def desconectar(self, usuario_id: str, websocket: WebSocket = None):
        """Elimina la conexión solo si la que se desconecta es la registrada."""
        actual = self.conexiones.get(usuario_id)
        if actual is None:
            return
        if websocket is not None and actual is not websocket:
            return
        self.conexiones.pop(usuario_id, None)
        log.info(f"WebSocket removido para usuario {usuario_id}")

    async def notify(self, usuario_id: str, evento: dict):
        """Envía una notificación JSON al usuario si está conectado."""
        websocket = self.conexiones.get(usuario_id)
        if websocket:
            try:
                await websocket.send_json(evento)
            except Exception:
                await self.desconectar(usuario_id, websocket)

    def esta_conectado(self, usuario_id: str) -> bool:
        return usuario_id in self.conexiones


manager = ConnectionManager()


async def refrescar_presencia_periodicamente(usuario_id: str, websocket: WebSocket):
    """
    Tarea que corre en background mientras el WebSocket está activo.
    Refresca la presencia en Redis cada 30s para mantener al usuario
    marcado como online.
    """
    try:
        while True:
            await asyncio.sleep(INTERVALO_REFRESCO_PRESENCIA)
            if manager.conexiones.get(usuario_id) is websocket:
                try:
                    await marcar_presencia(usuario_id)
                    log.debug(f"Presencia refrescada para {usuario_id}")
                except Exception as e:
                    log.error(f"Error refrescando presencia de {usuario_id}: {e}")
            else:
                break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.warning(f"Tarea de refresco terminó con error para {usuario_id}: {e}")


@router.websocket("/ws/{usuario_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    usuario_id: str,
    token: str = Query(None)
):
    """
    Endpoint WebSocket por usuario.
    Marca presencia en Redis al conectar y la refresca cada 30s.
    """
    # Validar token
    if not token:
        await websocket.close(code=4001, reason="Token faltante")
        return

    try:
        payload = await validar_token(token)
    except HTTPException:
        await websocket.close(code=4001, reason="Token inválido")
        return

    if payload.get("sub") != usuario_id:
        await websocket.close(code=4003, reason="Token pertenece a otro usuario")
        return

    # Conectar al manager (acepta el WebSocket)
    await manager.conectar(usuario_id, websocket)

    # Marcar presencia EXPLÍCITAMENTE después de conectar.
    # Llamada separada con manejo de errores propio para que si falla,
    # quede registrado claramente en logs.
    try:
        await marcar_presencia(usuario_id)
        log.info(f"Presencia marcada como ONLINE para {usuario_id}")
    except Exception as e:
        log.error(f"FALLO al marcar presencia inicial de {usuario_id}: {e}")

    # Arrancar tarea background de refresco periódico
    tarea_presencia = asyncio.create_task(
        refrescar_presencia_periodicamente(usuario_id, websocket)
    )

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log.info(f"WebSocket desconectado limpiamente para {usuario_id}")
    except Exception as e:
        log.warning(f"Error en WebSocket de {usuario_id}: {e}")
    finally:
        # Cancelar tarea de refresco
        tarea_presencia.cancel()
        try:
            await tarea_presencia
        except asyncio.CancelledError:
            pass

        # Remover del manager
        await manager.desconectar(usuario_id, websocket)

        # Quitar presencia EXPLÍCITAMENTE
        try:
            await quitar_presencia(usuario_id)
            log.info(f"Presencia marcada como OFFLINE para {usuario_id}")
        except Exception as e:
            log.error(f"FALLO al quitar presencia de {usuario_id}: {e}")