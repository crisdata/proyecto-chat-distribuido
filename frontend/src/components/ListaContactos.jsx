// ListaContactos.jsx
// Panel central con la lista de contactos.
// Lumi (la IA) aparece siempre al inicio, separada del resto.
// Cada contacto muestra su propio badge de mensajes no leídos
// estilo WhatsApp/Telegram.

import { useState, useMemo } from "react";
import { Search, Bot, User, PenSquare } from "lucide-react";
import { formatearHora } from "../utils/tiempo";
import { getAvatarStyle } from "../utils/avatarColors";
import IndicadorPresencia from "./IndicadorPresencia";
import ModalNuevoChat from "./ModalNuevoChat";

export default function ListaContactos({
	contactos,
	contactoActivo,
	onSeleccionar,
	usuarioActual,
	iaId,
	presencias = {},
	noLeidos = { total: 0, porContacto: {} },
}) {
	const [busqueda, setBusqueda] = useState("");
	const [mostrarModalNuevoChat, setMostrarModalNuevoChat] = useState(false);

	const { lumi, humanos } = useMemo(() => {
		const filtroBusqueda = (c) =>
			c.nombre.toLowerCase().includes(busqueda.toLowerCase());

		const lumi = contactos.find((c) => c.id === iaId);
		const humanos = contactos
			.filter((c) => c.id !== iaId)
			.filter(filtroBusqueda);

		return {
			lumi: lumi && filtroBusqueda(lumi) ? lumi : null,
			humanos,
		};
	}, [contactos, iaId, busqueda]);

	function renderContacto(contacto) {
		const esIA = contacto.id === iaId;
		const activo = contactoActivo?.id === contacto.id;
		const estado = presencias[contacto.id]?.estado || "offline";
		const cantidadNoLeidos = noLeidos.porContacto[contacto.id] || 0;

		return (
			<button
				key={contacto.id}
				onClick={() => onSeleccionar(contacto)}
				className={`w-full flex items-center gap-3 px-4 py-3
                    transition text-left border-b border-vibe-800/50
                    ${
											activo
												? esIA
													? "bg-lumi-400/10 border-l-4 border-l-lumi-400"
													: "bg-cyan-500/10 border-l-4 border-l-cyan-500"
												: "hover:bg-vibe-800/50"
										}`}
			>
				<div className="relative flex-shrink-0">
					<div
						style={getAvatarStyle(contacto.nombre, esIA)}
						className={`w-11 h-11 rounded-full flex items-center
                        justify-center font-semibold
                        ${esIA ? "text-white" : ""}`}
					>
						{esIA ? <Bot size={20} /> : contacto.nombre.charAt(0).toUpperCase()}
					</div>
					<IndicadorPresencia estado={estado} tamano="md" />
				</div>

				<div className="flex-1 min-w-0">
					<div className="flex items-center justify-between gap-2">
						<span
							className={`text-sm font-medium truncate
                              ${
																activo
																	? esIA
																		? "text-lumi-400"
																		: "text-cyan-400"
																	: cantidadNoLeidos > 0
																		? "text-vibe-100 font-semibold"
																		: "text-vibe-200"
															}`}
						>
							{contacto.nombre}
						</span>
						{contacto.creado_en && (
							<span
								className={`text-xs flex-shrink-0
                                ${
																	cantidadNoLeidos > 0
																		? "text-cyan-400 font-semibold"
																		: "text-vibe-600"
																}`}
							>
								{formatearHora(contacto.creado_en)}
							</span>
						)}
					</div>
					<div className="flex items-center justify-between gap-2 mt-0.5">
						<p className="text-xs text-vibe-500 truncate">
							{esIA ? "Tu compañera virtual" : "Usuario registrado"}
						</p>
						{/* Badge individual por contacto */}
						{cantidadNoLeidos > 0 && (
							<span
								className="flex-shrink-0 min-w-[20px] h-5 px-1.5
                               rounded-full bg-cyan-500
                               text-vibe-950 text-xs font-bold
                               flex items-center justify-center
                               shadow-glow-cyan"
							>
								{cantidadNoLeidos > 9 ? "9+" : cantidadNoLeidos}
							</span>
						)}
					</div>
				</div>
			</button>
		);
	}

	return (
		<div className="w-80 bg-vibe-900 border-r border-vibe-800 flex flex-col">
			<div className="px-5 pt-6 pb-4 border-b border-vibe-800">
				<div className="flex items-center justify-between mb-4">
					<h2 className="text-lg font-semibold text-vibe-100">Mensajes</h2>
					{noLeidos.total > 0 && (
						<span
							className="px-2 py-0.5 rounded-full bg-cyan-500
                             text-vibe-950 text-xs font-bold"
						>
							{noLeidos.total > 9 ? "9+" : noLeidos.total}
						</span>
					)}
				</div>

				<div
					className="flex items-center gap-2 bg-vibe-800 rounded-xl
                        px-3 py-2.5 border border-vibe-700
                        focus-within:border-cyan-500 transition"
				>
					<Search size={15} className="text-vibe-500 flex-shrink-0" />
					<input
						type="text"
						placeholder="Buscar conversaciones..."
						value={busqueda}
						onChange={(e) => setBusqueda(e.target.value)}
						className="flex-1 bg-transparent text-sm text-vibe-200
                       placeholder-vibe-500 outline-none"
					/>
				</div>
			</div>

			<div className="flex-1 overflow-y-auto py-2">
				{lumi && (
					<>
						{renderContacto(lumi)}
						<div className="my-2 mx-4 h-px bg-vibe-700/60" />
					</>
				)}

				{humanos.length === 0 && !lumi ? (
					<div
						className="flex flex-col items-center justify-center
                          h-40 text-vibe-500 text-sm gap-2"
					>
						<User size={32} className="opacity-30" />
						<p>No hay contactos disponibles</p>
					</div>
				) : (
					humanos.map(renderContacto)
				)}
			</div>

			<div className="p-4 border-t border-vibe-800">
				<button
					onClick={() => setMostrarModalNuevoChat(true)}
					className="w-full py-3 rounded-xl bg-gradient-vibe
                           text-white text-sm font-semibold transition
                           shadow-glow-cyan hover:opacity-90 active:scale-[0.98]
                           flex items-center justify-center gap-2"
				>
					<PenSquare size={16} />
					Nuevo chat
				</button>
			</div>

			{/* Modal para nuevo chat */}
			{mostrarModalNuevoChat && (
				<ModalNuevoChat
					usuarioActual={usuarioActual}
					iaId={iaId}
					contactosExistentes={contactos}
					onSeleccionar={onSeleccionar}
					onCerrar={() => setMostrarModalNuevoChat(false)}
				/>
			)}
		</div>
	);
}
