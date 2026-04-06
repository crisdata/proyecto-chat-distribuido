// Registro.jsx
// Pantalla inicial de la aplicación.
// El usuario escribe su nombre para registrarse en el sistema.
// Una vez registrado, App.jsx toma el control y muestra el chat.

import { useState } from 'react'
import { registrarUsuario } from '../services/api'

export default function Registro({ onRegistro }) {
  const [nombre, setNombre] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  async function handleRegistro() {
    const nombreLimpio = nombre.trim()
    if (nombreLimpio.length < 2) {
      setError('El nombre debe tener al menos 2 caracteres.')
      return
    }

    setCargando(true)
    setError('')

    try {
      const usuario = await registrarUsuario(nombreLimpio)
      onRegistro(usuario)
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  // Permite enviar con Enter además del botón
  function handleKeyDown(e) {
    if (e.key === 'Enter') handleRegistro()
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <div className="bg-white rounded-2xl shadow-panel p-10 w-full max-w-sm flex flex-col gap-5">

        {/* Logo e identidad */}
        <div className="flex flex-col items-center gap-2 mb-2">
          <div className="text-5xl">💬</div>
          <h1 className="text-2xl font-semibold text-gray-800">
            Chat Distribuido
          </h1>
          <p className="text-sm text-gray-400 text-center">
            Ingresa tu nombre para comenzar
          </p>
        </div>

        {/* Campo de nombre */}
        <input
          type="text"
          placeholder="Tu nombre..."
          value={nombre}
          onChange={e => setNombre(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={100}
          disabled={cargando}
          className="w-full px-4 py-3 rounded-xl border border-gray-200
                     bg-gray-50 text-gray-800 placeholder-gray-400
                     focus:outline-none focus:ring-2 focus:ring-primary-500
                     focus:border-transparent transition disabled:opacity-50"
        />

        {/* Mensaje de error */}
        {error && (
          <p className="text-red-500 text-sm text-center -mt-2">
            {error}
          </p>
        )}

        {/* Botón de registro */}
        <button
          onClick={handleRegistro}
          disabled={cargando || nombre.trim().length < 2}
          className="w-full py-3 rounded-xl bg-primary-500 hover:bg-primary-600
                     text-white font-semibold transition
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {cargando ? 'Registrando...' : 'Entrar al chat'}
        </button>

        {/* Nota informativa */}
        <p className="text-xs text-gray-400 text-center">
          Proyecto Grupo 4 — COTECNOVA
        </p>
      </div>
    </div>
  )
}
