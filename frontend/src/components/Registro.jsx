// Registro.jsx
// Pantalla inicial de bienvenida a Vibe.
// El usuario escribe su nombre para registrarse en el sistema.

import { useState } from 'react'
import { MessageCircle, Sparkles } from 'lucide-react'
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

  function handleKeyDown(e) {
    if (e.key === 'Enter') handleRegistro()
  }

  return (
    <div className="flex items-center justify-center h-screen bg-vibe-950 px-4">
      <div className="bg-vibe-900 rounded-3xl shadow-panel p-10 w-full max-w-sm
                      flex flex-col gap-5 border border-vibe-800">

        {/* Logo e identidad */}
        <div className="flex flex-col items-center gap-3 mb-2">
          <div className="w-16 h-16 rounded-2xl bg-gradient-vibe flex items-center
                          justify-center shadow-glow-cyan">
            <MessageCircle size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-vibe-100 tracking-tight">
            Vibe
          </h1>
          <p className="text-sm text-vibe-400 text-center leading-relaxed">
            Conecta con personas reales.<br />
            Tu privacidad, primero.
          </p>
        </div>

        {/* Campo de nombre */}
        <input
          type="text"
          placeholder="¿Cómo te llamas?"
          value={nombre}
          onChange={e => setNombre(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={100}
          disabled={cargando}
          className="w-full px-4 py-3.5 rounded-xl border border-vibe-700
                     bg-vibe-800 text-vibe-100 placeholder-vibe-500
                     focus:outline-none focus:ring-2 focus:ring-cyan-500
                     focus:border-transparent transition disabled:opacity-50"
        />

        {/* Mensaje de error */}
        {error && (
          <p className="text-red-400 text-sm text-center -mt-2">
            {error}
          </p>
        )}

        {/* Botón de registro */}
        <button
          onClick={handleRegistro}
          disabled={cargando || nombre.trim().length < 2}
          className="w-full py-3.5 rounded-xl bg-gradient-vibe
                     text-white font-semibold transition shadow-glow-cyan
                     hover:opacity-90 active:scale-[0.98]
                     disabled:opacity-50 disabled:cursor-not-allowed
                     disabled:shadow-none"
        >
          {cargando ? 'Entrando...' : 'Entrar a Vibe'}
        </button>

        {/* Lumi como teaser */}
        <div className="flex items-center justify-center gap-2 text-xs
                        text-vibe-500 -mt-1">
          <Sparkles size={12} className="text-lumi-400" />
          <span>Conoce a Lumi, tu compañera virtual</span>
        </div>

        {/* Footer */}
        <p className="text-xs text-vibe-600 text-center mt-2">
          Proyecto académico — COTECNOVA
        </p>
      </div>
    </div>
  )
}