import { useCallback, useEffect, useRef, useState } from 'react'

const LIMITE = 120 * 1024 * 1024
const NIVELES = [
  { id: 0, texto: 'Menos de 10 Mbps' },
  { id: 1, texto: '10 a menos de 40 Mbps' },
  { id: 2, texto: '40 a menos de 70 Mbps' },
  { id: 3, texto: '70 a menos de 90 Mbps' },
  { id: 4, texto: '90 Mbps o más' },
]
const numero = n => Number(n ?? 0).toLocaleString('es-MX')
const pct = n => `${Number(n ?? 0).toFixed(2)}%`
const fecha = s => new Date(s).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })

function errorArchivo(file) {
  if (!file) return 'Selecciona un CSV para analizar.'
  if (!file.name.toLowerCase().endsWith('.csv')) return 'El archivo debe tener extensión CSV.'
  if (!file.size) return 'El archivo está vacío.'
  if (file.size > LIMITE) return 'El archivo supera el límite de 120 MiB.'
  return ''
}

async function jsonSeguro(res) {
  const datos = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(datos.error || `Error HTTP ${res.status}`)
  return datos
}

function Nivel({ id }) {
  return <span className={`twin-level twin-level-${id}`}>Nivel {id}</span>
}

function Distribucion({ elementos }) {
  const maximo = Math.max(1, ...elementos.map(x => x.registros))
  return (
    <section className="twin-card">
      <div className="twin-card-head"><div><h3>Distribución de tráfico</h3><p>Registros clasificados por nivel de intensidad</p></div></div>
      <div className="twin-distribution">
        {elementos.map(x => (
          <div className="twin-distribution-row" key={x.nivel}>
            <div className="twin-distribution-label"><Nivel id={x.nivel} /><span>{x.rango}</span></div>
            <div className="twin-distribution-track"><div className={`twin-bar twin-bg-${x.nivel}`} style={{ width: `${100 * x.registros / maximo}%` }} /></div>
            <div className="twin-distribution-value"><strong>{numero(x.registros)}</strong><small>{pct(x.porcentaje)}</small></div>
          </div>
        ))}
      </div>
    </section>
  )
}

function DistribucionRouters({ routers }) {
  return (
    <section className="twin-card">
      <div className="twin-card-head"><div><h3>Distribución por router</h3><p>Participación de cada nivel en los registros del equipo</p></div></div>
      <div className="twin-router-list">
        {routers.map(r => (
          <div className="twin-router-row" key={r.router}>
            <div className="twin-router-meta"><strong>{r.router}</strong><span>{numero(r.total)} registros</span></div>
            <div className="twin-stacked" role="img" aria-label={`${r.router}: ${NIVELES.map(x => `nivel ${x.id}: ${r.niveles[String(x.id)] ?? 0}`).join(', ')}`}>
              {NIVELES.map(x => (
                <div key={x.id} title={`Nivel ${x.id}: ${numero(r.niveles[String(x.id)])}`} className={`twin-bg-${x.id}`}
                  style={{ width: `${r.total ? Number(r.niveles[String(x.id)] ?? 0) * 100 / r.total : 0}%` }} />
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="twin-legend">{NIVELES.map(x => <span key={x.id}><i className={`twin-bg-${x.id}`} /> Nivel {x.id}</span>)}</div>
    </section>
  )
}

function Evolucion({ dias }) {
  if (!dias.length) return null
  return (
    <section className="twin-card">
      <div className="twin-card-head"><div><h3>Intensidad por fecha</h3><p>Distribución diaria de las cinco categorías</p></div><span className="twin-subtle">{numero(dias.length)} días</span></div>
      <div className="twin-days-scroll">
        <div className="twin-days" style={{ minWidth: `${Math.max(600, dias.length * 60)}px` }}>
          {dias.map(d => (
            <div className="twin-day" key={d.fecha} title={`${d.fecha} · ${numero(d.total)} registros`}>
              <div className="twin-day-stack">
                {NIVELES.map(x => <div key={x.id} className={`twin-bg-${x.id}`} style={{ height: `${d.total ? Number(d.niveles[String(x.id)] ?? 0) * 100 / d.total : 0}%` }} />)}
              </div>
              <span>{d.fecha.slice(5)}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="twin-chart-note">Cada columna representa el 100 % de los registros de ese día. Desplaza horizontalmente para consultar más fechas.</p>
    </section>
  )
}

function Tabla({ analisisId }) {
  const [filtro, setFiltro] = useState('todas')
  const [pagina, setPagina] = useState(1)
  const [tamano, setTamano] = useState(25)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    if (!analisisId) return
    const controller = new AbortController()
    setDatos(null)
    setError('')
    setCargando(true)
    const parametros = new URLSearchParams({ vista: filtro, pagina: String(pagina), tamano: String(tamano) })
    fetch(`/api/twin/analisis/${encodeURIComponent(analisisId)}/predicciones/?${parametros}`, { signal: controller.signal })
      .then(jsonSeguro).then(setDatos)
      .catch(err => { if (err.name !== 'AbortError') setError(err.message) })
      .finally(() => { if (!controller.signal.aborted) setCargando(false) })
    return () => controller.abort()
  }, [analisisId, filtro, pagina, tamano])

  const total = Number(datos?.total ?? 0)
  const desde = total ? (pagina - 1) * tamano + 1 : 0
  const hasta = Math.min(pagina * tamano, total)
  return (
    <section className="twin-card">
      <div className="twin-card-head"><div><h3>Registros clasificados</h3><p>Consulta por página sin cargar el CSV completo en el navegador</p></div></div>
      <div className="twin-filter-row">
        <label htmlFor="twin-filtro">Clasificación</label>
        <select id="twin-filtro" value={filtro} onChange={e => { setFiltro(e.target.value); setPagina(1) }}>
          <option value="todas">Todos los niveles</option>
          {NIVELES.map(x => <option key={x.id} value={String(x.id)}>Nivel {x.id}: {x.texto}</option>)}
        </select>
      </div>
      <div className="twin-table-scroll" role="region" aria-label="Predicciones de Digital Twin" tabIndex="0">
        <table className="twin-table">
          <thead><tr><th>Fecha UTC</th><th>Router</th><th>Nivel</th><th>Intensidad</th><th>Puntuación del modelo</th></tr></thead>
          <tbody>
            {(datos?.filas ?? []).map((f, i) => (
              <tr key={`${f.timestamp}-${f.router}-${i}`}>
                <td>{f.fecha_utc.replace('T', ' ').replace('Z', ' UTC')}</td>
                <td><strong>{f.router}</strong></td><td><Nivel id={f.nivel} /></td>
                <td>{f.rango_trafico}</td><td>{pct(f.confianza_modelo * 100)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {cargando && <p className="twin-table-state">Consultando registros…</p>}
        {!cargando && error && <p className="twin-error" role="alert">{error}</p>}
        {!cargando && !error && datos && total === 0 && <p className="twin-table-state">No existen registros en este nivel.</p>}
      </div>
      <div className="twin-table-footer">
        <span>{numero(desde)}–{numero(hasta)} de {numero(total)} registros</span>
        <div className="twin-pager">
          <label htmlFor="twin-tamano">Filas</label>
          <select id="twin-tamano" value={tamano} onChange={e => { setTamano(Number(e.target.value)); setPagina(1) }}>
            {[25, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          <button type="button" disabled={cargando || pagina === 1} aria-label="Página anterior" onClick={() => setPagina(x => x - 1)}>‹</button>
          <span>{pagina} / {datos?.paginas ?? '…'}</span>
          <button type="button" disabled={cargando || !datos || pagina >= datos.paginas} aria-label="Página siguiente" onClick={() => setPagina(x => x + 1)}>›</button>
        </div>
      </div>
    </section>
  )
}

export default function TwinPage({ onAnalisisGuardado }) {
  const [archivo, setArchivo] = useState(null)
  const [arrastrando, setArrastrando] = useState(false)
  const [procesando, setProcesando] = useState(false)
  const [error, setError] = useState('')
  const [resultado, setResultado] = useState(null)
  const [historial, setHistorial] = useState([])
  const [descargando, setDescargando] = useState(false)
  const [consultando, setConsultando] = useState(false)
  const resultadosRef = useRef(null)
  const inputRef = useRef(null)

  const cargarHistorial = useCallback(async () => {
    try {
      const res = await fetch('/api/twin/historial/')
      const datos = await jsonSeguro(res)
      setHistorial(datos.analisis ?? [])
    } catch (err) { setError(err.message) }
  }, [])

  useEffect(() => { cargarHistorial() }, [cargarHistorial])

  useEffect(() => {
    const ignorarArchivos = e => { if (e.dataTransfer?.types?.includes('Files')) e.preventDefault() }
    window.addEventListener('dragover', ignorarArchivos)
    window.addEventListener('drop', ignorarArchivos)
    return () => { window.removeEventListener('dragover', ignorarArchivos); window.removeEventListener('drop', ignorarArchivos) }
  }, [])

  function elegirArchivo(file) {
    const mensaje = errorArchivo(file)
    if (mensaje) { setError(mensaje); return }
    setArchivo(file)
    setError('')
    setResultado(null)
  }

  function mostrarResultado(datos) {
    setResultado(datos)
    setError('')
    requestAnimationFrame(() => resultadosRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  async function ejecutar(e) {
    e.preventDefault()
    if (procesando) return
    const mensaje = errorArchivo(archivo)
    if (mensaje) { setError(mensaje); return }
    setProcesando(true)
    setError('')
    try {
      const csrf = await jsonSeguro(await fetch('/api/csrf/', { credentials: 'same-origin' }))
      const formulario = new FormData()
      formulario.append('archivo', archivo)
      const datos = await jsonSeguro(await fetch('/api/twin/analizar/', {
        method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrf.csrfToken }, body: formulario,
      }))
      if (!datos.analisis_id || !datos.resumen) throw new Error('El servidor no devolvió un análisis guardado.')
      mostrarResultado(datos)
      await cargarHistorial()
      onAnalisisGuardado?.()
    } catch (err) { setError(err.message || 'No se pudo ejecutar Digital Twin.') }
    finally { setProcesando(false) }
  }

  async function recuperar(id) {
    setConsultando(true)
    setError('')
    try {
      const datos = await jsonSeguro(await fetch(`/api/twin/analisis/${encodeURIComponent(id)}/`))
      mostrarResultado(datos)
    } catch (err) { setError(err.message) }
    finally { setConsultando(false) }
  }

  async function descargar() {
    if (!resultado?.analisis_id || descargando) return
    setDescargando(true)
    setError('')
    try {
      const res = await fetch(`/api/twin/analisis/${encodeURIComponent(resultado.analisis_id)}/descargar/`)
      if (!res.ok) { await jsonSeguro(res); throw new Error('No se pudo descargar el resultado.') }
      const blob = await res.blob()
      const enlace = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = enlace
      a.download = `failnet_twin_${resultado.analisis_id}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      setTimeout(() => URL.revokeObjectURL(enlace), 1000)
    } catch (err) { setError(err.message) }
    finally { setDescargando(false) }
  }

  const resumen = resultado?.resumen
  const niveles = resumen?.niveles ?? []
  const elevado = niveles.filter(x => Number(x.nivel) === 4).reduce((a, x) => a + Number(x.registros), 0)

  return (
    <div className="twin-page">
      <header className="twin-intro">
        <span className="twin-eyebrow">ANÁLISIS / DIGITAL TWIN</span>
        <h1>Intensidad del tráfico</h1>
        <p>Clasifica registros de monitoreo en cinco niveles de tráfico y explora los resultados por router y fecha.</p>
      </header>

      <form className="twin-card twin-upload" onSubmit={ejecutar}>
        <div className="twin-card-head"><div><h2>Archivo de entrada</h2><p>Un CSV compatible con las 67 características del modelo. No se utiliza la etiqueta LABEL para predecir.</p></div><span className="twin-chip">Clasificación automática</span></div>
        <div className={`twin-drop ${arrastrando ? 'is-dragging' : ''}`} onDragOver={e => { e.preventDefault(); if (!procesando) setArrastrando(true) }}
          onDragLeave={e => { e.preventDefault(); if (!e.currentTarget.contains(e.relatedTarget)) setArrastrando(false) }}
          onDrop={e => { e.preventDefault(); setArrastrando(false); if (!procesando) elegirArchivo(e.dataTransfer.files[0]) }}>
          <div className="twin-drop-symbol" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 16V3m0 0L7 8m5-5 5 5" />
              <path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" />
            </svg>
          </div>
          <strong>{arrastrando ? 'Suelta el archivo CSV aquí' : archivo ? archivo.name : 'Arrastra tu archivo CSV aquí'}</strong>
          <span>{archivo ? `${(archivo.size / 1024 / 1024).toFixed(2)} MiB · Listo para analizar` : 'O selecciona un archivo desde tu computadora'}</span>
          <button type="button" className="twin-select" disabled={procesando} onClick={() => inputRef.current?.click()}>Seleccionar CSV</button>
          <input ref={inputRef} type="file" accept=".csv,text/csv" onChange={e => { if (e.target.files?.[0]) elegirArchivo(e.target.files[0]); e.target.value = '' }} hidden />
        </div>
        {error && <p className="twin-error" role="alert">{error}</p>}
        <div className="twin-upload-footer"><span>1 archivo CSV · Máximo 120 MiB</span>
          <button
            type="submit"
            disabled={procesando}
            aria-busy={procesando}
            className={`sofi-run-button ${procesando ? 'is-loading' : ''} ${resultado ? 'is-success' : ''}`}
          >
            <span>{procesando ? 'Analizando archivo…' : resultado ? 'Ejecutar otro análisis' : 'Ejecutar análisis Digital Twin'}</span>
            {procesando ? (
              <span className="sofi-run-spinner" aria-hidden="true" />
            ) : (
              <svg className="sofi-run-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 12h16m-6-6 6 6-6 6" />
              </svg>
            )}
          </button>
        </div>
        {procesando && <p className="twin-processing" role="status">El modelo está procesando el CSV. No cierres ni recargues esta página hasta terminar.</p>}
      </form>

      {resultado && <section ref={resultadosRef} className="twin-results" aria-live="polite">
        <div className="twin-results-head"><div><span className="twin-eyebrow">RESULTADOS / DIGITAL TWIN</span><h2>Análisis completado</h2></div><button type="button" className="twin-download" onClick={descargar} disabled={descargando}>{descargando ? 'Preparando archivo…' : '↓ Descargar CSV completo'}</button></div>
        {resultado.advertencia && <p className="twin-warning" role="status">{resultado.advertencia}</p>}
        <div className="twin-stats">
          <div className="twin-stat"><span>Registros procesados</span><strong>{numero(resumen.total_registros)}</strong><small>Predicciones generadas</small></div>
          <div className="twin-stat"><span>Routers analizados</span><strong>{numero(resumen.total_routers)}</strong><small>Equipos identificados</small></div>
          <div className="twin-stat twin-stat-accent"><span>Tráfico nivel 4</span><strong>{numero(elevado)}</strong><small>{pct(resumen.total_registros ? elevado * 100 / resumen.total_registros : 0)} del total</small></div>
        </div>
        <Distribucion elementos={niveles} />
        <DistribucionRouters routers={resultado.routers ?? []} />
        <Evolucion dias={resultado.distribucion_diaria ?? []} />
        <Tabla key={resultado.analisis_id} analisisId={resultado.analisis_id} />
      </section>}

      <section className="twin-card twin-history">
        <div className="twin-card-head"><div><h3>Historial de Digital Twin</h3><p>Consulta análisis guardados en MongoDB Atlas</p></div></div>
        {historial.length === 0 ? <p className="twin-empty">Todavía no hay análisis guardados.</p> : (
          <div className="twin-history-list">{historial.map(item => (
            <div className="twin-history-row" key={item.analisis_id}>
              <div><strong>{fecha(item.fecha_creacion)}</strong><span>{item.nombre_archivo} · {numero(item.resumen?.total_registros)} registros</span></div>
              <button type="button" disabled={consultando || procesando} onClick={() => recuperar(item.analisis_id)}>Ver resultados</button>
            </div>
          ))}</div>
        )}
      </section>
    </div>
  )
}
