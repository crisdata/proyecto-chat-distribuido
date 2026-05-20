// App.jsx
// Componente raíz de la aplicación.
// Gestiona el estado global y aplica el contenedor con la paleta Vibe.

import { useState, useEffect } from 'react'
import { MessageCircle } from 'lucide-react'
import Registro from './components/Registro'
import Sidebar from './components/Sidebar'
import ListaContactos from './components/ListaContactos'
import Chat from './components/Chat'
import {
  listarUsuarios,
  obtenerIdIA,
  obtenerUsuarioActual,
  setToken
} from './services/api'

export default function App() {
  const [usuario, setUsuario] = useState(null)
  const [contactos, setContactos] = useState([])
  const [contactoActivo, setContactoActivo] = useState(null)
  const [iaId, setIaId] = useState(null)
  const [cargandoSesion, setCargandoSesion] = useState(true)

  // Al montar: intentar restaurar la sesión desde el token
  useEffect(() => {
    async function restaurarSesion() {
      const usuarioRecuperado = await obtenerUsuarioActual()
      if (usuarioRecuperado) {
        setUsuario(usuarioRecuperado)
      }
      setCargandoSesion(false)
    }
    restaurarSesion()
  }, [])

  // Al tener usuario, cargar contactos e ID del nodo IA
  useEffect(() => {
    if (!usuario) return

    async function cargarDatos() {
      try {
        const [usuarios, idIA] = await Promise.all([
          listarUsuarios(),
          obtenerIdIA()
        ])
        setContactos(usuarios.filter(u => u.id !== usuario.id))
        setIaId(idIA)
      } catch (error) {
        console.error('Error al cargar contactos:', error)
      }
    }

    cargarDatos()

    const intervalo = setInterval(cargarDatos, 10000)
    return () => clearInterval(intervalo)
  }, [usuario])

  // Cerrar sesión: limpia token, contactos y vuelve al registro
  function handleLogout() {
    setToken(null)
    setUsuario(null)
    setContactos([])
    setContactoActivo(null)
    setIaId(null)
  }

  // Pantalla de carga inicial
  if (cargandoSesion) {
    return (
      <div className="flex items-center justify-center h-screen bg-vibe-950">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-vibe flex items-center
                          justify-center shadow-glow-cyan animate-pulse">
            <MessageCircle size={24} className="text-white" />
          </div>
          <div className="text-vibe-400 text-sm">Cargando Vibe...</div>
        </div>
      </div>
    )
  }

  if (!usuario) {
    return <Registro onRegistro={setUsuario} />
  }

  return (
    <div className="flex h-screen bg-vibe-950 overflow-hidden">
      {/* Sidebar ahora recibe contactos e iaId para acceso rápido a Lumi,
          y onSeleccionar para abrir la conversación con ella */}
      <Sidebar
        usuario={usuario}
        contactos={contactos}
        iaId={iaId}
        onSeleccionar={setContactoActivo}
        onLogout={handleLogout}
      />

      <ListaContactos
        contactos={contactos}
        contactoActivo={contactoActivo}
        onSeleccionar={setContactoActivo}
        usuarioActual={usuario}
        iaId={iaId}
      />

      {contactoActivo ? (
        <Chat
          usuarioActual={usuario}
          contacto={contactoActivo}
          iaId={iaId}
        />
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center bg-vibe-950">
          <div className="w-20 h-20 rounded-2xl bg-vibe-900 flex items-center
                          justify-center mb-4 border border-vibe-800">
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
  )
}