import { useCallback, useEffect, useRef, useState } from 'react'

const MAX_CARACTERES = 8000
const CATEGORIAS = {
  conectividad: { titulo: 'Conectividad', descripcion: 'Problemas de comunicación entre equipos' },
  interfaces: { titulo: 'Interfaces', descripcion: 'Eventos asociados con interfaces de red' },
  rendimiento: { titulo: 'Rendimiento', descripcion: 'Latencia, lentitud o degradación' },
  servicios: { titulo: 'Servicios', descripcion: 'Problemas de servicios de red' },
}
const ETIQUETAS_ENTIDADES = {
  dispositivos: 'Dispositivos', direcciones_ip: 'Direcciones IP',
  interfaces: 'Interfaces', protocolos: 'Protocolos',
}
const fecha = texto => new Date(texto).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })

async function obtenerJson(respuesta) {
  const datos = await respuesta.json().catch(() => ({}))
  if (!respuesta.ok) throw new Error(datos.error || `Error del servidor: ${respuesta.status}`)
  return datos
}

function ElementoEntidad({ nombre, contenido }) {
  const valores = Array.isArray(contenido) ? contenido : (contenido == null ? [] : [contenido])
  return (
    <div className="pnl-entity-group">
      <h4>{ETIQUETAS_ENTIDADES[nombre] || nombre.replaceAll('_', ' ')}</h4>
      {valores.length ? (
        <div className="pnl-entity-list">
          {valores.map((valor, i) => (
            <span className="pnl-entity-chip" key={i}>
              {typeof valor === 'object' ? JSON.stringify(valor) : String(valor)}
            </span>
          ))}
        </div>
      ) : <p>No se identificaron elementos.</p>}
    </div>
  )
}

export default function PnlPage({ onAnalisisGuardado }) {
  const [texto, setTexto] = useState('')
  const [procesando, setProcesando] = useState(false)
  const [error, setError] = useState('')
  const [resultado, setResultado] = useState(null)
  const [historial, setHistorial] = useState([])
  const [errorHistorial, setErrorHistorial] = useState('')
  const [recuperando, setRecuperando] = useState(false)
  const [descargando, setDescargando] = useState(false)
  const resultadosRef = useRef(null)

  const cargarHistorial = useCallback(async () => {
    try {
      const datos = await obtenerJson(await fetch('/api/pnl/historial/'))
      setHistorial(datos.analisis ?? [])
      setErrorHistorial('')
    } catch (err) { setErrorHistorial(err.message || 'No se pudo cargar el historial.') }
  }, [])

  useEffect(() => { cargarHistorial() }, [cargarHistorial])

  function mostrarResultado(datos) {
    setResultado(datos)
    setError('')
    requestAnimationFrame(() => resultadosRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  async function analizar(evento) {
    evento.preventDefault()
    if (procesando) return
    const reporte = texto.trim()
    if (reporte.length < 3 || reporte.length > MAX_CARACTERES) {
      setError(`Escribe un reporte de entre 3 y ${MAX_CARACTERES.toLocaleString('es-MX')} caracteres.`)
      return
    }
    setProcesando(true)
    setError('')
    try {
      const { csrfToken } = await obtenerJson(await fetch('/api/csrf/', { credentials: 'same-origin' }))
      const datos = await obtenerJson(await fetch('/api/pnl/analizar/', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ texto: reporte }),
      }))
      if (!datos.analisis_id || !datos.categoria) throw new Error('El servidor no devolvió el análisis guardado.')
      mostrarResultado(datos)
      setTexto('') // Limpiar únicamente después de guardar el análisis correctamente.
      await cargarHistorial()
      onAnalisisGuardado?.()
    } catch (err) { setError(err.message || 'No se pudo analizar el reporte.') }
    finally { setProcesando(false) }
  }

  async function recuperar(id) {
    if (recuperando) return
    setRecuperando(true)
    setError('')
    try {
      const datos = await obtenerJson(await fetch(`/api/pnl/analisis/${encodeURIComponent(id)}/`))
      // Consultar el historial no sobrescribe el reporte que el usuario esté redactando.
      mostrarResultado(datos)
    } catch (err) { setError(err.message || 'No se pudo recuperar el reporte.') }
    finally { setRecuperando(false) }
  }

  async function descargar() {
    if (!resultado?.analisis_id || descargando) return
    setDescargando(true)
    setError('')
    try {
      const respuesta = await fetch(`/api/pnl/analisis/${encodeURIComponent(resultado.analisis_id)}/descargar/`)
      if (!respuesta.ok) {
        const datos = await respuesta.json().catch(() => ({}))
        throw new Error(datos.error || 'No se pudo descargar el reporte.')
      }
      const url = URL.createObjectURL(await respuesta.blob())
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = `failnet_pnl_${resultado.analisis_id}.txt`
      document.body.appendChild(enlace)
      enlace.click()
      enlace.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) { setError(err.message || 'No se pudo descargar el reporte.') }
    finally { setDescargando(false) }
  }

  const categoria = resultado ? CATEGORIAS[resultado.categoria] : null
  const entidades = resultado?.entidades && typeof resultado.entidades === 'object' ? resultado.entidades : {}

  return (
    <div className="pnl-page">
      <section className="pnl-intro">
        <span className="pnl-eyebrow">ANÁLISIS / PNL</span>
        <h1>Análisis de reportes de red</h1>
        <p>Clasifica un incidente, identifica elementos de red y extrae la información más relevante de su descripción.</p>
      </section>

      <form className="pnl-card" onSubmit={analizar}>
        <div className="pnl-card-head">
          <div><h2>Reporte de entrada</h2><p>Describe un problema de red o pega un reporte técnico para analizarlo.</p></div>
          <span className="pnl-chip">Análisis inteligente de texto</span>
        </div>
        <label className="pnl-label" htmlFor="pnl-reporte">Descripción del incidente</label>
        <textarea id="pnl-reporte" className="pnl-textarea" rows={9}
          maxLength={MAX_CARACTERES} value={texto} disabled={procesando}
          onChange={evento => { setTexto(evento.target.value); setError(''); setResultado(null) }}
          placeholder="Ejemplo: El router R3 dejó de responder al ping hacia 192.168.1.10. La interfaz GigabitEthernet0/1 presenta errores y el personal de redes investiga el incidente."
          spellCheck="true" />
        {error && <p className="pnl-error" role="alert">{error}</p>}
        <div className="pnl-form-footer">
          <span>{texto.length.toLocaleString('es-MX')} / {MAX_CARACTERES.toLocaleString('es-MX')} caracteres</span>
          <button type="submit" disabled={procesando} aria-busy={procesando}
            className={`sofi-run-button ${procesando ? 'is-loading' : ''} ${resultado ? 'is-success' : ''}`}>
            <span>{procesando ? 'Analizando reporte…' : resultado ? 'Ejecutar otro análisis' : 'Ejecutar análisis PNL'}</span>
            {procesando ? <span className="sofi-run-spinner" aria-hidden="true" /> :
              <svg className="sofi-run-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6" /></svg>}
          </button>
        </div>
      </form>

      {resultado && (
        <section className="pnl-results" ref={resultadosRef} aria-live="polite">
          <div className="pnl-results-top">
            <div><span className="pnl-eyebrow">RESULTADOS / PNL</span><h2>Análisis completado</h2></div>
            <button type="button" className="pnl-download" disabled={descargando} onClick={descargar}>
              {descargando ? 'Preparando descarga…' : 'Descargar reporte TXT'}
            </button>
          </div>
          {resultado.advertencia && <p className="pnl-warning" role="status">{resultado.advertencia}</p>}
          <div className="pnl-result-grid">
            <article className="pnl-card pnl-category">
              <span className="pnl-field-label">CATEGORÍA DETECTADA</span>
              <strong>{categoria?.titulo || resultado.categoria}</strong>
              <p>{categoria?.descripcion || 'Clasificación del modelo PNL.'}</p>
            </article>
            <article className="pnl-card pnl-summary">
              <span className="pnl-field-label">RESUMEN EXTRACTIVO</span>
              <p>{resultado.resumen || 'No se obtuvo un resumen.'}</p>
            </article>
          </div>
          <section className="pnl-card">
            <div className="pnl-card-head"><div><h3>Entidades identificadas</h3><p>Elementos detectados en el texto original.</p></div></div>
            <div className="pnl-entities">
              {Object.entries(entidades).length ? Object.entries(entidades).map(([nombre, contenido]) =>
                <ElementoEntidad nombre={nombre} contenido={contenido} key={nombre} />
              ) : <p>No se identificaron entidades en el reporte.</p>}
            </div>
          </section>
          <section className="pnl-card">
            <div className="pnl-card-head"><div><h3>Reporte original</h3><p>Texto utilizado para el análisis.</p></div></div>
            <p className="pnl-original">{resultado.reporte_original}</p>
          </section>
        </section>
      )}

      <section className="pnl-card pnl-history">
        <div className="pnl-card-head"><div><h3>Historial de PNL</h3><p>Explora tus reportes anteriores y recupera sus resultados.</p></div></div>
        {errorHistorial && <p className="pnl-error" role="alert">{errorHistorial}</p>}
        {!errorHistorial && historial.length === 0 && <p className="pnl-empty">Todavía no hay análisis guardados.</p>}
        <div className="pnl-history-list">
          {historial.map(item => (
            <article className="pnl-history-item" key={item.analisis_id}>
              <div className="pnl-history-text">
                <strong>{fecha(item.fecha_creacion)} · {CATEGORIAS[item.categoria]?.titulo || item.categoria}</strong>
                <p>{item.vista_previa || 'Sin vista previa.'}</p>
              </div>
              <button type="button" disabled={recuperando} onClick={() => recuperar(item.analisis_id)}>Ver resultados</button>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
