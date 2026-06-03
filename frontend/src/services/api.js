// services/api.js
// Centraliza todas las llamadas a la API del backend.

const BASE_URL = "/api";
const WS_URL =
	window.location.protocol === "https:"
		? `wss://${window.location.host}/ws`
		: `ws://${window.location.host}/ws`;

// ── Token JWT ─────────────────────────────────────────────────────────────

let _token = sessionStorage.getItem("chat_token") || null;

export function getToken() {
	return _token;
}

export function setToken(token) {
	_token = token;
	if (token) {
		sessionStorage.setItem("chat_token", token);
	} else {
		sessionStorage.removeItem("chat_token");
	}
}

function authHeaders() {
	return _token ? { Authorization: `Bearer ${_token}` } : {};
}

// ── Usuarios ──────────────────────────────────────────────────────────────

export async function loginUsuario(email, nombre = null) {
	const body = { email };
	if (nombre !== null) body.nombre = nombre;

	const res = await fetch(`${BASE_URL}/usuarios/login`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(body),
	});
	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || "Error al iniciar sesión");
	}
	const data = await res.json();
	if (data.token) setToken(data.token);
	return data;
}

export async function registrarUsuario(nombre) {
	const res = await fetch(`${BASE_URL}/usuarios`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ nombre }),
	});
	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || "Error al registrar usuario");
	}
	const data = await res.json();
	if (data.token) setToken(data.token);
	return data;
}

export async function listarUsuarios() {
	const res = await fetch(`${BASE_URL}/usuarios`);
	if (!res.ok) throw new Error("Error al obtener usuarios");
	return res.json();
}

export async function obtenerIdIA() {
	const usuarios = await listarUsuarios();
	// Buscamos por "Lumi" (nombre actual) o "Asistente IA" (compatibilidad)
	// por si algún despliegue antiguo aún no se ha migrado.
	const ia = usuarios.find(
		(u) => u.nombre === "Lumi" || u.nombre === "Asistente IA",
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
			headers: authHeaders(),
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

export async function enviarMensaje(
	emisor_id,
	receptor_id,
	contenido,
	expiraEn = null,
) {
	const body = { emisor_id, receptor_id, contenido };
	if (expiraEn !== null) body.expira_en = expiraEn;

	const res = await fetch(`${BASE_URL}/mensaje_privado`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			...authHeaders(),
		},
		body: JSON.stringify(body),
	});
	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || "Error al enviar mensaje");
	}
	return res.json();
}

export async function obtenerConversacionBilateral(
	usuarioId,
	contactoId,
	{ limit = 50, beforeId = null } = {},
) {
	const params = new URLSearchParams({ limit: String(limit) });
	if (beforeId) params.set("before_id", String(beforeId));

	const res = await fetch(
		`${BASE_URL}/conversacion/${usuarioId}/${contactoId}?${params.toString()}`,
		{ headers: authHeaders() },
	);
	if (!res.ok) throw new Error("Error al obtener conversación");
	return res.json();
}

/**
 * Consulta los mensajes no leídos del usuario.
 * Retorna { no_leidos: total, por_contacto: { uuid: cantidad } }
 */
export async function obtenerNoLeidos(usuarioId) {
	try {
		const res = await fetch(`${BASE_URL}/no_leidos/${usuarioId}`, {
			headers: authHeaders(),
		});
		if (!res.ok) return { no_leidos: 0, por_contacto: {} };
		return await res.json();
	} catch {
		return { no_leidos: 0, por_contacto: {} };
	}
}

/**
 * Marca todos los mensajes con un contacto específico como leídos.
 * Se llama cuando el usuario abre el chat con ese contacto.
 */
export async function marcarComoLeidos(usuarioId, contactoId) {
	try {
		await fetch(`${BASE_URL}/no_leidos/${usuarioId}/${contactoId}`, {
			method: "DELETE",
			headers: authHeaders(),
		});
	} catch (error) {
		console.warn("Error al marcar como leídos:", error);
	}
}

// ── Inteligencia Artificial ───────────────────────────────────────────────

export async function enviarMensajeIA(emisor_id, ia_id, contenido) {
	const res = await fetch(`${BASE_URL}/ia/mensaje`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			...authHeaders(),
		},
		body: JSON.stringify({ emisor_id, receptor_id: ia_id, contenido }),
	});
	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || "El nodo IA no está disponible");
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

// ── Grupos ─────────────────────────────────────────────────────────────────

export async function crearGrupo(nombre) {
	const res = await fetch(`${BASE_URL}/grupos`, {
		method: "POST",
		headers: { "Content-Type": "application/json", ...authHeaders() },
		body: JSON.stringify({ nombre }),
	});
	if (!res.ok) throw new Error("Error al crear grupo");
	return res.json();
}

export async function buscarGrupos(q) {
	const res = await fetch(`${BASE_URL}/grupos/buscar?q=${encodeURIComponent(q)}`, {
		headers: authHeaders(),
	});
	if (!res.ok) throw new Error("Error al buscar grupos");
	return res.json();
}

export async function gruposMios() {
	const res = await fetch(`${BASE_URL}/grupos/mios`, {
		headers: authHeaders(),
	});
	if (!res.ok) throw new Error("Error al obtener grupos");
	return res.json();
}

export async function unirseAGrupo(grupoId) {
	const res = await fetch(`${BASE_URL}/grupos/${grupoId}/unirse`, {
		method: "POST",
		headers: authHeaders(),
	});
	if (!res.ok) throw new Error("Error al unirse al grupo");
	return res.json();
}

export async function mensajesGrupo(grupoId, { limit = 50, beforeId = null } = {}) {
	const params = new URLSearchParams({ limit: String(limit) });
	if (beforeId) params.set("before_id", String(beforeId));
	const res = await fetch(
		`${BASE_URL}/grupos/${grupoId}/mensajes?${params.toString()}`,
		{ headers: authHeaders() },
	);
	if (!res.ok) throw new Error("Error al obtener mensajes del grupo");
	return res.json();
}

export async function enviarMensajeGrupo(grupoId, contenido) {
	const res = await fetch(`${BASE_URL}/grupos/${grupoId}/mensajes`, {
		method: "POST",
		headers: { "Content-Type": "application/json", ...authHeaders() },
		body: JSON.stringify({ contenido }),
	});
	if (!res.ok) throw new Error("Error al enviar mensaje al grupo");
	return res.json();
}

// ── WebSocket ─────────────────────────────────────────────────────────────

export function crearWebSocket(usuarioId, onMensaje, onEstado) {
	let intentos = 0;
	let timeoutId = null;
	let ws = null;
	let cerradoManualmente = false;

	function conectar() {
		if (cerradoManualmente) return;

		const token = getToken();
		if (!token) {
			onEstado("desconectado");
			return;
		}

		ws = new WebSocket(`${WS_URL}/${usuarioId}`);

		ws.onopen = () => {
			// El token viaja en el primer mensaje, no en la URL,
			// para evitar que quede registrado en los logs de Nginx.
			ws.send(JSON.stringify({ tipo: "auth", token }));
			intentos = 0;
			onEstado("conectado");
		};

		ws.onmessage = (evento) => {
			try {
				const datos = JSON.parse(evento.data);
				onMensaje(datos);
			} catch {
				// mensaje malformado — ignorar
			}
		};

		ws.onclose = (evento) => {
			if (cerradoManualmente) return;
			if (evento.code === 4001 || evento.code === 4003) {
				onEstado("desconectado");
				return;
			}
			const espera = Math.min(1000 * 2 ** intentos, 30000);
			intentos++;
			onEstado("reconectando");
			timeoutId = setTimeout(conectar, espera);
		};

		ws.onerror = () => {
			ws.close();
		};
	}

	conectar();

	return function cerrar() {
		cerradoManualmente = true;
		clearTimeout(timeoutId);
		if (ws) ws.close();
	};
}
