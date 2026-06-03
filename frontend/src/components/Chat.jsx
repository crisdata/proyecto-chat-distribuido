// Chat.jsx
// Panel derecho con la conversación. Avatar del contacto con gradiente único.
// Header muestra estado de presencia real (En línea / Activo hace X / Reposando).

import { useState, useEffect, useRef, useCallback } from "react";
import {
	Send,
	Bot,
	User,
	Loader,
	Shield,
	Flame,
	Users,
	Eye,
	EyeOff,
} from "lucide-react";
import Mensaje from "./Mensaje";
import {
	enviarMensaje,
	enviarMensajeIA,
	obtenerConversacionBilateral,
	mensajesGrupo,
	enviarMensajeGrupo,
} from "../services/api";
import { esHoy } from "../utils/tiempo";
import { getAvatarStyle } from "../utils/avatarColors";
import { formatearTiempoRelativo } from "../utils/tiempo";
import IndicadorPresencia from "./IndicadorPresencia";

export default function Chat({
	usuarioActual,
	contacto,
	iaId,
	presencias = {},
	actualizacionMensajes = 0,
}) {
	const [mensajes, setMensajes] = useState([]);
	const [texto, setTexto] = useState("");
	const [enviando, setEnviando] = useState(false);
	const [cargando, setCargando] = useState(true);
	const [modoAutodestructivo, setModoAutodestructivo] = useState(false);
	const [modo, setModo] = useState("con_memoria");
	const esSinMemoria = modo === "sin_memoria";
	const finalRef = useRef(null);
	const esIA = contacto.id === iaId;
	const esGrupo = contacto.tipo === "grupo";

	// Presencia del contacto que estoy viendo
	const presencia = presencias[contacto.id];
	const estado = presencia?.estado || "offline";
	const ultimaActividad = presencia?.ultima_actividad;

	const cargarConversacion = useCallback(async () => {
		try {
			let data;
			if (esGrupo) {
				data = await mensajesGrupo(contacto.id);
			} else {
				data = await obtenerConversacionBilateral(
					usuarioActual.id,
					contacto.id,
				);
			}
			setMensajes(data);
		} catch (error) {
			console.error("Error al cargar mensajes:", error);
		}
	}, [usuarioActual.id, contacto.id]);

	useEffect(() => {
		setCargando(true);
		setMensajes([]);
		cargarConversacion().finally(() => setCargando(false));
	}, [contacto.id, cargarConversacion]);

	useEffect(() => {
		if (actualizacionMensajes === 0) return;
		cargarConversacion();
	}, [actualizacionMensajes, cargarConversacion]);

	useEffect(() => {
		finalRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [mensajes]);

	async function handleEnviar() {
		const contenido = texto.trim();
		if (!contenido || enviando) return;

		setEnviando(true);
		setTexto("");

		try {
			if (esGrupo) {
				await enviarMensajeGrupo(contacto.id, contenido);
			} else if (esIA) {
				await enviarMensajeIA(usuarioActual.id, iaId, contenido, modo);
			} else {
				const expiraEn = modoAutodestructivo ? 30 : null;
				await enviarMensaje(usuarioActual.id, contacto.id, contenido, expiraEn);
			}
			await cargarConversacion();
		} catch (error) {
			console.error("Error al enviar mensaje:", error);
			setTexto(contenido);
		} finally {
			setEnviando(false);
		}
	}

	function handleKeyDown(e) {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			handleEnviar();
		}
	}

	function renderMensajes() {
		let fechaAnterior = null;
		return mensajes.map((mensaje, index) => {
			const fechaActual = new Date(mensaje.timestamp).toDateString();
			const mostrarFecha = fechaActual !== fechaAnterior;
			fechaAnterior = fechaActual;

			return (
				<div key={mensaje.id || index}>
					{mostrarFecha && (
						<div className="flex items-center justify-center my-4">
							<span
								className="px-3 py-1 bg-vibe-800 text-vibe-500
                               text-xs rounded-full border border-vibe-700"
							>
								{esHoy(mensaje.timestamp) ? "Hoy" : fechaActual}
							</span>
						</div>
					)}
					<Mensaje
						mensaje={mensaje}
						usuarioActual={usuarioActual}
						iaId={iaId}
						nombreEmisor={
							mensaje.emisor_id === contacto.id ? contacto.nombre : null
						}
					/>
				</div>
			);
		});
	}

	// Texto descriptivo del estado del contacto en el header
	function getTextoEstado() {
		if (esGrupo) return "Grupo público";
		if (esSinMemoria) return "Sin memoria · No se guarda historial";
		if (esIA) {
			if (estado === "online")
				return `Modelo: ${import.meta.env.VITE_OLLAMA_MODEL || "llama3.2:3b"}`;
			if (estado === "reposando") return "Reposando — vuelve en un momento";
			return "No disponible";
		}

		if (estado === "online") return "En línea";
		if (estado === "offline") {
			const relativo = formatearTiempoRelativo(ultimaActividad);
			return relativo ? `Activo ${relativo}` : "Desconectado";
		}
		return "";
	}

	// Color del texto según el estado
	function getColorEstado() {
		if (esGrupo) return "text-cyan-400";
		if (esSinMemoria) return "text-amber-400";
		if (estado === "online") return esIA ? "text-lumi-400" : "text-online-400";
		if (estado === "reposando") return "text-amber-400";
		return "text-vibe-500";
	}

	return (
		<div className="flex-1 flex flex-col bg-vibe-950">
			{/* Encabezado de la conversación */}
			<div
				className="bg-vibe-950 border-b border-vibe-800 px-6 py-4
					flex items-center gap-3"
			>
				{/* Avatar o ícono de grupo */}
				{esGrupo ? (
					<div className="w-10 h-10 rounded-full bg-cyan-500/15 flex items-center justify-center flex-shrink-0">
						<Users size={20} className="text-cyan-400" />
					</div>
				) : (
					<div className="relative flex-shrink-0">
						<div
							style={getAvatarStyle(contacto.nombre, esIA)}
							className={`w-10 h-10 rounded-full flex items-center justify-center
						font-semibold
						${esIA ? "text-white" : ""}`}
						>
							{esIA ? (
								<Bot size={20} />
							) : (
								contacto.nombre.charAt(0).toUpperCase()
							)}
						</div>
						<IndicadorPresencia estado={estado} tamano="sm" />
					</div>
				)}

				<div className="flex-1">
					<h3 className="font-semibold text-vibe-100 text-sm">
						{contacto.nombre}
					</h3>
					<p className={`text-xs flex items-center gap-1 ${getColorEstado()}`}>
						{estado === "online" && !esIA && (
							<span className="w-1.5 h-1.5 rounded-full bg-online-400 inline-block" />
						)}
						{estado === "online" && esIA && (
							<span className="w-1.5 h-1.5 rounded-full bg-lumi-400 inline-block" />
						)}
						{estado === "reposando" && (
							<span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
						)}
						{getTextoEstado()}
					</p>
				</div>
				{!esGrupo && (
					<button
						title={esSinMemoria ? "Modo sin memoria" : "Modo con memoria"}
						onClick={() =>
							setModo(esSinMemoria ? "con_memoria" : "sin_memoria")
						}
						className={`w-8 h-8 rounded-lg flex items-center justify-center transition ${
							esSinMemoria
								? "bg-amber-500/15 text-amber-400"
								: "bg-vibe-800 text-vibe-500 hover:text-cyan-400"
						}`}
					>
						{esSinMemoria ? <EyeOff size={15} /> : <Eye size={15} />}
					</button>
				)}
				<Shield size={18} className="text-cyan-500" />
			</div>

			{/* Área de mensajes */}
			<div className="flex-1 overflow-y-auto px-6 py-4">
				{cargando ? (
					<div
						className="flex items-center justify-center h-full gap-2
                          text-vibe-500 text-sm"
					>
						<Loader size={18} className="animate-spin" />
						<span>Cargando conversación...</span>
					</div>
				) : mensajes.length === 0 ? (
					<div
						className="flex flex-col items-center justify-center
                          h-full gap-3 text-vibe-500"
					>
						<div
							className={`w-16 h-16 rounded-full flex items-center
								justify-center
								${
									esGrupo
										? "bg-cyan-500/15"
										: esIA
											? "bg-lumi-400/15"
											: "bg-cyan-500/15"
								}`}
						>
							{esGrupo ? (
								<Users size={32} className="text-cyan-400" />
							) : esIA ? (
								<Bot size={32} className="text-lumi-400" />
							) : (
								<User size={32} className="text-cyan-400" />
							)}
						</div>
						<p className="text-sm font-medium text-vibe-300">
							{esGrupo
								? `Bienvenido a ${contacto.nombre}`
								: esIA
									? "¡Hola! Soy Lumi, tu compañera virtual. ¿En qué puedo acompañarte?"
									: `Inicia una conversación con ${contacto.nombre}`}
						</p>
					</div>
				) : (
					renderMensajes()
				)}

				{enviando && esIA && (
					<div className="flex items-center gap-2 mt-2 text-vibe-500 text-xs">
						<Loader size={14} className="animate-spin text-lumi-400" />
						<span>Lumi está pensando...</span>
					</div>
				)}
				<div ref={finalRef} />
			</div>

			{/* Input de mensaje */}
			<div
				className="bg-vibe-950 border-t border-vibe-800 px-4 py-3
                      flex items-end gap-3"
			>
				<button
					title={
						modoAutodestructivo
							? "Desactivar mensaje autodestructivo"
							: "Mensaje autodestructivo (30s)"
					}
					onClick={() => setModoAutodestructivo((prev) => !prev)}
					className={`w-10 h-10 rounded-xl flex items-center justify-center
                     transition ${
												modoAutodestructivo
													? "bg-red-500/20 text-red-400 shadow-glow-red"
													: "bg-vibe-800 text-vibe-600 hover:bg-vibe-700 hover:text-cyan-400"
}`}
				>
					<Flame size={18} />
				</button>

				<textarea
					value={texto}
					onChange={(e) => setTexto(e.target.value)}
					onKeyDown={handleKeyDown}
					placeholder={
						modoAutodestructivo
							? "Mensaje autodestructivo (30s)..."
							: "Escribe un mensaje..."
					}
					rows={1}
					disabled={enviando}
					className={`flex-1 px-4 py-2.5 rounded-2xl
                     border text-sm outline-none resize-none
                     transition
                     disabled:opacity-50 max-h-32 overflow-y-auto
                     ${
												modoAutodestructivo
													? "bg-red-500/5 border-red-500/40 text-red-100 placeholder-red-400/50 focus:ring-2 focus:ring-red-500"
													: "bg-vibe-800 border-vibe-700 text-vibe-100 placeholder-vibe-500 focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
}`}
				/>
				<button
					onClick={handleEnviar}
					disabled={!texto.trim() || enviando}
					className="w-10 h-10 rounded-full bg-gradient-vibe
                     text-white flex items-center justify-center
                     transition flex-shrink-0 shadow-glow-cyan
                     hover:opacity-90 active:scale-95
                     disabled:opacity-40 disabled:cursor-not-allowed
                     disabled:shadow-none"
				>
					{enviando ? (
						<Loader size={18} className="animate-spin" />
					) : (
						<Send size={18} />
					)}
				</button>
			</div>
		</div>
	);
}
