// Mensaje.jsx
// Burbuja individual de mensaje. Avatar del emisor con gradiente único.
// Si el mensaje tiene expira_en, muestra un contador regresivo y se
// auto-elimina visualmente al expirar.

import { useState, useEffect } from "react";
import { Bot, Timer } from "lucide-react";
import { formatearHora } from "../utils/tiempo";
import { getAvatarStyle } from "../utils/avatarColors";

export default function Mensaje({
	mensaje,
	usuarioActual,
	iaId,
	nombreEmisor,
}) {
	const esEnviado = mensaje.emisor_id === usuarioActual.id;
	const esIA = mensaje.emisor_id === iaId;
	const esAutodestructivo = !!mensaje.expira_en;

	// Contador regresivo para mensajes autodestructivos
	const [segundosRestantes, setSegundosRestantes] = useState(() => {
		if (!mensaje.expira_en) return null;
		const expira = new Date(mensaje.expira_en + "Z").getTime();
		const ahora = Date.now();
		return Math.max(0, Math.floor((expira - ahora) / 1000));
	});

	const [visible, setVisible] = useState(true);

	useEffect(() => {
		if (!esAutodestructivo || segundosRestantes === null) return;

		if (segundosRestantes <= 0) {
			setVisible(false);
			return;
		}

		const intervalo = setInterval(() => {
			setSegundosRestantes((prev) => {
				if (prev === null || prev <= 1) {
					clearInterval(intervalo);
					setTimeout(() => setVisible(false), 400);
					return 0;
				}
				return prev - 1;
			});
		}, 1000);

		return () => clearInterval(intervalo);
	}, [esAutodestructivo]);

	if (!visible) return null;

	return (
		<div
			className={`flex items-end gap-2 mb-2 animate-fade-in-up
                     ${esEnviado ? "flex-row-reverse" : "flex-row"}`}
		>
			{/* Avatar del remitente con gradiente único */}
			{!esEnviado && (
				<div
					style={getAvatarStyle(nombreEmisor, esIA)}
					className={`w-7 h-7 rounded-full flex items-center justify-center
                      flex-shrink-0 text-xs font-semibold mb-1
                      ${esIA ? "text-white" : ""}`}
				>
					{esIA ? (
						<Bot size={14} />
					) : (
						nombreEmisor?.charAt(0).toUpperCase() || "?"
					)}
				</div>
			)}

			{/* Burbuja del mensaje */}
			<div>
				{!esEnviado && nombreEmisor && !esIA && (
					<p className="text-[11px] text-vibe-400 mb-1 px-2 font-medium">
						{nombreEmisor}
					</p>
				)}
				<div
					className={`max-w-xs lg:max-w-md px-4 py-2.5 rounded-2xl
                       shadow-bubble text-sm leading-relaxed
                       ${esAutodestructivo ? "border-2 border-red-500/50" : ""}
                       ${
													esEnviado
														? "bg-gradient-vibe text-white rounded-br-sm"
														: "bg-vibe-700 text-vibe-100 rounded-bl-sm"
}${esIA && !esEnviado ? " border-l-2 border-lumi-400" : ""}`}
			>
					<p className="whitespace-pre-wrap break-words">{mensaje.contenido}</p>

					<p
						className={`text-xs mt-1 flex items-center justify-end gap-1
                       ${esEnviado ? "text-white/60" : "text-vibe-500"}`}
					>
						{segundosRestantes !== null && (
							<span className="flex items-center gap-0.5 text-red-400">
								<Timer size={10} />
								{segundosRestantes}s
							</span>
						)}
						{formatearHora(mensaje.timestamp)}
					</p>
				</div>
			</div>
		</div>
	);
}
