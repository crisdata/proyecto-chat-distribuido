// App.jsx
// Componente raíz de la aplicación.
// Gestiona el estado global y aplica el contenedor con la paleta Vibe.
//
// Los polling de presencia y no leídos viven aquí porque App.jsx es el
// único componente que NUNCA se desmonta mientras hay sesión activa.

import { useState, useEffect, useRef, useMemo } from 'react'
import { MessageCircle } from 'lucide-react'
import Registro from './components/Registro'
import Sidebar from './components/Sidebar'
import ListaContactos from './components/ListaContactos'
import Chat from './components/Chat'
import {
  listarUsuarios,
  obtenerIdIA,
  obtenerUsuarioActual,
  obtenerNoLeidos,
  marcarComoLeidos,
  setToken
} from './services/api'
import { usePresencia } from './hooks/usePresencia'

export default function App() {
  const [usuario, setUsuario] = useState(null)
  const [contactos, setContactos] = useState([])
  const [contactoActivo, setContactoActivo] = useState(null)
  const [iaId, setIaId] = useState(null)
  const [cargandoSesion, setCargandoSesion] = useState(true)
  const [noLeidos, setNoLeidos] = useState({ total: 0, porContacto: {} })

  const huellaContactosRef = useRef('')

  const idsParaPresencia = useMemo(
    () => contactos.map(c => c.id),
    [contactos]
  )

  const presencias = usePresencia(idsParaPresencia)

  // Restaurar sesión al montar
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

  // Polling de contactos cada 10s
  useEffect(() => {
    if (!usuario) return

    async function cargarDatos() {
      try {
        const [usuarios, idIA] = await Promise.all([
          listarUsuarios(),
          obtenerIdIA()
        ])

        const nuevosContactos = usuarios.filter(u => u.id !== usuario.id)
        const nuevaHuella = nuevosContactos
          .map(c => `${c.id}:${c.nombre}`)
          .sort()
          .join('|')

        if (nuevaHuella !== huellaContactosRef.current) {
          huellaContactosRef.current = nuevaHuella
          setContactos(nuevosContactos)
        }

        setIaId(prev => prev === idIA ? prev : idIA)
      } catch (error) {
        console.error('Error al cargar contactos:', error)
      }
    }

    cargarDatos()
    const intervalo = setInterval(cargarDatos, 10000)
    return () => clearInterval(intervalo)
  }, [usuario])

  // Polling de mensajes no leídos cada 3s.
  // Usa una ref con el id del usuario para que el polling sea
  // estable y no se reinicie por re-renders.
  const usuarioIdRef = useRef(null)
  usuarioIdRef.current = usuario?.id || null

  useEffect(() => {
    if (!usuario) {
      setNoLeidos({ total: 0, porContacto: {} })
      return
    }

    let cancelado = false

    async function actualizar() {
      const uid = usuarioIdRef.current
      if (!uid) return

      const data = await obtenerNoLeidos(uid)
      if (cancelado) return

      setNoLeidos({
        total: data.no_leidos || 0,
        porContacto: data.por_contacto || {}
      })
    }

    actualizar()
    const intervalo = setInterval(actualizar, 3000)

    return () => {
      cancelado = true
      clearInterval(intervalo)
    }
  }, [usuario])

  // Al seleccionar un contacto, marcarlo como leído.
  // Esto borra el badge específico de ese contacto.
  async function handleSeleccionarContacto(contacto) {
    setContactoActivo(contacto)
    if (usuario && contacto) {
      await marcarComoLeidos(usuario.id, contacto.id)
      // Refrescar inmediatamente para que el badge desaparezca
      const data = await obtenerNoLeidos(usuario.id)
      setNoLeidos({
        total: data.no_leidos || 0,
        porContacto: data.por_contacto || {}
      })
    }
  }

  function handleLogout() {
    setToken(null)
    setUsuario(null)
    setContactos([])
    setContactoActivo(null)
    setIaId(null)
    setNoLeidos({ total: 0, porContacto: {} })
    huellaContactosRef.current = ''
  }

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
      <Sidebar
        usuario={usuario}
        contactos={contactos}
        iaId={iaId}
        onSeleccionar={handleSeleccionarContacto}
        onLogout={handleLogout}
      />

      <ListaContactos
        contactos={contactos}
        contactoActivo={contactoActivo}
        onSeleccionar={handleSeleccionarContacto}
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