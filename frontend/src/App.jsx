// App.jsx
// Componente raíz de la aplicación.
// Gestiona el estado global: usuario autenticado, contactos,
// contacto seleccionado e ID del nodo IA.

import { useState, useEffect } from 'react'
import Registro from './components/Registro'
import Sidebar from './components/Sidebar'
import ListaContactos from './components/ListaContactos'
import Chat from './components/Chat'
import { listarUsuarios, obtenerIdIA } from './services/api'

export default function App() {
  // Usuario actual registrado en el sistema
  const [usuario, setUsuario] = useState(null)
  // Lista de todos los contactos disponibles
  const [contactos, setContactos] = useState([])
  // Contacto actualmente seleccionado para chatear
  const [contactoActivo, setContactoActivo] = useState(null)
  // ID del nodo IA para identificarlo en la lista de contactos
  const [iaId, setIaId] = useState(null)

  // Al registrarse, cargar contactos e ID del nodo IA
  useEffect(() => {
    if (!usuario) return

    async function cargarDatos() {
      try {
        const [usuarios, idIA] = await Promise.all([
          listarUsuarios(),
          obtenerIdIA()
        ])
        // Excluir al usuario actual de su propia lista de contactos
        setContactos(usuarios.filter(u => u.id !== usuario.id))
        setIaId(idIA)
      } catch (error) {
        console.error('Error al cargar contactos:', error)
      }
    }

    cargarDatos()

    // Actualizar lista de contactos cada 10 segundos
    // para mostrar nuevos usuarios que se registren
    const intervalo = setInterval(cargarDatos, 10000)
    return () => clearInterval(intervalo)
  }, [usuario])

  // Mientras no hay usuario registrado mostrar pantalla de registro
  if (!usuario) {
    return <Registro onRegistro={setUsuario} />
  }

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* Sidebar izquierdo con navegación */}
      <Sidebar usuario={usuario} />

      {/* Panel central con lista de contactos */}
      <ListaContactos
        contactos={contactos}
        contactoActivo={contactoActivo}
        onSeleccionar={setContactoActivo}
        usuarioActual={usuario}
        iaId={iaId}
      />

      {/* Panel derecho con la conversación */}
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