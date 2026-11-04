import { useCallback, useEffect, useMemo, useState } from 'react'

const abreviar = (valor) => valor ? `${String(valor).slice(0, 13)}…${String(valor).slice(-9)}` : 'Sin dato'
const etiquetas = { genesis: 'Génesis', SOFI: 'SOFI', DIGITAL_TWIN: 'Digital Twin', PNL: 'PNL' }

export default function BlockchainPage() {
  const [datos, setDatos] = useState(null)
  const [verificacion, setVerificacion] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [verificando, setVerificando] = useState(false)
  const [error, setError] = useState('')
  const [filtro, setFiltro] = useState('todos')
  const [pagina, setPagina] = useState(1)

  const cargar = useCallback(async () => {
    setCargando(true)
    setError('')
    setVerificacion(null)
    try {
      const respuesta = await fetch('/api/blockchain/estado/')
      const json = await respuesta.json()
      if (!respuesta.ok) throw new Error(json.error || 'No se pudo cargar la cadena.')
      setDatos(json)
    } catch (err) { setError(err.message) }
    finally { setCargando(false) }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  async function verificar() {
    if (verificando || cargando) return
    setVerificando(true)
    setError('')
    setVerificacion(null)
    try {
      // Refrescar los bloques antes de validar, para no mostrar hashes antiguos.
      const estadoRespuesta = await fetch('/api/blockchain/estado/', { cache: 'no-store' })
      const estadoActual = await estadoRespuesta.json()
      if (!estadoRespuesta.ok) throw new Error(estadoActual.error || 'No se pudieron actualizar los bloques.')
      setDatos(estadoActual)

      const csrf = await fetch('/api/csrf/', { credentials: 'same-origin' })
      if (!csrf.ok) throw new Error('No se pudo obtener el token CSRF.')
      const { csrfToken } = await csrf.json()
      const respuesta = await fetch('/api/blockchain/verificar/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken },
        cache: 'no-store',
      })
      const json = await respuesta.json()
      if (!respuesta.ok) throw new Error(json.error || 'Falló la comprobación.')
      setVerificacion(json)
    } catch (err) { setError(err.message) }
    finally { setVerificando(false) }
  }

  const estados = useMemo(() => new Map(
    (verificacion?.auditoria?.resultados ?? []).map(item => [String(item.indice), item])
  ), [verificacion])
  const erroresCadena = useMemo(() => new Map(
    (verificacion?.cadena?.errores ?? []).map(item => [String(item.indice), item])
  ), [verificacion])
  const bloques = useMemo(() => (datos?.bloques ?? []).filter(b => filtro === 'todos' || b.tipo.toUpperCase() === filtro), [datos, filtro])
  const paginas = Math.max(1, Math.ceil(bloques.length / 10))
  const visibles = bloques.slice((pagina - 1) * 10, pagina * 10)
  const cadenaValida = verificacion?.cadena?.valida
  const auditoria = verificacion?.auditoria

  return (
    <div className="bc-page">
      <header className="bc-intro">
        <span className="bc-eyebrow">INTEGRIDAD / BLOCKCHAIN</span>
        <h1>Registro de integridad</h1>
        <p>Consulta los bloques de FailNet y verifica las huellas SHA-256 de tus análisis.</p>
      </header>

      <section className="bc-metrics" aria-label="Resumen de blockchain">
        <div className="bc-metric"><span>Bloques registrados</span><strong>{datos?.total_bloques?.toLocaleString('es-MX') ?? '—'}</strong><small>Incluye el historico de los bloques</small></div>
        <div className="bc-metric"><span>Análisis con referencia</span><strong>{datos ? datos.bloques.filter(b => b.datos?.analisis_id).length.toLocaleString('es-MX') : '—'}</strong><small>Vínculos declarados en la cadena</small></div>
        <div className="bc-metric bc-metric-dark"><span>Estado de la cadena</span><strong className="bc-verification-state">{cadenaValida === true ? 'Íntegra' : cadenaValida === false ? 'Alterada' : 'Sin verificar'}</strong><small>Resultado de la última comprobación</small></div>
      </section>

      <section className="bc-card bc-check">
        <div>
          <h2>Verificación de integridad</h2>
          <p>Comprueba el encadenamiento de bloques, sus hashes y la coincidencia de los análisis con Atlas y sus resultados.</p>
        </div>
        <button type="button" className={`sofi-run-button ${verificando ? 'is-loading' : ''}`} onClick={verificar} disabled={!datos || verificando || cargando} aria-busy={verificando}>
          <span>{verificando ? 'Actualizando y verificando…' : verificacion ? 'Volver a verificar' : 'Verificar integridad'}</span>
          {verificando ? <span className="sofi-run-spinner" aria-hidden="true" /> :
            <svg className="sofi-run-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6" /></svg>}
        </button>
      </section>

      {error && <div className="bc-notice bc-request-error" role="alert">{error} <button type="button" onClick={cargar}>Reintentar</button></div>}
      {verificacion && (
        <section className={`bc-notice ${cadenaValida && !auditoria.errores ? 'bc-good' : 'bc-warning'}`} aria-live="polite">
          <strong>{cadenaValida ? 'La cadena superó la verificación de hashes.' : 'La cadena no superó la verificación.'}</strong>
          <p>{verificacion.cadena.mensaje}</p>
          {cadenaValida && <p>{auditoria.verificados} análisis íntegros · {auditoria.errores} inconsistencias · {auditoria.historicos} bloques históricos sin vínculo verificable.</p>}
          {cadenaValida === false && (verificacion.cadena.errores ?? []).length > 0 &&
            <p>Bloques con problemas: {[...new Set(verificacion.cadena.errores.map(item => item.indice))].map(i => `#${i}`).join(', ')}. Los registros siguen disponibles para consulta.</p>}
        </section>
      )}

      <section className="bc-card">
        <div className="bc-card-heading">
          <div><h2>Historial de bloques</h2><p>Del más reciente al más antiguo. Selecciona un bloque para ver su información.</p></div>
          <label className="bc-filter">Módulo
            <select value={filtro} onChange={e => { setFiltro(e.target.value); setPagina(1) }}>
              <option value="todos">Todos</option><option value="SOFI">SOFI</option>
              <option value="DIGITAL_TWIN">Digital Twin</option><option value="PNL">PNL</option>
              <option value="GENESIS">Génesis</option>
            </select>
          </label>
        </div>
        {cargando ? <p className="bc-empty">Cargando bloques…</p> : bloques.length === 0 ? <p className="bc-empty">No hay bloques para este filtro.</p> : (
          <div className="bc-list">
            {visibles.map((b, index) => {
              const estado = estados.get(String(b.indice))
              const falloCadena = erroresCadena.get(String(b.indice))
              return <details className="bc-block" key={`${b.indice}-${b.hash}`}>
                <summary>
                  <span className="bc-number">#{b.indice}</span>
                  <span className="bc-block-name"><strong>{etiquetas[b.tipo] || b.tipo}</strong><small>{b.fecha || 'Fecha no disponible'}</small></span>
                  <span className="bc-block-hash" title={b.hash}>{abreviar(b.hash)}</span>
                  {falloCadena ? <span className="bc-state bc-invalid">{falloCadena.tipo === 'hash' ? 'Hash alterado' : 'Enlace inválido'}</span> :
                    estado && <span className={`bc-state ${estado.estado === 'error' ? 'bc-invalid' : `bc-${estado.estado}`}`}>{estado.estado === 'integro' ? 'Íntegro' : estado.estado === 'error' ? 'Inconsistencia' : 'Histórico'}</span>}
                  <span className="bc-caret" aria-hidden="true">⌄</span>
                </summary>
                <div className="bc-detail">
                  <div><span>Hash SHA-256</span><code>{b.hash}</code><button type="button" onClick={() => navigator.clipboard.writeText(b.hash)}>Copiar</button></div>
                  <div><span>Hash anterior</span><code>{b.hash_anterior}</code><button type="button" onClick={() => navigator.clipboard.writeText(b.hash_anterior)}>Copiar</button></div>
                  {b.datos?.analisis_id && <div><span>ID de análisis (Atlas)</span><code>{b.datos.analisis_id}</code></div>}
                  {b.datos?.sha256_entrada && <div><span>SHA-256 entrada</span><code>{b.datos.sha256_entrada}</code></div>}
                  {b.datos?.sha256_resultado && <div><span>SHA-256 resultado</span><code>{b.datos.sha256_resultado}</code></div>}
                  {falloCadena && <p className="bc-detail-alert">{falloCadena.mensaje}</p>}
                  {estado && <p className={estado.estado === 'error' ? 'bc-detail-alert' : 'bc-detail-note'}>{estado.mensaje}</p>}
                </div>
              </details>
            })}
          </div>
        )}
        <div className="bc-footer"><span>{bloques.length ? (pagina - 1) * 10 + 1 : 0}–{Math.min(pagina * 10, bloques.length)} de {bloques.length} bloques</span>
          <nav aria-label="Paginación de bloques"><button type="button" onClick={() => setPagina(p => p - 1)} disabled={pagina === 1}>Anterior</button><span>{pagina} / {paginas}</span><button type="button" onClick={() => setPagina(p => p + 1)} disabled={pagina >= paginas}>Siguiente</button></nav>
        </div>
      </section>
    </div>
  )
}
