// usePresencia.js
// Hook que mantiene actualizado el estado de presencia de una lista de
// usuarios mediante polling al endpoint bulk cada N segundos.
//
// DISEÑO ROBUSTO:
//   - Un solo intervalo creado al montar, destruido al desmontar.
//   - Los IDs se leen desde una ref en cada tick del polling.
//   - Re-renders del padre NO reinician el polling.
//   - Tolerante a StrictMode (doble montaje en desarrollo).
//
// Uso:
//   const presencias = usePresencia(['uuid1', 'uuid2', ...])
//   presencias['uuid1'] -> { estado: 'online' | 'offline' | 'reposando' }

import { useState, useEffect, useRef } from 'react'

const INTERVALO_POLLING_MS = 10000  // 10 segundos
const BASE_URL = '/api'

export function usePresencia(usuarioIds) {
  const [presencias, setPresencias] = useState({})

  // Ref que siempre contiene los IDs actuales del padre.
  // Actualizarla NO causa re-render ni reinicia efectos.
  const idsActualesRef = useRef([])
  idsActualesRef.current = usuarioIds || []

  useEffect(() => {
    let cancelado = false

    async function consultarPresencia() {
      const ids = idsActualesRef.current
      if (!ids || ids.length === 0) {
        if (!cancelado) setPresencias({})
        return
      }

      try {
        const res = await fetch(`${BASE_URL}/usuarios/presencia/bulk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ usuario_ids: ids })
        })

        if (!res.ok) {
          console.warn('Error consultando presencia bulk:', res.status)
          return
        }

        const data = await res.json()
        if (cancelado) return

        const mapa = {}
        for (const p of data) {
          mapa[p.usuario_id] = {
            estado: p.estado,
            ultima_actividad: p.ultima_actividad
          }
        }
        setPresencias(mapa)
      } catch (error) {
        console.warn('Error de red consultando presencia:', error)
      }
    }

    // Primera consulta inmediata
    consultarPresencia()

    // Polling periódico — el intervalo se crea UNA SOLA VEZ al montar
    const intervalo = setInterval(consultarPresencia, INTERVALO_POLLING_MS)

    return () => {
      cancelado = true
      clearInterval(intervalo)
    }
  }, [])  // Dependencias vacías: el efecto corre solo al montar/desmontar

  return presencias
}