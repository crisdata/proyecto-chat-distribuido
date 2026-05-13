// App.jsx
// Componente raíz de la aplicación.
// Gestiona el estado global: usuario autenticado, contactos,
// contacto seleccionado e ID del nodo IA.
// Al cargar, intenta restaurar la sesión desde el token guardado
// en sessionStorage. Si el token sigue siendo válido, entra directo
// al chat. Si no, muestra el formulario de registro.

import { useState, useEffect } from 'react'
import Registro from './components/Registro'
import Sidebar from './components/Sidebar'
import ListaContactos from './components/ListaContactos'
import Chat from './components/Chat'
import {
  listarUsuarios,
  obtenerIdIA,
  obtenerUsuarioActual
} from './services/api'

export default function App() {
  const [usuario, setUsuario] = useState(null)
  const [contactos, setContactos] = useState([])
  const [contactoActivo, setContactoActivo] = useState(null)
  const [iaId, setIaId] = useState(null)
  // Estado para evitar el "flash" del formulario de registro
  // mientras se verifica el token al cargar la página
  const [cargandoSesion, setCargandoSesion] = useState(true)

  // Al montar el componente: intentar restaurar la sesión
  // desde el token guardado en sessionStorage
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

  // Mientras se verifica el token, mostrar pantalla de carga simple
  if (cargandoSesion) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-gray-400 text-sm">Cargando...</div>
      </div>
    )
  }

  // Sin usuario logueado → pantalla de registro
  if (!usuario) {
    return <Registro onRegistro={setUsuario} />
  }

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      <Sidebar usuario={usuario} />

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
        <div className="flex-1 flex flex-col items-center justify-center bg-gray-50">
          <div className="text-6xl mb-4 opacity-20">💬</div>
          <p className="text-gray-400 text-sm">
            Selecciona un contacto para comenzar a chatear
          </p>
        </div>
      )}
    </div>
  )
}