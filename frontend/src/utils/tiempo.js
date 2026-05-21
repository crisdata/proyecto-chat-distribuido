// tiempo.js
// Helpers para formatear fechas y tiempos relativos en español.
//
// formatearTiempoRelativo convierte un timestamp ISO en texto humano:
//   - "hace unos segundos"
//   - "hace 5 min"
//   - "hace 3 horas"
//   - "hace 2 días"
//   - "el 15 mar"

/**
 * Convierte un timestamp ISO en texto relativo en español.
 * Retorna string vacío si el timestamp es inválido o null.
 */
export function formatearTiempoRelativo(timestampISO) {
  if (!timestampISO) return ''

  const fecha = new Date(timestampISO)
  if (isNaN(fecha.getTime())) return ''

  const ahora = new Date()
  const diffMs = ahora - fecha
  const diffSeg = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSeg / 60)
  const diffHoras = Math.floor(diffMin / 60)
  const diffDias = Math.floor(diffHoras / 24)

  if (diffSeg < 10) return 'hace un momento'
  if (diffSeg < 60) return 'hace unos segundos'
  if (diffMin < 60) return `hace ${diffMin} min`
  if (diffHoras < 24) return `hace ${diffHoras} ${diffHoras === 1 ? 'hora' : 'horas'}`
  if (diffDias < 7) return `hace ${diffDias} ${diffDias === 1 ? 'día' : 'días'}`

  // Más de 7 días: mostrar fecha corta
  const meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
                 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
  return `el ${fecha.getDate()} ${meses[fecha.getMonth()]}`
}