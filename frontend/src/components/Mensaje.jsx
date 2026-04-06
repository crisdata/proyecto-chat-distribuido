// Mensaje.jsx
// Burbuja individual de mensaje dentro de la conversación.
// Diferencia visualmente entre mensajes enviados, recibidos y de la IA.

import { Bot } from 'lucide-react'
import { formatearHora } from '../services/api'

export default function Mensaje({ mensaje, usuarioActual, iaId, nombreEmisor }) {
  const esEnviado = mensaje.emisor_id === usuarioActual.id
  const esIA = mensaje.emisor_id === iaId

  return (
    <div className={`flex items-end gap-2 mb-1
                     ${esEnviado ? 'flex-row-reverse' : 'flex-row'}`}>

      {/* Avatar del remitente — solo visible en mensajes recibidos */}
      {!esEnviado && (
        <div className={`w-7 h-7 rounded-full flex items-center justify-center
                         flex-shrink-0 text-white text-xs font-semibold mb-1
                         ${esIA ? 'bg-emerald-500' : 'bg-primary-400'}`}>
          {esIA
            ? <Bot size={14} />
            : (nombreEmisor?.charAt(0).toUpperCase() || '?')
          }
        </div>
      )}

      {/* Burbuja del mensaje */}
      <div className={`max-w-xs lg:max-w-md px-4 py-2.5 rounded-2xl
                       shadow-message text-sm leading-relaxed
                       ${esEnviado
                         ? 'bg-chat-sent text-gray-800 rounded-br-sm'
                         : esIA
                           ? 'bg-chat-ia text-gray-800 rounded-bl-sm border-l-2 border-emerald-400'
                           : 'bg-chat-received text-gray-800 rounded-bl-sm border border-gray-100'
                       }`}>

        {/* Contenido del mensaje */}
        <p className="whitespace-pre-wrap break-words">
          {mensaje.contenido}
        </p>

        {/* Hora del mensaje */}
        <p className={`text-xs mt-1 text-right
                       ${esEnviado ? 'text-gray-500' : 'text-gray-400'}`}>
          {formatearHora(mensaje.timestamp)}
        </p>
      </div>

    </div>
  )
}