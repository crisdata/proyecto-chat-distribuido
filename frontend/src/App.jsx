// App.jsx
// Componente raíz de la aplicación.
// Gestiona el estado global y aplica el contenedor con la paleta Vibe.
//
// Los polling de presencia y no leídos viven aquí porque App.jsx es el
// único componente que NUNCA se desmonta mientras hay sesión activa.

import { useState, useEffect, useRef, useMemo } from "react";
import { MessageCircle } from "lucide-react";
import Registro from "./components/Registro";
import Sidebar from "./components/Sidebar";
import ListaContactos from "./components/ListaContactos";
import Chat from "./components/Chat";
import {
	listarUsuarios,
	obtenerIdIA,
	obtenerUsuarioActual,
	obtenerNoLeidos,
	marcarComoLeidos,
	crearWebSocket,
	setToken,
	gruposMios,
} from "./services/api";
import { usePresencia } from "./hooks/usePresencia";

export default function App() {
	const [usuario, setUsuario] = useState(null);
	const [contactos, setContactos] = useState([]);
	const [contactoActivo, setContactoActivo] = useState(null);
	const [iaId, setIaId] = useState(null);
	const [grupos, setGrupos] = useState([]);
	const [cargandoSesion, setCargandoSesion] = useState(true);
	const [noLeidos, setNoLeidos] = useState({ total: 0, porContacto: {} });
	const [actualizacionMensajes, setActualizacionMensajes] = useState(0);
	const [mensajeSinMemoriaEntrante, setMensajeSinMemoriaEntrante] = useState(null);

	const huellaContactosRef = useRef("");
	const contactoActivoRef = useRef(null);
	contactoActivoRef.current = contactoActivo;

	const idsParaPresencia = useMemo(
		() => contactos.map((c) => c.id),
		[contactos],
	);

	const presencias = usePresencia(idsParaPresencia);

	// Restaurar sesión al montar
	useEffect(() => {
		async function restaurarSesion() {
			const usuarioRecuperado = await obtenerUsuarioActual();
			if (usuarioRecuperado) {
				setUsuario(usuarioRecuperado);
			}
			setCargandoSesion(false);
		}
		restaurarSesion();
	}, []);

	// Polling de contactos cada 10s
	useEffect(() => {
		if (!usuario) return;

		async function cargarDatos() {
			try {
				const [usuarios, idIA] = await Promise.all([
					listarUsuarios(),
					obtenerIdIA(),
				]);

				const nuevosContactos = usuarios.filter((u) => u.id !== usuario.id);
				const nuevaHuella = nuevosContactos
					.map((c) => `${c.id}:${c.nombre}`)
					.sort()
					.join("|");

				if (nuevaHuella !== huellaContactosRef.current) {
					huellaContactosRef.current = nuevaHuella;
					setContactos(nuevosContactos);
				}

				setIaId((prev) => (prev === idIA ? prev : idIA));
			} catch (error) {
				console.error("Error al cargar contactos:", error);
			}
		}

		cargarDatos();
		const intervalo = setInterval(cargarDatos, 10000);
		return () => clearInterval(intervalo);
	}, [usuario]);

	// Polling de grupos unidos cada 10s
	useEffect(() => {
		if (!usuario) return;

		async function cargarGrupos() {
			try {
				const data = await gruposMios();
				setGrupos(data);
			} catch (e) {
				console.error("Error al cargar grupos:", e);
			}
		}

		cargarGrupos();
		const intervalo = setInterval(cargarGrupos, 10000);
		return () => clearInterval(intervalo);
	}, [usuario]);

	// No leídos: carga inicial + reconciliación lenta.
	// Las actualizaciones normales llegan por WebSocket para evitar
	// consultar al backend cada 3 segundos.
	useEffect(() => {
		if (!usuario) {
			setNoLeidos({ total: 0, porContacto: {} });
			return;
		}

		let cancelado = false;

		async function actualizar() {
			const data = await obtenerNoLeidos(usuario.id);
			if (cancelado) return;

			setNoLeidos({
				total: data.no_leidos || 0,
				porContacto: data.por_contacto || {},
			});
		}

		actualizar();
		const intervalo = setInterval(actualizar, 60000);

		return () => {
			cancelado = true;
			clearInterval(intervalo);
		};
	}, [usuario]);

	// WebSocket único por sesión.
	// Evita abrir/cerrar conexiones al cambiar de contacto y permite
	// actualizar badges de no leídos con eventos push del worker.
	useEffect(() => {
		if (!usuario) return;

		const cerrarWS = crearWebSocket(
			usuario.id,
			(datos) => {
				if (datos.tipo === "mensaje_sin_memoria") {
					setMensajeSinMemoriaEntrante(datos);
					return;
				}
				if (datos.tipo !== "nuevo_mensaje") return;

				const emisorId = datos.emisor_id;
				const delta = datos.no_leidos_delta || 1;
				const contactoActivoActual = contactoActivoRef.current;

				if (contactoActivoActual?.id === emisorId) {
					setActualizacionMensajes((prev) => prev + 1);
					marcarComoLeidos(usuario.id, emisorId).catch((error) => {
						console.warn("Error al marcar mensaje activo como leído:", error);
					});
					return;
				}

				setNoLeidos((prev) => {
					const actualContacto = prev.porContacto[emisorId] || 0;
					return {
						total: prev.total + delta,
						porContacto: {
							...prev.porContacto,
							[emisorId]: actualContacto + delta,
						},
					};
				});
			},
			() => {},
		);

		return () => cerrarWS();
	}, [usuario]);

	// Al seleccionar un contacto, marcarlo como leído.
	// Esto borra el badge específico de ese contacto.
	async function handleSeleccionarContacto(contacto) {
		setContactoActivo(contacto);
		if (usuario && contacto) {
			await marcarComoLeidos(usuario.id, contacto.id);
			// Refrescar inmediatamente para que el badge desaparezca
			const data = await obtenerNoLeidos(usuario.id);
			setNoLeidos({
				total: data.no_leidos || 0,
				porContacto: data.por_contacto || {},
			});
		}
	}

	function handleSeleccionarGrupo(grupo) {
		setContactoActivo({ ...grupo, tipo: "grupo" });
	}

	function handleLogout() {
		setToken(null);
		setUsuario(null);
		setContactos([]);
		setContactoActivo(null);
		setIaId(null);
		setNoLeidos({ total: 0, porContacto: {} });
		setActualizacionMensajes(0);
		setGrupos([]);
		huellaContactosRef.current = "";
	}

	if (cargandoSesion) {
		return (
			<div className="flex items-center justify-center h-screen bg-vibe-950">
				<div className="flex flex-col items-center gap-3">
					<div
						className="w-12 h-12 rounded-xl bg-gradient-vibe flex items-center
                          justify-center shadow-glow-cyan animate-pulse"
					>
						<MessageCircle size={24} className="text-white" />
					</div>
					<div className="text-vibe-400 text-sm">Cargando Vibe...</div>
				</div>
			</div>
		);
	}

	if (!usuario) {
		return <Registro onRegistro={setUsuario} />;
	}

	return (
		<div className="flex h-screen bg-vibe-950 overflow-hidden">
			<Sidebar
				usuario={usuario}
				contactos={contactos}
				iaId={iaId}
				onSeleccionar={handleSeleccionarContacto}
				onLogout={handleLogout}
			/>

			<ListaContactos
				contactos={contactos}
				grupos={grupos}
				contactoActivo={contactoActivo}
				onSeleccionar={handleSeleccionarContacto}
				onSeleccionarGrupo={handleSeleccionarGrupo}
				usuarioActual={usuario}
				iaId={iaId}
				presencias={presencias}
				noLeidos={noLeidos}
			/>

			{contactoActivo ? (
				<Chat
					usuarioActual={usuario}
					contacto={contactoActivo}
					iaId={iaId}
					presencias={presencias}
					actualizacionMensajes={actualizacionMensajes}
				mensajeSinMemoriaEntrante={mensajeSinMemoriaEntrante}
				onConsumirSinMemoria={() => setMensajeSinMemoriaEntrante(null)}
				/>
			) : (
				<div className="flex-1 flex flex-col items-center justify-center bg-vibe-950">
					<div
						className="w-20 h-20 rounded-2xl bg-vibe-900 flex items-center
                          justify-center mb-4 border border-vibe-800"
					>
						<MessageCircle size={36} className="text-vibe-600" />
					</div>
					<p className="text-vibe-400 text-sm">
						Selecciona un contacto para comenzar a chatear
					</p>
					<p className="text-vibe-600 text-xs mt-1">
						Vibe — conexiones reales, privacidad real
					</p>
				</div>
			)}
		</div>
	);
}
