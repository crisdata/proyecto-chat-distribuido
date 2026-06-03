// ModalNuevoChat.jsx
// Modal para iniciar un nuevo chat con cualquier usuario registrado.
// Muestra usuarios que NO están ya en la lista de contactos visibles.

import { useState, useEffect, useMemo } from "react";
import { Search, X, User, Bot } from "lucide-react";
import { listarUsuarios } from "../services/api";
import { getAvatarStyle } from "../utils/avatarColors";

export default function ModalNuevoChat({
	usuarioActual,
	iaId,
	contactosExistentes,
	onSeleccionar,
	onCerrar,
}) {
	const [busqueda, setBusqueda] = useState("");
	const [todosUsuarios, setTodosUsuarios] = useState([]);

	useEffect(() => {
		async function cargar() {
			try {
				const usuarios = await listarUsuarios();
				setTodosUsuarios(usuarios);
			} catch (error) {
				console.error("Error al cargar usuarios:", error);
			}
		}
		cargar();
	}, []);

	// IDs de los contactos que ya están en la lista
	const idsExistentes = useMemo(
		() => new Set(contactosExistentes.map((c) => c.id)),
		[contactosExistentes],
	);

	// Usuarios que el usuario actual puede contactar (no él mismo, no contactos existentes)
	const usuariosDisponibles = useMemo(() => {
		const termino = busqueda.toLowerCase().trim();
		return todosUsuarios.filter((u) => {
			if (u.id === usuarioActual.id) return false;
			if (idsExistentes.has(u.id)) return false;
			if (termino && !u.nombre.toLowerCase().includes(termino)) return false;
			return true;
		});
	}, [todosUsuarios, usuarioActual.id, idsExistentes, busqueda]);

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
			<div
				className="bg-vibe-900 rounded-2xl w-full max-w-sm mx-4 shadow-2xl
                      border border-vibe-700 overflow-hidden"
			>
				{/* Header */}
				<div
					className="flex items-center justify-between px-5 py-4
                        border-b border-vibe-800"
				>
					<h3 className="text-lg font-semibold text-vibe-100">Nuevo chat</h3>
					<button
						onClick={onCerrar}
						className="w-8 h-8 rounded-lg flex items-center justify-center
                         text-vibe-500 hover:text-vibe-200 hover:bg-vibe-800
                         transition"
					>
						<X size={18} />
					</button>
				</div>

				{/* Búsqueda */}
				<div className="px-5 pt-3 pb-2">
					<div
						className="flex items-center gap-2 bg-vibe-800 rounded-xl
                            px-3 py-2.5 border border-vibe-700
                            focus-within:border-cyan-500 transition"
					>
						<Search size={15} className="text-vibe-500 flex-shrink-0" />
						<input
							type="text"
							placeholder="Buscar usuario..."
							value={busqueda}
							onChange={(e) => setBusqueda(e.target.value)}
							autoFocus
							className="flex-1 bg-transparent text-sm text-vibe-200
                           placeholder-vibe-500 outline-none"
						/>
					</div>
				</div>

				{/* Lista de usuarios */}
				<div className="max-h-72 overflow-y-auto px-2 py-2">
					{usuariosDisponibles.length === 0 ? (
						<div className="flex flex-col items-center justify-center py-8 gap-2">
							<User size={28} className="text-vibe-600" />
							<p className="text-vibe-500 text-sm">
								{busqueda
									? "No se encontraron usuarios"
									: "No hay usuarios nuevos disponibles"}
							</p>
						</div>
					) : (
						usuariosDisponibles.map((usuario) => {
							const esIA = usuario.id === iaId;
							return (
								<button
									key={usuario.id}
									onClick={() => {
										onSeleccionar(usuario);
										onCerrar();
									}}
									className="w-full flex items-center gap-3 px-3 py-2.5
                               rounded-xl hover:bg-vibe-800 transition text-left"
								>
									<div
										style={getAvatarStyle(usuario.nombre, esIA)}
										className={`w-9 h-9 rounded-full flex items-center
                                justify-center font-semibold text-sm
                                ${esIA ? "text-white" : ""}`}
									>
										{esIA ? (
											<Bot size={16} />
										) : (
											usuario.nombre.charAt(0).toUpperCase()
										)}
									</div>
									<div className="flex-1 min-w-0">
										<p className="text-sm font-medium text-vibe-200 truncate">
											{usuario.nombre}
										</p>
										<p className="text-xs text-vibe-500">
											{esIA ? "Compañera virtual" : "Usuario registrado"}
										</p>
									</div>
								</button>
							);
						})
					)}
				</div>
			</div>
		</div>
	);
}
