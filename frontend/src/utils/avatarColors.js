// avatarColors.js
// Estilo de avatar único por usuario, basado en hash determinístico del nombre.
//
// Filosofía visual:
//   - Usuarios humanos: avatar slate neutro + letra coloreada
//     (minimalismo elegante, no invade visualmente)
//   - Lumi (IA): gradiente púrpura vibrante completo
//     (única identidad cálida, destaca naturalmente)

// Paleta de colores para las letras de avatares humanos.
// Tonos vibrantes pero como son solo para una letra pequeña,
// no abruman la composición general.
const COLORES_LETRA = [
  '#60a5fa',  // azul cielo
  '#f472b6',  // rosa
  '#34d399',  // esmeralda
  '#fbbf24',  // ámbar
  '#22d3ee',  // cian
  '#c084fc',  // violeta claro
  '#a3e635',  // lima
  '#fb923c',  // coral
]

// Gradiente exclusivo de Lumi (la IA). Mantiene su identidad vibrante completa.
const GRADIENTE_LUMI = { from: '#a855f7', to: '#6366f1' }

/**
 * Hash simple y determinístico de un string.
 * Algoritmo djb2 modificado.
 */
function hashString(str) {
  let hash = 5381
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash) + str.charCodeAt(i)
    hash = hash & hash
  }
  return Math.abs(hash)
}

/**
 * Retorna el color único asignado al usuario para su letra.
 * Determinístico: el mismo nombre siempre tiene el mismo color.
 */
export function getColorLetra(nombre) {
  if (!nombre) return COLORES_LETRA[0]
  const hash = hashString(nombre.toLowerCase())
  return COLORES_LETRA[hash % COLORES_LETRA.length]
}

/**
 * Retorna el estilo inline del avatar listo para usar en JSX.
 *
 * Para Lumi (esIA=true): gradiente púrpura completo con texto blanco
 * Para humanos: fondo slate neutro con borde sutil, color de letra único
 */
export function getAvatarStyle(nombre, esIA = false) {
  if (esIA) {
    const { from, to } = GRADIENTE_LUMI
    return {
      background: `linear-gradient(135deg, ${from} 0%, ${to} 100%)`,
      color: '#ffffff',
    }
  }

  return {
    background: '#1e293b',
    border: '0.5px solid #334155',
    color: getColorLetra(nombre),
  }
}