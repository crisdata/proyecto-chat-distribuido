// services/api.js
// Centraliza todas las llamadas a la API del backend.
// Todos los componentes importan desde aquí, nunca hacen fetch directamente.
// BASE_URL usa /api que en desarrollo Vite redirige a FastAPI mediante proxy,
// y en producción Nginx hace el mismo trabajo sin cambiar una sola línea.

const BASE_URL = '/api';
const WS_URL = window.location.protocol === 'https:'
  ? `wss://${window.location.host}/ws`
  : `ws://${window.location.host}/ws`;

// ── Usuarios ──────────────────────────────────────────────────────────────

export async function registrarUsuario(nombre) {
  const res = await fetch(`${BASE_URL}/usuarios`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Error al registrar usuario');
  }
  return res.json();
}

export async function listarUsuarios() {
  const res = await fetch(`${BASE_URL}/usuarios`);
  if (!res.ok) throw new Error('Error al obtener usuarios');
  return res.json();
}

// Obtiene el ID real del nodo IA desde la lista de usuarios.
// El nodo IA se registra con el nombre "Asistente IA" al arrancar el servidor.
export async function obtenerIdIA() {
  const usuarios = await listarUsuarios();
  const ia = usuarios.find(u => u.nombre === 'Asistente IA');
  return ia ? ia.id : null;
}

// ── Mensajes ──────────────────────────────────────────────────────────────

export async function enviarMensaje(emisor_id, receptor_id, contenido) {
  const res = await fetch(`${BASE_URL}/mensaje_privado`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ emisor_id, receptor_id, contenido }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Error al enviar mensaje');
  }
  return res.json();
}

export async function obtenerConversacion(usuario_id) {
  const res = await fetch(`${BASE_URL}/conversacion/${usuario_id}`);
  if (!res.ok) throw new Error('Error al obtener conversación');
  return res.json();
}

export async function obtenerNoLeidos(usuario_id) {
  const res = await fetch(`${BASE_URL}/no_leidos/${usuario_id}`);
  if (!res.ok) return { no_leidos: 0 };
  return res.json();
}

// ── Inteligencia Artificial ───────────────────────────────────────────────

export async function enviarMensajeIA(emisor_id, ia_id, contenido) {
  const res = await fetch(`${BASE_URL}/ia/mensaje`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ emisor_id, receptor_id: ia_id, contenido }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'El nodo IA no está disponible');
  }
  return res.json();
}

export async function estadoIA() {
  try {
    const res = await fetch(`${BASE_URL}/ia/estado`);
    return { disponible: res.ok };
  } catch {
    return { disponible: false };
  }
}

// ── WebSocket ─────────────────────────────────────────────────────────────

/**
 * Crea y gestiona una conexión WebSocket con reconexión automática.
 *
 * onMensaje   — callback que se ejecuta al recibir una notificación
 * onEstado    — callback que recibe 'conectado' | 'reconectando' | 'desconectado'
 *
 * Retorna una función para cerrar la conexión manualmente,
 * usada en el cleanup del useEffect de Chat.jsx.
 *
 * Backoff exponencial:
 *   intento 1 → 1s, intento 2 → 2s, intento 3 → 4s ... máximo 30s
 */
export function crearWebSocket(usuarioId, onMensaje, onEstado) {
  let intentos = 0
  let timeoutId = null
  let ws = null
  let cerradoManualmente = false

  function conectar() {
    if (cerradoManualmente) return

    ws = new WebSocket(`${WS_URL}/${usuarioId}`)

    ws.onopen = () => {
      intentos = 0
      onEstado('conectado')
    }

    ws.onmessage = (evento) => {
      try {
        const datos = JSON.parse(evento.data)
        onMensaje(datos)
      } catch {
        // mensaje malformado — ignorar
      }
    }

    ws.onclose = () => {
      if (cerradoManualmente) return
      // Calcular tiempo de espera con backoff exponencial
      // mínimo 1s, máximo 30s
      const espera = Math.min(1000 * Math.pow(2, intentos), 30000)
      intentos++
      onEstado('reconectando')
      timeoutId = setTimeout(conectar, espera)
    }

    ws.onerror = () => {
      // Forzar onclose para disparar la reconexión
      ws.close()
    }
  }

  conectar()

  // Retorna función de cierre manual para el cleanup de useEffect
  return function cerrar() {
    cerradoManualmente = true
    clearTimeout(timeoutId)
    if (ws) ws.close()
  }
}

// ── Utilidades ────────────────────────────────────────────────────────────

export function formatearHora(timestamp) {
  // Agrega 'Z' si no tiene zona horaria para que JavaScript
  // lo interprete como UTC y lo convierta correctamente a hora local
  const ts = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z'
  const fecha = new Date(ts)
  return fecha.toLocaleTimeString('es-CO', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  })
}

export function esHoy(timestamp) {
  const ts = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z'
  const hoy = new Date()
  const fecha = new Date(ts)
  return hoy.toDateString() === fecha.toDateString()
}
