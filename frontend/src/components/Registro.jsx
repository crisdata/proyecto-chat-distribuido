// Registro.jsx
// Pantalla inicial de bienvenida a Vibe.
// Login demo por correo: si el correo no existe, pide nombre visible.

import { useState } from "react";
import { Mail, MessageCircle, Sparkles, UserRound } from "lucide-react";
import { loginUsuario } from "../services/api";

export default function Registro({ onRegistro }) {
	const [paso, setPaso] = useState("email");
	const [email, setEmail] = useState("");
	const [nombre, setNombre] = useState("");
	const [cargando, setCargando] = useState(false);
	const [error, setError] = useState("");

	const emailLimpio = email.trim().toLowerCase();
	const nombreLimpio = nombre.trim();

	async function enviarEmail() {
		if (!emailLimpio || !emailLimpio.includes("@")) {
			setError("Ingresa un correo válido para continuar.");
			return;
		}

		setCargando(true);
		setError("");

		try {
			const respuesta = await loginUsuario(emailLimpio);
			if (respuesta.token) {
				onRegistro(respuesta);
				return;
			}
			if (respuesta.requiere_nombre) {
				setPaso("nombre");
				return;
			}
			setError("No se pudo iniciar sesión. Intenta de nuevo.");
		} catch (err) {
			setError(err.message);
		} finally {
			setCargando(false);
		}
	}

	async function enviarNombre() {
		if (nombreLimpio.length < 2) {
			setError("El nombre debe tener al menos 2 caracteres.");
			return;
		}

		setCargando(true);
		setError("");

		try {
			const usuario = await loginUsuario(emailLimpio, nombreLimpio);
			onRegistro(usuario);
		} catch (err) {
			setError(err.message);
		} finally {
			setCargando(false);
		}
	}

	function handleSubmit() {
		if (paso === "email") enviarEmail();
		else enviarNombre();
	}

	function handleKeyDown(e) {
		if (e.key === "Enter") handleSubmit();
	}

	return (
		<div className="flex items-center justify-center h-screen bg-vibe-950 px-4">
			<div
				className="bg-vibe-900 rounded-3xl shadow-panel p-10 w-full max-w-sm
                      flex flex-col gap-5 border border-vibe-800"
			>
				{/* Logo e identidad */}
				<div className="flex flex-col items-center gap-3 mb-2">
					<div
						className="w-16 h-16 rounded-2xl bg-gradient-vibe flex items-center
                          justify-center shadow-glow-cyan"
					>
						<MessageCircle size={32} className="text-white" />
					</div>
					<h1 className="text-3xl font-bold text-vibe-100 tracking-tight">
						Vibe
					</h1>
					<p className="text-sm text-vibe-400 text-center leading-relaxed">
						Conecta con personas reales.
						<br />
						Tu privacidad, primero.
					</p>
				</div>

				{paso === "email" ? (
					<>
						<label className="flex flex-col gap-2">
							<span className="text-xs font-medium text-vibe-400">
								Correo de acceso
							</span>
							<div
								className="flex items-center gap-2 px-4 py-3.5 rounded-xl
                              border border-vibe-700 bg-vibe-800
                              focus-within:ring-2 focus-within:ring-cyan-500
                              focus-within:border-transparent transition"
							>
								<Mail size={17} className="text-vibe-500" />
								<input
									type="email"
									placeholder="tu-correo@ejemplo.com"
									value={email}
									onChange={(e) => setEmail(e.target.value)}
									onKeyDown={handleKeyDown}
									disabled={cargando}
									className="flex-1 bg-transparent text-vibe-100 placeholder-vibe-500
                             focus:outline-none disabled:opacity-50"
								/>
							</div>
						</label>
						<p className="text-xs text-vibe-500 text-center leading-relaxed">
							Demo académico sin verificación de correo. Vibe no muestra tu
							correo a otros usuarios.
						</p>
					</>
				) : (
					<>
						<div
							className="rounded-xl border border-cyan-500/30 bg-cyan-500/10
                            px-4 py-3 text-xs text-cyan-100 leading-relaxed"
						>
							No encontramos ese correo. Elegí un nombre visible para completar
							tu primer ingreso.
						</div>
						<label className="flex flex-col gap-2">
							<span className="text-xs font-medium text-vibe-400">
								Nombre visible
							</span>
							<div
								className="flex items-center gap-2 px-4 py-3.5 rounded-xl
                              border border-vibe-700 bg-vibe-800
                              focus-within:ring-2 focus-within:ring-cyan-500
                              focus-within:border-transparent transition"
							>
								<UserRound size={17} className="text-vibe-500" />
								<input
									type="text"
									placeholder="Nombre y apellido recomendado"
									value={nombre}
									onChange={(e) => setNombre(e.target.value)}
									onKeyDown={handleKeyDown}
									maxLength={100}
									disabled={cargando}
									className="flex-1 bg-transparent text-vibe-100 placeholder-vibe-500
                             focus:outline-none disabled:opacity-50"
								/>
							</div>
						</label>
					</>
				)}

				{/* Mensaje de error */}
				{error && (
					<p className="text-red-400 text-sm text-center -mt-2">{error}</p>
				)}

				{/* Botón de acceso */}
				<button
					onClick={handleSubmit}
					disabled={
						cargando ||
						(paso === "email" && !emailLimpio) ||
						(paso === "nombre" && nombreLimpio.length < 2)
					}
					className="w-full py-3.5 rounded-xl bg-gradient-vibe
                     text-white font-semibold transition shadow-glow-cyan
                     hover:opacity-90 active:scale-[0.98]
                     disabled:opacity-50 disabled:cursor-not-allowed
                     disabled:shadow-none"
				>
					{cargando
						? "Entrando..."
						: paso === "email"
							? "Continuar"
							: "Crear sesión"}
				</button>

				{paso === "nombre" && (
					<button
						onClick={() => {
							setPaso("email");
							setError("");
						}}
						disabled={cargando}
						className="text-xs text-vibe-500 hover:text-cyan-400 transition"
					>
						Usar otro correo
					</button>
				)}

				{/* Lumi como teaser */}
				<div
					className="flex items-center justify-center gap-2 text-xs
                        text-vibe-500 -mt-1"
				>
					<Sparkles size={12} className="text-lumi-400" />
					<span>Conoce a Lumi, tu compañera virtual</span>
				</div>

				{/* Footer */}
				<p className="text-xs text-vibe-600 text-center mt-2">
					Proyecto académico — COTECNOVA
				</p>
			</div>
		</div>
	);
}
