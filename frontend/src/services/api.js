// services/api.js
// Centraliza todas las llamadas a la API del backend.

const BASE_URL = '/api';
const WS_URL = window.location.protocol === 'https:'
  ? `wss://${window.location.host}/ws`
  : `ws://${window.location.host}/ws`;

// ── Token JWT ─────────────────────────────────────────────────────────────

let _token = sessionStorage.getItem('chat_token') || null;

export function getToken() {
  return _token;
}

export function setToken(token) {
  _token = token;
  if (token) {
    sessionStorage.setItem('chat_token', token);
  } else {
    sessionStorage.removeItem('chat_token');
  }
}

function authHeaders() {
  return _token ? { 'Authorization': `Bearer ${_token}` } : {};
}

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
  const data = await res.json();
  if (data.token) setToken(data.token);
  return data;
}

export async function listarUsuarios() {
  const res = await fetch(`${BASE_URL}/usuarios`);
  if (!res.ok) throw new Error('Error al obtener usuarios');
  return res.json();
}

export async function obtenerIdIA() {
  const usuarios = await listarUsuarios();
  // Buscamos por "Lumi" (nombre actual) o "Asistente IA" (compatibilidad)
  // por si algún despliegue antiguo aún no se ha migrado.
  const ia = usuarios.find(u =>
    u.nombre === 'Lumi' || u.nombre === 'Asistente IA'
  );
  return ia ? ia.id : null;
}

// Recupera el usuario actual desde el token guardado en sessionStorage.
// Retorna null si no hay token o si el token es inválido/expiró.
// El frontend usa esto al cargar la página para restaurar la sesión.
export async function obtenerUsuarioActual() {
  if (!_token) return null;

  try {
    const res = await fetch(`${BASE_URL}/usuarios/me`, {
      headers: authHeaders()
    });
    if (!res.ok) {
      // Token inválido o expirado — limpiar para forzar nuevo login
      setToken(null);
      return null;
    }
    return await res.json();
  } catch {
    setToken(null);
    return null;
  }
}

// ── Mensajes ──────────────────────────────────────────────────────────────

export async function enviarMensaje(emisor_id, receptor_id, contenido) {
  const res = await fetch(`${BASE_URL}/mensaje_privado`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
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
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
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

export function crearWebSocket(usuarioId, onMensaje, onEstado) {
  let intentos = 0
  let timeoutId = null
  let ws = null
  let cerradoManualmente = false

  function conectar() {
    if (cerradoManualmente) return

    const token = getToken()
    if (!token) {
      onEstado('desconectado')
      return
    }

    ws = new WebSocket(`${WS_URL}/${usuarioId}?token=${encodeURIComponent(token)}`)

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

    ws.onclose = (evento) => {
      if (cerradoManualmente) return
      if (evento.code === 4001 || evento.code === 4003) {
        onEstado('desconectado')
        return
      }
      const espera = Math.min(1000 * Math.pow(2, intentos), 30000)
      intentos++
      onEstado('reconectando')
      timeoutId = setTimeout(conectar, espera)
    }

    ws.onerror = () => {
      ws.close()
    }
  }

  conectar()

  return function cerrar() {
    cerradoManualmente = true
    clearTimeout(timeoutId)
    if (ws) ws.close()
  }
}

// ── Utilidades ────────────────────────────────────────────────────────────

export function formatearHora(timestamp) {
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