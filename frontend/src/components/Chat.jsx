// Chat.jsx
// Panel derecho con la conversación activa entre dos usuarios.
// Tema oscuro Vibe. Tinte púrpura cuando el contacto es la IA.

import { useState, useEffect, useRef, useCallback } from 'react'
import { Send, Bot, User, Loader, Wifi, WifiOff, Shield, Flame } from 'lucide-react'
import Mensaje from './Mensaje'
import {
  enviarMensaje,
  enviarMensajeIA,
  esHoy,
  crearWebSocket
} from '../services/api'

const BASE_URL = '/api'

export default function Chat({ usuarioActual, contacto, iaId }) {
  const [mensajes, setMensajes] = useState([])
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [estadoWS, setEstadoWS] = useState('conectado')
  const finalRef = useRef(null)
  const esIA = contacto.id === iaId

  const cargarConversacion = useCallback(async () => {
    try {
      const res = await fetch(
        `${BASE_URL}/conversacion/${usuarioActual.id}/${contacto.id}`
      )
      if (!res.ok) throw new Error('Error al cargar conversación')
      const data = await res.json()
      setMensajes(data)
    } catch (error) {
      console.error('Error al cargar mensajes:', error)
    }
  }, [usuarioActual.id, contacto.id])

  useEffect(() => {
    setCargando(true)
    setMensajes([])
    cargarConversacion().finally(() => setCargando(false))

    const cerrarWS = crearWebSocket(
      usuarioActual.id,
      (datos) => {
        if (datos.tipo === 'nuevo_mensaje' &&
            datos.emisor_id === contacto.id) {
          cargarConversacion()
        }
      },
      (estado) => setEstadoWS(estado)
    )

    return () => cerrarWS()
  }, [usuarioActual.id, contacto.id, cargarConversacion])

  useEffect(() => {
    finalRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes])

  async function handleEnviar() {
    const contenido = texto.trim()
    if (!contenido || enviando) return

    setEnviando(true)
    setTexto('')

    try {
      if (esIA) {
        await enviarMensajeIA(usuarioActual.id, iaId, contenido)
      } else {
        await enviarMensaje(usuarioActual.id, contacto.id, contenido)
      }
      await cargarConversacion()
    } catch (error) {
      console.error('Error al enviar mensaje:', error)
      setTexto(contenido)
    } finally {
      setEnviando(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleEnviar()
    }
  }

  // Agrupar mensajes por fecha
  function renderMensajes() {
    let fechaAnterior = null
    return mensajes.map((mensaje, index) => {
      const fechaActual = new Date(mensaje.timestamp).toDateString()
      const mostrarFecha = fechaActual !== fechaAnterior
      fechaAnterior = fechaActual

      return (
        <div key={mensaje.id || index}>
          {mostrarFecha && (
            <div className="flex items-center justify-center my-4">
              <span className="px-3 py-1 bg-vibe-800 text-vibe-500
                               text-xs rounded-full border border-vibe-700">
                {esHoy(mensaje.timestamp) ? 'Hoy' : fechaActual}
              </span>
            </div>
          )}
          <Mensaje
            mensaje={mensaje}
            usuarioActual={usuarioActual}
            iaId={iaId}
            nombreEmisor={
              mensaje.emisor_id === contacto.id ? contacto.nombre : null
            }
          />
        </div>
      )
    })
  }

  // Indicador de estado WebSocket
  const indicadorWS = {
    conectado: {
      icono: <Wifi size={14} />,
      texto: 'En línea',
      clase: 'text-online-400'
    },
    reconectando: {
      icono: <Loader size={14} className="animate-spin" />,
      texto: 'Reconectando...',
      clase: 'text-amber-400'
    },
    desconectado: {
      icono: <WifiOff size={14} />,
      texto: 'Sin conexión',
      clase: 'text-red-400'
    }
  }[estadoWS] || {
    icono: <Wifi size={14} />,
    texto: 'En línea',
    clase: 'text-online-400'
  }

  return (
    <div className="flex-1 flex flex-col bg-vibe-950">

      {/* Encabezado de la conversación */}
      <div className="bg-vibe-950 border-b border-vibe-800 px-6 py-4
                      flex items-center gap-3">
        <div className={`w-10 h-10 rounded-full flex items-center justify-center
                         text-white font-semibold flex-shrink-0
                         ${esIA ? 'bg-gradient-lumi' : 'bg-gradient-vibe'}`}>
          {esIA
            ? <Bot size={20} />
            : contacto.nombre.charAt(0).toUpperCase()
          }
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-vibe-100 text-sm">
            {contacto.nombre}
          </h3>
          {esIA ? (
            <p className="text-xs text-lumi-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-lumi-400 inline-block"></span>
              {`Modelo: ${import.meta.env.VITE_OLLAMA_MODEL || 'llama3.2:3b'}`}
            </p>
          ) : (
            <div className={`flex items-center gap-1 text-xs ${indicadorWS.clase}`}>
              {indicadorWS.icono}
              <span>{indicadorWS.texto}</span>
            </div>
          )}
        </div>
        {/* Ícono de privacidad (decorativo, refuerza la identidad) */}
        <Shield size={18} className="text-cyan-500" />
      </div>

      {/* Área de mensajes */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {cargando ? (
          <div className="flex items-center justify-center h-full gap-2
                          text-vibe-500 text-sm">
            <Loader size={18} className="animate-spin" />
            <span>Cargando conversación...</span>
          </div>
        ) : mensajes.length === 0 ? (
          <div className="flex flex-col items-center justify-center
                          h-full gap-3 text-vibe-500">
            <div className={`w-16 h-16 rounded-full flex items-center
                              justify-center
                              ${esIA
                                ? 'bg-lumi-400/15'
                                : 'bg-cyan-500/15'}`}>
              {esIA
                ? <Bot size={32} className="text-lumi-400" />
                : <User size={32} className="text-cyan-400" />
              }
            </div>
            <p className="text-sm font-medium text-vibe-300">
              {esIA
                ? '¡Hola! Soy tu asistente de IA. ¿En qué puedo ayudarte?'
                : `Inicia una conversación con ${contacto.nombre}`
              }
            </p>
          </div>
        ) : (
          renderMensajes()
        )}

        {/* Indicador de escritura cuando la IA está procesando */}
        {enviando && esIA && (
          <div className="flex items-center gap-2 mt-2 text-vibe-500 text-xs">
            <Loader size={14} className="animate-spin text-lumi-400" />
            <span>El asistente está pensando...</span>
          </div>
        )}
        <div ref={finalRef} />
      </div>

      {/* Input de mensaje */}
      <div className="bg-vibe-950 border-t border-vibe-800 px-4 py-3
                      flex items-end gap-3">
        {/* Ícono de mensaje autodestructivo — funcionalidad en Sprint 3 */}
        <button
          title="Mensaje autodestructivo (próximamente)"
          disabled
          className="w-10 h-10 rounded-xl bg-vibe-800 text-vibe-600
                     flex items-center justify-center
                     hover:bg-vibe-700 hover:text-cyan-400 transition
                     disabled:cursor-not-allowed"
        >
          <Flame size={18} />
        </button>

        <textarea
          value={texto}
          onChange={e => setTexto(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Escribe un mensaje..."
          rows={1}
          disabled={enviando}
          className="flex-1 px-4 py-2.5 rounded-2xl bg-vibe-800
                     border border-vibe-700 text-sm text-vibe-100
                     placeholder-vibe-500 outline-none resize-none
                     focus:ring-2 focus:ring-cyan-500
                     focus:border-transparent transition
                     disabled:opacity-50 max-h-32 overflow-y-auto"
        />
        <button
          onClick={handleEnviar}
          disabled={!texto.trim() || enviando}
          className="w-10 h-10 rounded-full bg-gradient-vibe
                     text-white flex items-center justify-center
                     transition flex-shrink-0 shadow-glow-cyan
                     hover:opacity-90 active:scale-95
                     disabled:opacity-40 disabled:cursor-not-allowed
                     disabled:shadow-none"
        >
          {enviando
            ? <Loader size={18} className="animate-spin" />
            : <Send size={18} />
          }
        </button>
      </div>

    </div>
  )
}