// IndicadorPresencia.jsx
// Punto visual que indica el estado de presencia de un usuario.
// Se coloca como overlay en la esquina inferior derecha del avatar.
//
// Estados:
//   online    -> verde   (usuario con WebSocket activo, o Lumi con Ollama OK)
//   offline   -> gris    (usuario desconectado)
//   reposando -> ámbar   (exclusivo de Lumi: Ollama no disponible)

const COLORES_PRESENCIA = {
  online: '#34d399',     // verde esmeralda
  offline: '#64748b',    // slate gris
  reposando: '#fbbf24',  // ámbar (solo Lumi)
}

export default function IndicadorPresencia({ estado, tamano = 'md' }) {
  const color = COLORES_PRESENCIA[estado] || COLORES_PRESENCIA.offline

  // Tamaños configurables: sm para avatares pequeños de mensajes,
  // md para lista y sidebar, lg para header del chat
  const dimensiones = {
    sm: { punto: 'w-2.5 h-2.5', borde: 'border-2' },
    md: { punto: 'w-3 h-3', borde: 'border-2' },
    lg: { punto: 'w-3.5 h-3.5', borde: 'border-2' },
  }[tamano] || { punto: 'w-3 h-3', borde: 'border-2' }

  return (
    <span
      className={`${dimensiones.punto} ${dimensiones.borde}
                  border-vibe-900 rounded-full
                  absolute bottom-0 right-0
                  ${estado === 'online' ? 'shadow-glow-online' : ''}`}
      style={{ backgroundColor: color }}
      aria-label={`Estado: ${estado}`}
    />
  )
}