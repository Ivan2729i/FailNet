import { useCallback, useEffect, useRef, useState } from 'react'

const MAX_CSV_BYTES = 25 * 1024 * 1024
const formatoNumero = (numero) => Number(numero ?? 0).toLocaleString('es-MX')
const formatoPorcentaje = (numero) => `${Number(numero ?? 0).toFixed(2)}%`

function validarCsv(archivo) {
  if (!archivo) return 'No se recibió ningún archivo.'
  if (!archivo.name.toLowerCase().endsWith('.csv')) return 'Selecciona un archivo con extensión .csv.'
  if (archivo.size === 0) return 'El archivo CSV está vacío.'
  if (archivo.size > MAX_CSV_BYTES) return 'El archivo supera el máximo de 25 MiB.'
  return null
}

function ZonaCargaCsv({ id, titulo, archivo, deshabilitado, alSeleccionar, alError }) {
  const inputRef = useRef(null)
  const profundidad = useRef(0)
  const [arrastrando, setArrastrando] = useState(false)

  function aplicarArchivo(nuevoArchivo) {
    const mensaje = validarCsv(nuevoArchivo)
    if (mensaje) {
      alError(`${titulo}: ${mensaje}`)
      return
    }
    alSeleccionar(nuevoArchivo)
  }

  function manejarEntrada(evento) {
    if (deshabilitado || !evento.dataTransfer?.types?.includes('Files')) return
    evento.preventDefault()
    profundidad.current += 1
    setArrastrando(true)
  }

  function manejarSalida(evento) {
    evento.preventDefault()
    profundidad.current = Math.max(0, profundidad.current - 1)
    if (profundidad.current === 0) setArrastrando(false)
  }

  function manejarArrastre(evento) {
    if (!evento.dataTransfer?.types?.includes('Files')) return
    evento.preventDefault()
    evento.dataTransfer.dropEffect = deshabilitado ? 'none' : 'copy'
  }

  function manejarSoltar(evento) {
    evento.preventDefault()
    profundidad.current = 0
    setArrastrando(false)
    if (deshabilitado) return

    const archivos = Array.from(evento.dataTransfer?.files ?? [])
    if (archivos.length !== 1) {
      alError(`${titulo}: arrastra un solo archivo CSV a este recuadro.`)
      return
    }
    aplicarArchivo(archivos[0])
  }

  return (
    <div
      className={`sofi-dropzone ${arrastrando ? 'is-over' : ''} ${archivo ? 'has-file' : ''} ${deshabilitado ? 'is-disabled' : ''}`}
      onDragEnter={manejarEntrada}
      onDragOver={manejarArrastre}
      onDragLeave={manejarSalida}
      onDrop={manejarSoltar}
      role="group"
      aria-label={`Cargar CSV de ${titulo}`}
    >
      <div className="sofi-dropzone-head">
        <span className="sofi-dropzone-title">{titulo}</span>
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 16V3m0 0L7 8m5-5 5 5" />
          <path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" />
        </svg>
      </div>
      <p className="sofi-dropzone-help">
        {arrastrando ? 'Suelta el CSV aquí' : archivo ? 'Archivo listo para analizar' : 'Arrastra un archivo CSV aquí o selecciónalo'}
      </p>
      <div className="sofi-dropzone-actions">
        <input
          ref={inputRef}
          id={id}
          type="file"
          accept=".csv,text/csv"
          className="sofi-file-input"
          disabled={deshabilitado}
          onChange={(evento) => {
            const seleccionado = evento.target.files?.[0]
            if (seleccionado) aplicarArchivo(seleccionado)
            evento.target.value = '' // Permite seleccionar de nuevo el mismo archivo.
          }}
        />
        <button
          type="button"
          className="sofi-file-button"
          onClick={() => inputRef.current?.click()}
          disabled={deshabilitado}
        >
          {archivo ? 'Cambiar archivo' : 'Seleccionar archivo'}
        </button>
        <span className="sofi-file-name" aria-live="polite" title={archivo?.name || ''}>
          {archivo ? `${archivo.name} · ${(archivo.size / (1024 * 1024)).toFixed(2)} MiB` : 'Sin archivos seleccionados'}
        </span>
      </div>
      {arrastrando && <span className="sofi-dropzone-overlay" aria-hidden="true">SOLTAR ARCHIVO</span>}
    </div>
  )
}

function TarjetaMetrica({ titulo, valor, descripcion, destacada = false }) {
  return (
    <article className={`rounded-xl border p-5 sm:p-6 ${destacada ? 'border-[#233c68] bg-[var(--forest)] text-white' : 'border-[var(--border)] bg-white text-[var(--ink)]'}`}>
      <p className={`text-[11px] font-bold uppercase tracking-[.12em] ${destacada ? 'text-sky-200' : 'text-slate-500'}`}>{titulo}</p>
      <p className={`mt-5 text-4xl font-bold tracking-tight tabular-nums ${destacada ? 'text-[var(--lime)]' : 'text-[var(--ink)]'}`}>{valor}</p>
      <p className={`mt-2 text-xs ${destacada ? 'text-slate-300' : 'text-slate-500'}`}>{descripcion}</p>
    </article>
  )
}


function GraficaDiaria({ dias }) {
  const maximo = Math.max(1, ...dias.map(dia => dia.fallas))
  const marcas = Array.from({ length: 5 }, (_, i) => Math.round(maximo * (4 - i) / 4))
  const ancho = Math.max(720, dias.length * 47)
  const fechas = dias.map(d => new Date(`${d.fecha}T12:00:00Z`))
  const etiqueta = fecha => new Intl.DateTimeFormat('es-MX', { day: '2-digit', month: 'short', timeZone: 'UTC' }).format(fecha)

  return (
    <section className="sofi-chart-card" aria-label="Detecciones de falla por fecha">
      <div className="sofi-card-head">
        <div>
          <h3>Detecciones de falla por día</h3>
          <p>Registros clasificados como falla en cada fecha</p>
        </div>
        <span className="sofi-chart-count">{formatoNumero(dias.length)} días</span>
      </div>
      <div className="sofi-chart-scroll" tabIndex={0} aria-label="Gráfica desplazable horizontalmente">
        <div className="sofi-chart-grid" style={{ minWidth: ancho }}>
          <div className="sofi-chart-axis">
            {marcas.map((v, i) => <span key={i}>{v}</span>)}
          </div>
          <div className="sofi-chart-body">
            <div className="sofi-chart-lines">
              {marcas.map((_, i) => <span key={i} />)}
            </div>
            <div className="sofi-chart-bars">
              {dias.map((dia, i) => (
                <div className="sofi-chart-column" key={dia.fecha}>
                  <div className="sofi-chart-bar-wrap" title={`${dia.fecha}: ${dia.fallas} detecciones de ${dia.total} registros`}>
                    <div className="sofi-chart-bar" style={{ height: `${dia.fallas / maximo * 100}%` }} />
                    <div className="sofi-chart-tooltip">{dia.fallas} fallas · {dia.fecha}</div>
                  </div>
                  <span className="sofi-chart-date">{i % 3 === 0 || i === dias.length - 1 ? etiqueta(fechas[i]) : ''}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function TablaPredicciones({ datos, cargando, error, vista, cambiarVista, pagina, cambiarPagina, tamano, cambiarTamano }) {
  const total = datos?.total ?? 0
  const paginas = datos?.paginas ?? 1
  const desde = total ? (pagina - 1) * tamano + 1 : 0
  const hasta = total ? Math.min(pagina * tamano, total) : 0
  const opciones = [
    { id: 'todas', texto: 'Todas' },
    { id: 'fallas', texto: 'Fallas' },
    { id: 'normales', texto: 'Normales' },
  ]
  return (
    <section className="sofi-table-card">
      <div className="sofi-table-head">
        <div>
          <h3>Predicciones</h3>
          <p>Consulta las mediciones y sus probabilidades de falla</p>
        </div>
        <div className="sofi-filter-list" role="group" aria-label="Filtrar predicciones">
          {opciones.map(op => (
            <button key={op.id} type="button" aria-pressed={vista === op.id} className={vista === op.id ? 'is-active' : ''}
              onClick={() => cambiarVista(op.id)}>{op.texto}</button>
          ))}
        </div>
      </div>
      <div className="sofi-table-scroll" role="region" aria-label="Tabla de predicciones desplazable" tabIndex={0}>
        <table className="sofi-result-table">
          <thead><tr><th>Fecha UTC</th><th>Timestamp</th><th>Probabilidad de falla</th><th>Clasificación</th></tr></thead>
          <tbody>
            {(datos?.filas ?? []).map(fila => (
              <tr key={fila.timestamp}>
                <td>{String(fila.fecha_utc).replace('T', ' ').slice(0, 19)}</td>
                <td className="sofi-tabular-muted">{fila.timestamp}</td>
                <td className="sofi-tabular-muted">{formatoPorcentaje(fila.probabilidad_falla * 100)}</td>
                <td><span className={`sofi-class-badge ${fila.prediccion === 1 ? 'is-failure' : 'is-normal'}`}>{fila.clasificacion}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {cargando && <p className="sofi-table-feedback">Cargando registros…</p>}
        {error && <p role="alert" className="sofi-table-error">{error}</p>}
        {!cargando && !error && total === 0 && <p className="sofi-table-feedback">No hay registros para este filtro.</p>}
      </div>
      <div className="sofi-table-footer">
        <span>{formatoNumero(desde)}–{formatoNumero(hasta)} de {formatoNumero(total)} registros</span>
        <div className="sofi-paging-controls">
          <label htmlFor="sofi-tamano">Filas</label>
          <select id="sofi-tamano" value={tamano} onChange={e => cambiarTamano(Number(e.target.value))} disabled={cargando}>
            {[25, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          <button type="button" disabled={pagina <= 1 || cargando} onClick={() => cambiarPagina(pagina - 1)} aria-label="Página anterior">‹</button>
          <span className="sofi-page-count">{pagina} / {paginas}</span>
          <button type="button" disabled={pagina >= paginas || cargando} onClick={() => cambiarPagina(pagina + 1)} aria-label="Página siguiente">›</button>
        </div>
      </div>
    </section>
  )
}

export default function SofiPage({ onAnalisisGuardado }) {
  const [switchI, setSwitchI] = useState(null)
  const [switchII, setSwitchII] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [resultado, setResultado] = useState(null)
  const [vistaTabla, setVistaTabla] = useState('todas')
  const [pagina, setPagina] = useState(1)
  const [tamano, setTamano] = useState(25)
  const [paginaDatos, setPaginaDatos] = useState(null)
  const [cargandoPagina, setCargandoPagina] = useState(false)
  const [errorPagina, setErrorPagina] = useState('')
  const [historial, setHistorial] = useState([])
  const [descargando, setDescargando] = useState(false)
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const resultadosRef = useRef(null)

  useEffect(() => {
    const evitarAbrirCsv = evento => {
      if (evento.dataTransfer?.types?.includes('Files')) evento.preventDefault()
    }
    window.addEventListener('dragover', evitarAbrirCsv)
    window.addEventListener('drop', evitarAbrirCsv)
    return () => {
      window.removeEventListener('dragover', evitarAbrirCsv)
      window.removeEventListener('drop', evitarAbrirCsv)
    }
  }, [])

  const cargarHistorial = useCallback(async () => {
    try {
      const respuesta = await fetch('/api/sofi/historial/')
      if (!respuesta.ok) throw new Error('Error de historial')
      const json = await respuesta.json()
      setHistorial(json.analisis ?? [])
    } catch { setHistorial([]) }
  }, [])

  useEffect(() => { cargarHistorial() }, [cargarHistorial])

  // Pedimos solamente la página visible. No cargamos miles de filas al navegador.
  useEffect(() => {
    const id = resultado?.analisis_id
    if (!id) return
    const abortar = new AbortController()
    setCargandoPagina(true)
    setErrorPagina('')
    setPaginaDatos(null)
    const params = new URLSearchParams({ vista: vistaTabla, pagina: String(pagina), tamano: String(tamano) })
    fetch(`/api/sofi/analisis/${encodeURIComponent(id)}/predicciones/?${params}`, { signal: abortar.signal })
      .then(async res => {
        const json = await res.json()
        if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`)
        return json
      })
      .then(setPaginaDatos)
      .catch(err => { if (err.name !== 'AbortError') setErrorPagina(err.message) })
      .finally(() => { if (!abortar.signal.aborted) setCargandoPagina(false) })
    return () => abortar.abort()
  }, [resultado?.analisis_id, vistaTabla, pagina, tamano])

  function actualizarArchivo(numero, archivo) {
    if (numero === 1) setSwitchI(archivo)
    else setSwitchII(archivo)
    setError('')
    setResultado(null)
    setPaginaDatos(null)
  }

  function aplicarResultado(datos) {
    setResultado(datos)
    setPagina(1)
    setVistaTabla('todas')
    setError('')
    requestAnimationFrame(() => resultadosRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  async function ejecutarAnalisis(evento) {
    evento.preventDefault()
    if (cargando) return
    setError('')
    if (!switchI || !switchII) {
      setError('Selecciona ambos CSV antes de ejecutar el análisis.')
      return
    }
    const mensaje = validarCsv(switchI) || validarCsv(switchII)
    if (mensaje) { setError(mensaje); return }

    setCargando(true)
    try {
      const csrf = await fetch('/api/csrf/', { credentials: 'same-origin' })
      if (!csrf.ok) throw new Error('No se pudo obtener el token de seguridad.')
      const { csrfToken } = await csrf.json()
      const formulario = new FormData()
      formulario.append('switch_i', switchI)
      formulario.append('switch_ii', switchII)
      const respuesta = await fetch('/api/sofi/analizar/', {
        method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken }, body: formulario,
      })
      const datos = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) throw new Error(datos.error || `Error del servidor: ${respuesta.status}`)
      if (!datos.analisis_id || !datos.resumen) throw new Error('El análisis no se pudo guardar correctamente.')
      aplicarResultado(datos)
      await cargarHistorial()
      onAnalisisGuardado?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo ejecutar el análisis.')
    } finally { setCargando(false) }
  }

  async function recuperarAnalisis(id) {
    setCargandoHistorial(true)
    setError('')
    try {
      const respuesta = await fetch(`/api/sofi/analisis/${encodeURIComponent(id)}/`)
      const datos = await respuesta.json()
      if (!respuesta.ok) throw new Error(datos.error || 'No se pudo recuperar el análisis.')
      aplicarResultado(datos)
    } catch (err) { setError(err.message) }
    finally { setCargandoHistorial(false) }
  }

  async function descargarCsv() {
    if (!resultado?.analisis_id || descargando) return
    setDescargando(true)
    setError('')
    try {
      const res = await fetch(`/api/sofi/analisis/${encodeURIComponent(resultado.analisis_id)}/descargar/`)
      if (!res.ok) {
        const datos = await res.json().catch(() => ({}))
        throw new Error(datos.error || 'No se pudo descargar el CSV.')
      }
      const blob = await res.blob()
      const direccion = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = direccion
      a.download = `failnet_sofi_${resultado.analisis_id}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      setTimeout(() => URL.revokeObjectURL(direccion), 1000)
    } catch (err) { setError(err.message) }
    finally { setDescargando(false) }
  }

  const resumen = resultado?.resumen
  return (
    <div className="space-y-8 pb-8">
      <section className="border-b border-[var(--border)] pb-7">
        <span className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#0369a1]">ANÁLISIS / SOFI</span>
        <h1 className="mt-3 text-4xl font-bold tracking-tight text-[var(--ink)] sm:text-5xl">Detección de fallas</h1>
        <p className="mt-4 max-w-2xl text-[13px] leading-7 text-[var(--muted)]">Analiza registros de switches y consulta las predicciones de posibles fallas en la red.</p>
      </section>

      <form onSubmit={ejecutarAnalisis} className="rounded-xl border border-[var(--border)] bg-white p-5 sm:p-7">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-[var(--ink)]">Archivos de entrada</h2>
            <p className="mt-1 text-xs leading-6 text-slate-500">Carga los CSV de CoreSwitch-I y CoreSwitch-II. Se sincronizan por timestamp.</p>
          </div>
          <span className="rounded-md bg-[#e0f2fe] px-3 py-2 text-[11px] font-semibold text-[#075985]">Clasificación automática</span>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <ZonaCargaCsv id="sofi-i" titulo="CoreSwitch-I" archivo={switchI} deshabilitado={cargando}
            alSeleccionar={archivo => actualizarArchivo(1, archivo)} alError={setError} />
          <ZonaCargaCsv id="sofi-ii" titulo="CoreSwitch-II" archivo={switchII} deshabilitado={cargando}
            alSeleccionar={archivo => actualizarArchivo(2, archivo)} alError={setError} />
        </div>
        {error && <p role="alert" className="sofi-main-error">{error}</p>}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] pt-5">
          <p className="text-[11px] text-slate-500">2 archivos CSV · Hasta 25 MiB cada uno</p>
          <button type="submit" disabled={cargando} aria-busy={cargando}
            className={`sofi-run-button ${cargando ? 'is-loading' : ''} ${resultado ? 'is-success' : ''}`}>
            <span>{cargando ? 'Analizando archivos…' : resultado ? 'Ejecutar otro análisis' : 'Ejecutar análisis SOFI'}</span>
            {cargando ? <span className="sofi-run-spinner" aria-hidden="true" /> :
              <svg className="sofi-run-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6" /></svg>}
          </button>
        </div>
      </form>

      {resultado && (
        <section className="space-y-7" ref={resultadosRef} aria-live="polite">
          <div className="sofi-results-top">
            <div>
              <span className="text-[10px] font-extrabold uppercase tracking-[.15em] text-[#0369a1]">Resultados / SOFI</span>
              <h2 className="mt-2 text-2xl font-bold text-[var(--ink)]">Análisis completado</h2>
            </div>
            <button type="button" className="sofi-download-button" onClick={descargarCsv} disabled={descargando}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4" /></svg>
              {descargando ? 'Preparando descarga…' : 'Descargar CSV completo'}
            </button>
          </div>
          {resultado.advertencia && <p className="sofi-warning" role="status">{resultado.advertencia}</p>}
          <div className="grid gap-4 md:grid-cols-3">
            <TarjetaMetrica titulo="Registros sincronizados" valor={formatoNumero(resumen.registros_sincronizados)} descripcion="Mediciones analizadas" />
            <TarjetaMetrica titulo="Clasificados normales" valor={formatoNumero(resumen.normales)} descripcion={`${formatoPorcentaje(resumen.porcentaje_normales)} del total`} />
            <TarjetaMetrica titulo="Predicciones de falla" valor={formatoNumero(resumen.fallas)} descripcion={`${formatoPorcentaje(resumen.porcentaje_fallas)} del total`} destacada />
          </div>
          <GraficaDiaria dias={resultado.distribucion_diaria ?? []} />
          <TablaPredicciones datos={paginaDatos} cargando={cargandoPagina} error={errorPagina}
            vista={vistaTabla} cambiarVista={valor => { setVistaTabla(valor); setPagina(1) }}
            pagina={pagina} cambiarPagina={setPagina} tamano={tamano} cambiarTamano={valor => { setTamano(valor); setPagina(1) }} />
        </section>
      )}

      <section className="sofi-history">
        <div className="sofi-card-head"><div><h3>Historial de SOFI</h3><p>Recupera análisis anteriores sin volver a subir los CSV</p></div></div>
        {historial.length === 0 ? <p className="sofi-history-empty">Todavía no hay análisis guardados.</p> : (
          <div className="sofi-history-list">
            {historial.map(item => (
              <div className="sofi-history-item" key={item.analisis_id}>
                <div>
                  <strong>{new Date(item.fecha_creacion).toLocaleString('es-MX')}</strong>
                  <span>{formatoNumero(item.resumen?.registros_sincronizados)} registros · {formatoNumero(item.resumen?.fallas)} fallas predichas</span>
                </div>
                <button type="button" disabled={cargandoHistorial} onClick={() => recuperarAnalisis(item.analisis_id)}>Ver resultados</button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
