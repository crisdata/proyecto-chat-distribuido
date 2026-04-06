// services/api.js
// Centraliza todas las llamadas a la API del backend.
// Todos los componentes importan desde aquí, nunca hacen fetch directamente.
// BASE_URL usa /api que en desarrollo Vite redirige a FastAPI mediante proxy,
// y en producción Nginx hace el mismo trabajo sin cambiar una sola línea.

const BASE_URL = '/api';

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
  // ia_id se obtiene previamente con obtenerIdIA()
  // para usar el UUID real del nodo IA registrado en el sistema
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

// ── Utilidades ────────────────────────────────────────────────────────────

export function formatearHora(timestamp) {
  const fecha = new Date(timestamp);
  return fecha.toLocaleTimeString('es-CO', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
}

export function esHoy(timestamp) {
  const hoy = new Date();
  const fecha = new Date(timestamp);
  return hoy.toDateString() === fecha.toDateString();
}
