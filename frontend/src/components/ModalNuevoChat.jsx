// ModalNuevoChat.jsx
// Modal con pestañas: Personas, Grupos, Crear grupo.

import { useState, useEffect, useMemo } from "react";
import {
	Search,
	X,
	User,
	Bot,
	Users,
	PlusCircle,
	Eye,
	EyeOff,
} from "lucide-react";
import {
	listarUsuarios,
	buscarGrupos,
	crearGrupo,
	unirseAGrupo,
} from "../services/api";
import { getAvatarStyle } from "../utils/avatarColors";

function TabButton({ tab, actual, onClick, icon: Icon, children }) {
	const activo = tab === actual;
	return (
		<button
			onClick={() => onClick(tab)}
			className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs
				font-medium rounded-lg transition
				${
					activo
						? "bg-cyan-500/20 text-cyan-300"
						: "text-vibe-500 hover:text-vibe-300"
				}`}
		>
			<Icon size={14} />
			{children}
		</button>
	);
}

export default function ModalNuevoChat({
	usuarioActual,
	iaId,
	onSeleccionar,
	onSeleccionarGrupo,
	onCerrar,
}) {
	const [tab, setTab] = useState("personas");
	const [busqueda, setBusqueda] = useState("");
	const [todosUsuarios, setTodosUsuarios] = useState([]);
	const [gruposBusqueda, setGruposBusqueda] = useState([]);
	const [cargandoGrupos, setCargandoGrupos] = useState(false);
	const [nombreGrupo, setNombreGrupo] = useState("");
	const [creando, setCreando] = useState(false);
	const [modoChat, setModoChat] = useState("con_memoria");
	const [error, setError] = useState("");

	// Cargar usuarios para pestaña Personas
	useEffect(() => {
		async function cargar() {
			try {
				const usuarios = await listarUsuarios();
				setTodosUsuarios(usuarios);
			} catch (e) {
				console.error("Error al cargar usuarios:", e);
			}
		}
		cargar();
	}, []);

	// Buscar grupos (debounced por 300ms desde el input)
	useEffect(() => {
		if (tab !== "grupos") return;
		const q = busqueda.trim();
		if (!q) {
			setGruposBusqueda([]);
			return;
		}

		let activo = true;
		const timer = setTimeout(async () => {
			try {
				setCargandoGrupos(true);
				const data = await buscarGrupos(q);
				if (activo) setGruposBusqueda(data);
			} catch (e) {
				console.error("Error al buscar grupos:", e);
			} finally {
				if (activo) setCargandoGrupos(false);
			}
		}, 300);

		return () => {
			activo = false;
			clearTimeout(timer);
		};
	}, [busqueda, tab]);

	function cambiarTab(t) {
		setTab(t);
		setBusqueda("");
		setError("");
	}

	// Usuarios disponibles (todos menos el actual)
	const usuariosDisponibles = useMemo(() => {
		const termino = busqueda.toLowerCase().trim();
		return todosUsuarios.filter((u) => {
			if (u.id === usuarioActual.id) return false;
			if (termino && !u.nombre.toLowerCase().includes(termino)) return false;
			return true;
		});
	}, [todosUsuarios, usuarioActual.id, busqueda]);

	async function handleUnirseOSeleccionar(grupo) {
		if (!grupo.es_miembro) {
			await unirseAGrupo(grupo.id);
		}
		onSeleccionarGrupo?.(grupo);
		onCerrar();
	}

	async function handleCrearGrupo() {
		const nombre = nombreGrupo.trim();
		if (nombre.length < 2) {
			setError("El nombre debe tener al menos 2 caracteres.");
			return;
		}
		setCreando(true);
		setError("");
		try {
			const grupo = await crearGrupo(nombre);
			onSeleccionarGrupo?.(grupo);
			onCerrar();
		} catch (e) {
			setError(e.message);
		} finally {
			setCreando(false);
		}
	}

	function handleKeyCrear(e) {
		if (e.key === "Enter") handleCrearGrupo();
	}

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
							text-vibe-500 hover:text-vibe-200 hover:bg-vibe-800 transition"
					>
						<X size={18} />
					</button>
				</div>

				{/* Tabs */}
				<div className="flex gap-1 px-3 pt-3 pb-1">
					<TabButton
						tab="personas"
						actual={tab}
						onClick={cambiarTab}
						icon={User}
					>
						Personas
					</TabButton>
					<TabButton
						tab="grupos"
						actual={tab}
						onClick={cambiarTab}
						icon={Users}
					>
						Grupos
					</TabButton>
					<TabButton
						tab="crear"
						actual={tab}
						onClick={cambiarTab}
						icon={PlusCircle}
					>
						Crear
					</TabButton>
				</div>

				{/* Búsqueda (personas / grupos) */}
				{tab !== "crear" && (
					<div className="px-5 pt-2 pb-2 space-y-3">
						<div
							className="flex items-center gap-2 bg-vibe-800 rounded-xl
							px-3 py-2.5 border border-vibe-700
							focus-within:border-cyan-500 transition"
						>
							<Search size={15} className="text-vibe-500 flex-shrink-0" />
							<input
								type="text"
								placeholder={
									tab === "personas" ? "Buscar usuario..." : "Buscar grupo..."
								}
								value={busqueda}
								onChange={(e) => setBusqueda(e.target.value)}
								autoFocus
								className="flex-1 bg-transparent text-sm text-vibe-200
									placeholder-vibe-500 outline-none"
							/>
						</div>
						{tab === "personas" && renderSelectorModo()}
						{tab === "grupos" && (
							<p className="text-[11px] text-vibe-500 leading-relaxed">
								Los grupos son públicos y abiertos: cualquiera que los encuentre
								puede unirse.
							</p>
						)}
					</div>
				)}

				{/* Contenido según tab */}
				<div className="max-h-72 overflow-y-auto px-2 py-2">
					{tab === "personas" && renderPersonas()}
					{tab === "grupos" && renderGrupos()}
					{tab === "crear" && renderCrear()}
				</div>
			</div>
		</div>
	);

	function renderSelectorModo() {
		return (
			<div className="rounded-xl border border-vibe-700 bg-vibe-800/60 p-2 space-y-2">
				<div className="grid grid-cols-2 gap-2">
					<button
						type="button"
						onClick={() => setModoChat("con_memoria")}
						className={`flex items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-medium transition ${
							modoChat === "con_memoria"
								? "bg-cyan-500/20 text-cyan-300"
								: "text-vibe-500 hover:text-vibe-300"
						}`}
					>
						<Eye size={13} />
						Con memoria
					</button>
					<button
						type="button"
						onClick={() => setModoChat("sin_memoria")}
						className={`flex items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-medium transition ${
							modoChat === "sin_memoria"
								? "bg-amber-500/20 text-amber-300"
								: "text-vibe-500 hover:text-vibe-300"
						}`}
					>
						<EyeOff size={13} />
						Sin memoria
					</button>
				</div>
				<p className="text-[11px] text-vibe-500 leading-relaxed">
					Sin memoria: no se guarda historial en Vibe. Con memoria: el chat
					queda disponible para volver a consultarlo.
				</p>
			</div>
		);
	}

	function renderPersonas() {
		if (usuariosDisponibles.length === 0) {
			return (
				<div className="flex flex-col items-center justify-center py-8 gap-2">
					<User size={28} className="text-vibe-600" />
					<p className="text-vibe-500 text-sm">
						{busqueda
							? "No se encontraron usuarios"
							: "No hay usuarios nuevos disponibles"}
					</p>
				</div>
			);
		}
		return usuariosDisponibles.map((usuario) => {
			const esIA = usuario.id === iaId;
			return (
				<button
					key={usuario.id}
					onClick={() => {
						onSeleccionar({ ...usuario, modoInicial: modoChat });
						onCerrar();
					}}
					className="w-full flex items-center gap-3 px-3 py-2.5
						rounded-xl hover:bg-vibe-800 transition text-left"
				>
					<div
						style={getAvatarStyle(usuario.nombre, esIA)}
						className={`w-9 h-9 rounded-full flex items-center justify-center
							font-semibold text-sm ${esIA ? "text-white" : ""}`}
					>
						{esIA ? <Bot size={16} /> : usuario.nombre.charAt(0).toUpperCase()}
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
		});
	}

	function renderGrupos() {
		if (cargandoGrupos) {
			return (
				<p className="py-6 text-center text-sm text-vibe-500">
					Buscando grupos...
				</p>
			);
		}
		if (busqueda.trim() && gruposBusqueda.length === 0) {
			return (
				<p className="py-6 text-center text-sm text-vibe-500">
					No se encontraron grupos
				</p>
			);
		}
		return gruposBusqueda.map((grupo) => (
			<button
				key={grupo.id}
				onClick={() => handleUnirseOSeleccionar(grupo)}
				className="w-full flex items-center gap-3 px-3 py-2.5
					rounded-xl hover:bg-vibe-800 transition text-left"
			>
				<div className="w-9 h-9 rounded-full bg-cyan-500/15 flex items-center justify-center">
					<Users size={16} className="text-cyan-400" />
				</div>
				<div className="flex-1 min-w-0">
					<p className="text-sm font-medium text-vibe-200 truncate">
						{grupo.nombre}
					</p>
					<p className="text-xs text-vibe-500">
						{grupo.es_miembro ? "Ya eres miembro" : "Toca para unirte"}
					</p>
				</div>
				<span className="text-[10px] text-vibe-500 bg-vibe-800 px-2 py-0.5 rounded-full">
					Grupo público
				</span>
			</button>
		));
	}

	function renderCrear() {
		return (
			<div className="flex flex-col gap-3 px-3 py-2">
				<p className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-3 py-2 text-[11px] text-cyan-100 leading-relaxed">
					Grupo público: cualquier usuario que lo encuentre puede unirse. Los
					mensajes quedan guardados en el grupo.
				</p>
				<label className="flex flex-col gap-2">
					<span className="text-xs font-medium text-vibe-400">
						Nombre del grupo
					</span>
					<input
						type="text"
						placeholder="Ej: Programación"
						value={nombreGrupo}
						onChange={(e) => setNombreGrupo(e.target.value)}
						onKeyDown={handleKeyCrear}
						maxLength={100}
						disabled={creando}
						autoFocus
						className="w-full px-4 py-3 rounded-xl border border-vibe-700 bg-vibe-800
							text-vibe-100 placeholder-vibe-500 text-sm
							focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent
							disabled:opacity-50"
					/>
				</label>
				{error && <p className="text-red-400 text-xs">{error}</p>}
				<button
					onClick={handleCrearGrupo}
					disabled={creando || nombreGrupo.trim().length < 2}
					className="w-full py-3 rounded-xl bg-gradient-vibe text-white font-semibold
						transition hover:opacity-90 active:scale-[0.98]
						disabled:opacity-40 disabled:cursor-not-allowed text-sm"
				>
					{creando ? "Creando..." : "Crear grupo"}
				</button>
			</div>
		);
	}
}
