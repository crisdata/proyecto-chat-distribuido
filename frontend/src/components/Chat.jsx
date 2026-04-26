// Chat.jsx
// Panel derecho con la conversación activa entre dos usuarios.
// Usa WebSocket para recibir mensajes en tiempo real.
// Incluye reconexión automática con backoff exponencial
// e indicador visual del estado de conexión.

import { useState, useEffect, useRef, useCallback } from 'react'
import { Send, Bot, User, Loader, Wifi, WifiOff } from 'lucide-react'
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
  // Estado de la conexión WebSocket para el indicador visual
  const [estadoWS, setEstadoWS] = useState('conectado')
  const finalRef = useRef(null)
  const esIA = contacto.id === iaId

  // Carga la conversación bilateral desde el backend.
  // Se llama al montar, al recibir notificación WS y al enviar.
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

  // Cargar conversación al montar y conectar WebSocket
  useEffect(() => {
    setCargando(true)
    setMensajes([])
    cargarConversacion().finally(() => setCargando(false))

    // Crear conexión WebSocket con reconexión automática.
    // onMensaje se ejecuta al recibir notificación del servidor.
    // onEstado actualiza el indicador visual de conexión.
    const cerrarWS = crearWebSocket(
      usuarioActual.id,
      (datos) => {
        // Solo recargar si el mensaje viene del contacto activo
        if (datos.tipo === 'nuevo_mensaje' &&
            datos.emisor_id === contacto.id) {
          cargarConversacion()
        }
      },
      (estado) => setEstadoWS(estado)
    )

    // Cleanup: cerrar WebSocket al desmontar o cambiar de contacto
    return () => cerrarWS()
  }, [usuarioActual.id, contacto.id, cargarConversacion])

  // Auto-scroll al último mensaje cuando llegan mensajes nuevos
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
      // Recargar conversación inmediatamente después de enviar
      await cargarConversacion()
    } catch (error) {
      console.error('Error al enviar mensaje:', error)
      setTexto(contenido)
    } finally {
      setEnviando(false)
    }
  }

  // Enviar con Enter, nueva línea con Shift+Enter
  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleEnviar()
    }
  }

  // Agrupar mensajes por fecha para mostrar separadores
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
              <span className="px-3 py-1 bg-gray-100 rounded-full
                               text-xs text-gray-500">
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

  // Configuración del indicador visual de estado WebSocket
  const indicadorWS = {
    conectado: {
      icono: <Wifi size={14} />,
      texto: 'En línea',
      clase: 'text-emerald-500'
    },
    reconectando: {
      icono: <Loader size={14} className="animate-spin" />,
      texto: 'Reconectando...',
      clase: 'text-amber-500'
    },
    desconectado: {
      icono: <WifiOff size={14} />,
      texto: 'Sin conexión',
      clase: 'text-red-400'
    }
  }[estadoWS] || {
    icono: <Wifi size={14} />,
    texto: 'En línea',
    clase: 'text-emerald-500'
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-50">

      {/* Encabezado de la conversación */}
      <div className="bg-white border-b border-gray-100 px-6 py-4
                      flex items-center gap-3 shadow-panel">
        <div className={`w-10 h-10 rounded-full flex items-center justify-center
                         text-white font-semibold flex-shrink-0
                         ${esIA ? 'bg-emerald-500' : 'bg-primary-400'}`}>
          {esIA
            ? <Bot size={20} />
            : contacto.nombre.charAt(0).toUpperCase()
          }
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-800 text-sm">
            {contacto.nombre}
          </h3>
          {/* Indicador de estado: IA muestra modelo, usuarios muestran estado WS */}
          {esIA ? (
            <p className="text-xs text-emerald-500">
              {`Modelo: ${import.meta.env.VITE_OLLAMA_MODEL || 'llama3.2:3b'}`}
            </p>
          ) : (
            <div className={`flex items-center gap-1 text-xs ${indicadorWS.clase}`}>
              {indicadorWS.icono}
              <span>{indicadorWS.texto}</span>
            </div>
          )}
        </div>
        <div className="text-gray-400">
          {esIA ? <Bot size={18} /> : <User size={18} />}
        </div>
      </div>

      {/* Área de mensajes */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {cargando ? (
          <div className="flex items-center justify-center h-full gap-2
                          text-gray-400 text-sm">
            <Loader size={18} className="animate-spin" />
            <span>Cargando conversación...</span>
          </div>
        ) : mensajes.length === 0 ? (
          <div className="flex flex-col items-center justify-center
                          h-full gap-3 text-gray-400">
            <div className={`w-16 h-16 rounded-full flex items-center
                              justify-center
                              ${esIA ? 'bg-emerald-100' : 'bg-primary-50'}`}>
              {esIA
                ? <Bot size={32} className="text-emerald-500" />
                : <User size={32} className="text-primary-400" />
              }
            </div>
            <p className="text-sm font-medium text-gray-500">
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
          <div className="flex items-center gap-2 mt-2 text-gray-400 text-xs">
            <Loader size={14} className="animate-spin" />
            <span>El asistente está escribiendo...</span>
          </div>
        )}
        <div ref={finalRef} />
      </div>

      {/* Input de mensaje */}
      <div className="bg-white border-t border-gray-100 px-4 py-3
                      flex items-end gap-3">
        <textarea
          value={texto}
          onChange={e => setTexto(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Escribe un mensaje..."
          rows={1}
          disabled={enviando}
          className="flex-1 px-4 py-2.5 rounded-2xl bg-gray-50
                     border border-gray-200 text-sm text-gray-800
                     placeholder-gray-400 outline-none resize-none
                     focus:ring-2 focus:ring-primary-500
                     focus:border-transparent transition
                     disabled:opacity-50 max-h-32 overflow-y-auto"
        />
        <button
          onClick={handleEnviar}
          disabled={!texto.trim() || enviando}
          className="w-10 h-10 rounded-full bg-primary-500
                     hover:bg-primary-600 text-white flex items-center
                     justify-center transition flex-shrink-0
                     disabled:opacity-50 disabled:cursor-not-allowed"
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