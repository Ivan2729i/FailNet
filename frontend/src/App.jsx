import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Routes, Route, Navigate, useLocation } from 'react-router'
import SofiPage from './components/SofiPage.jsx'
import TwinPage from './components/TwinPage.jsx'
import PnlPage from './components/PnlPage.jsx'
import BlockchainPage from './components/BlockchainPage.jsx'
import './twin.css'
import './pnl.css'
import './sofi.css'
import './blockchain.css'


// Iconos SVG internos
function Icono({ tipo, size = 18, className = '' }) {
  const formas = {
    panel: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    estadisticas: <path d="M4 20V12M10 20V5M16 20V9M22 20V3" />,
    modulos: <><rect x="3" y="3" width="8" height="8" rx="1" /><rect x="13" y="3" width="8" height="8" rx="1" /><rect x="3" y="13" width="8" height="8" rx="1" /><rect x="13" y="13" width="8" height="8" rx="1" /></>,
    sofi: <><path d="M12 2 20 6v6c0 5-3.4 8.5-8 10-4.6-1.5-8-5-8-10V6l8-4Z" /><path d="m9 12 2 2 4-4" /></>,
    twin: <><circle cx="5" cy="12" r="2" /><circle cx="19" cy="5" r="2" /><circle cx="19" cy="19" r="2" /><path d="M7 11 17 6M7 13l10 5" /></>,
    pnl: <><path d="M6 2h9l4 4v16H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z" /><path d="M14 2v5h5M8 12h8M8 16h8" /></>,
    blockchain: <><rect x="3" y="4" width="7" height="7" rx="1" /><rect x="14" y="13" width="7" height="7" rx="1" /><path d="M10 7h4M14 7l3 3v3M10 17H7v-6" /></>,
    actualizar: <><path d="M20 7v5h-5M4 17v-5h5" /><path d="M5.5 9a7 7 0 0 1 12-2L20 12M4 12l2.5 5a7 7 0 0 0 12-2" /></>,
    alerta: <><path d="m12 3 10 18H2L12 3Z" /><path d="M12 9v5M12 18h.01" /></>,
    enlace: <path d="M7 17 17 7M9 7h8v8" />,
    cerrar: <path d="M5 5 19 19M19 5 5 19" />,
  }

  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
      strokeLinejoin="round" className={className} aria-hidden="true">
      {formas[tipo] ?? <circle cx="12" cy="12" r="8" />}
    </svg>
  )
}

const navegacion = [
  { id: 'resumen', nombre: 'Vista general', icono: 'panel' },
  { id: 'estadisticas', nombre: 'Estadísticas', icono: 'estadisticas' },
  { id: 'modulos', nombre: 'Módulos', icono: 'modulos' },
]

const herramientas = [
  { nombre: 'SOFI', icono: 'sofi', ruta: '/sofi', disponible: true },
  { nombre: 'Digital Twin', icono: 'twin', ruta: '/digital-twin', disponible: true },
  { nombre: 'PNL', icono: 'pnl', ruta: '/pnl', disponible: true },
  { nombre: 'Blockchain', icono: 'blockchain', ruta: '/blockchain', disponible: true },
]

const modulos = [
  { numero: '01', nombre: 'SOFI', ruta: '/sofi', tipo: 'Detección de fallas', descripcion: 'Clasificación de registros normales y eventos de falla.' },
  { numero: '02', nombre: 'Digital Twin', ruta: '/digital-twin', tipo: 'Análisis de tráfico', descripcion: 'Clasificación de cinco niveles de intensidad de tráfico.' },
  { numero: '03', nombre: 'PNL', ruta: '/pnl', tipo: 'Análisis de reportes', descripcion: 'Clasificación de texto, entidades y resumen técnico.' },
  { numero: '04', nombre: 'Blockchain', ruta: '/blockchain', tipo: 'Integridad de análisis', descripcion: 'Consulta de bloques y verificación de integridad mediante SHA-256.' },
]

function BarraLateral({
  abierta, cerrar, activa, seleccionar, rutaActual,
  arrastrando, desplazamiento, iniciarGesto, moverGesto,
  terminarGesto, cancelarGesto,
}) {
  return (
    <>
      {(abierta || arrastrando) && (
        <button
          type="button"
          className={`mobile-overlay ${arrastrando ? 'is-dragging' : ''}`}
          style={arrastrando
            ? { opacity: Math.max(0, Math.min(1, abierta
                ? (260 + desplazamiento) / 260
                : desplazamiento / 260)) }
            : undefined}
          aria-label="Cerrar navegación"
          onClick={cerrar}
        />
      )}
      <aside
        id="menu-failnet"
        className={`sidebar ${abierta ? 'sidebar-open' : ''} ${arrastrando ? 'is-dragging' : ''}`}
        style={{ '--swipe-offset': `${desplazamiento}px` }}
        aria-label="Navegación principal"
        onTouchStart={(evento) => iniciarGesto(evento, 'cerrar')}
      >
        <div className="sidebar-brand">
          {/* El logo regresa a inicio y recarga. */}
          <a href="/" className="sidebar-brand-home" aria-label="Ir al inicio de FailNet">
              <div className="brand-logo-container" aria-hidden="true">
                  <img
                    src="/images/failnet-logo.png"
                    alt=""
                    className="brand-logo"
                  />
              </div>
              <div className="brand-text">
                <strong>FAILNET</strong>
                <small>NETWORK ANALYSIS</small>
              </div>
          </a>
          <button
            type="button"
            className="sidebar-close-button"
            onClick={cerrar}
            aria-label="Cerrar menú lateral"
          >
            <Icono tipo="cerrar" size={20} />
          </button>
        </div>

        <div className="sidebar-content">
          <div className="sidebar-group">
            <p className="sidebar-heading">ESPACIO DE TRABAJO</p>
            <nav className="sidebar-links" aria-label="Secciones">
              {navegacion.map((item, index) => (
                <Link key={item.id} to={`/#${item.id}`}
                  className={`sidebar-link ${rutaActual === '/' && activa === item.id ? 'sidebar-link-active' : ''}`}
                  aria-current={rutaActual === '/' && activa === item.id ? 'location' : undefined}
                  style={{ '--nav-index': index }}
                  onClick={() => seleccionar(item.id)}>
                  <Icono tipo={item.icono} size={17} />
                  <span>{item.nombre}</span>
                </Link>
              ))}
            </nav>
          </div>

          <div className="sidebar-group">
            <p className="sidebar-heading">HERRAMIENTAS</p>
            <div className="sidebar-links">
              {herramientas.map((item, index) => (
                <Link key={item.nombre} to={item.ruta} onClick={cerrar}
                  className={`sidebar-link sidebar-tool-button ${rutaActual === item.ruta ? 'sidebar-link-active' : ''}`}
                  aria-current={rutaActual === item.ruta ? 'page' : undefined}
                  style={{ '--nav-index': index + 3 }}>
                  <Icono tipo={item.icono} size={17} />
                  <span>{item.nombre}</span>
                  {!item.disponible && <span className="sidebar-pending" title="Interfaz en desarrollo" />}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}

function FilaEstadistica({ nombre, numero, total }) {
  const porcentaje = total > 0 ? (numero / total) * 100 : 0
  return (
    <div className="stat-row">
      <div className="stat-row-top">
        <span>{nombre}</span>
        <strong className="tabular-nums">{numero.toLocaleString('es-MX')}</strong>
      </div>
      <div className="stat-track" role="progressbar" aria-label={`Proporción de ${nombre}`}
        aria-valuenow={Math.round(porcentaje)} aria-valuemin={0} aria-valuemax={100}>
        <div className="stat-fill" style={{ width: `${porcentaje}%` }} />
      </div>
      <p className="stat-percentage">{porcentaje.toFixed(1)}% del total</p>
    </div>
  )
}

function PaginaEnDesarrollo({ titulo, descripcion }) {
  return (
    <section className="intro-section" aria-label={titulo}>
      <div className="eyebrow"><span className="eyebrow-line" />MÓDULOS / FAILNET</div>
      <h1>{titulo}</h1>
      <p>{descripcion} La interfaz de este módulo estará disponible próximamente.</p>
      <Link to="/" className="ruta-volver">← Volver a Vista general</Link>
    </section>
  )
}

function App() {
  const [datos, setDatos] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [menuAbierto, setMenuAbierto] = useState(false)
  const [seccionActiva, setSeccionActiva] = useState('resumen')
  const location = useLocation()
  const rutaActual = location.pathname
  const pantalla = rutaActual === '/' ? 'general' : rutaActual.slice(1)
  const [actualizado, setActualizado] = useState(null)

  // Gesto táctil: un único estado controla panel, fondo y botones.
  const gesto = useRef(null)
  const [arrastrando, setArrastrando] = useState(false)
  const [desplazamiento, setDesplazamiento] = useState(0)

  const limpiarGesto = useCallback(() => {
    gesto.current = null
    setArrastrando(false)
    setDesplazamiento(0)
  }, [])

  const cerrarMenu = useCallback(() => {
    limpiarGesto()
    setMenuAbierto(false)
  }, [limpiarGesto])

  const alternarMenu = () => {
    limpiarGesto()
    setMenuAbierto(valor => !valor)
  }

  const iniciarGesto = (evento, accion) => {
    if (window.innerWidth > 820 || evento.touches.length !== 1 || gesto.current) return
    if ((accion === 'abrir' && menuAbierto) || (accion === 'cerrar' && !menuAbierto)) return

    const toque = evento.touches[0]
    gesto.current = {
      id: toque.identifier,
      accion,
      x: toque.clientX,
      y: toque.clientY,
      delta: 0,
      horizontal: false,
    }
  }

  // Las escuchas permanecen en window aunque el panel se mueva
  // fuera de la zona donde empezó el contacto.
  const moverGesto = useCallback((evento) => {
    const actual = gesto.current
    if (!actual) return

    const toque = Array.from(evento.touches).find(t => t.identifier === actual.id)
    if (!toque) return

    const dx = toque.clientX - actual.x
    const dy = toque.clientY - actual.y

    if (!actual.horizontal) {
      if (Math.abs(dy) > 12 && Math.abs(dy) > Math.abs(dx)) {
        gesto.current = null // Scroll vertical: no abrir el menú.
        return
      }
      if (Math.abs(dx) < 12 || Math.abs(dx) < Math.abs(dy) * 1.3) return
      if (actual.accion === 'abrir' && dx <= 0) return
      if (actual.accion === 'cerrar' && dx >= 0) return
      actual.horizontal = true
    }

    // Evita que el navegador transforme el arrastre en click o scroll.
    if (evento.cancelable) evento.preventDefault()

    actual.delta = actual.accion === 'abrir'
      ? Math.max(0, Math.min(260, dx))
      : Math.max(-260, Math.min(0, dx))

    setArrastrando(true)
    setDesplazamiento(actual.delta)
  }, [])

  const terminarGesto = useCallback((evento) => {
    const actual = gesto.current
    if (!actual) return

    const terminoEsteDedo = Array.from(evento.changedTouches).some(
      t => t.identifier === actual.id
    )
    if (!terminoEsteDedo) return

    if (actual.horizontal) {
      const completo = Math.abs(actual.delta) >= 75
      if (actual.accion === 'abrir') setMenuAbierto(completo)
      else setMenuAbierto(!completo)
    }

    gesto.current = null
    setArrastrando(false)
    setDesplazamiento(0)
  }, [])

  const cancelarGesto = useCallback(() => {
    gesto.current = null
    setArrastrando(false)
    setDesplazamiento(0)
  }, [])

  useEffect(() => {
    // passive:false permite preventDefault solamente durante el gesto horizontal.
    window.addEventListener('touchmove', moverGesto, { passive: false })
    window.addEventListener('touchend', terminarGesto)
    window.addEventListener('touchcancel', cancelarGesto)

    return () => {
      window.removeEventListener('touchmove', moverGesto)
      window.removeEventListener('touchend', terminarGesto)
      window.removeEventListener('touchcancel', cancelarGesto)
    }
  }, [moverGesto, terminarGesto, cancelarGesto])

  const cargarDatos = useCallback(async () => {
    setCargando(true)
    setError('')
    try {
      const respuesta = await fetch('/api/resumen/')
      if (!respuesta.ok) throw new Error(`No se pudo consultar el historial (HTTP ${respuesta.status}).`)
      const resultado = await respuesta.json()
      setDatos(resultado)
      setActualizado(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar los datos.')
      setDatos(null)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { cargarDatos() }, [cargarDatos])

  // El elemento activo acompaña el desplazamiento y cambia al seleccionar un enlace.
  useEffect(() => {
    if (rutaActual !== '/') return
    const actualizarSeccion = () => {
      const margenSuperior = Math.min(185, window.innerHeight * 0.38)
      let actual = 'resumen'
      for (const item of navegacion) {
        const nodo = document.getElementById(item.id)
        if (nodo && nodo.getBoundingClientRect().top <= margenSuperior) actual = item.id
      }
      const paginaConScroll = document.documentElement.scrollHeight > window.innerHeight + 40
      const alFinal = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 12
      if (paginaConScroll && alFinal) actual = 'modulos'
      setSeccionActiva(actual)
    }
    actualizarSeccion()
    window.addEventListener('scroll', actualizarSeccion, { passive: true })
    window.addEventListener('resize', actualizarSeccion)
    return () => {
      window.removeEventListener('scroll', actualizarSeccion)
      window.removeEventListener('resize', actualizarSeccion)
    }
  }, [rutaActual])

  useEffect(() => {
    if (!menuAbierto) return
    const tecla = (evento) => { if (evento.key === 'Escape') setMenuAbierto(false) }
    const overflowAnterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', tecla)
    return () => {
      document.body.style.overflow = overflowAnterior
      window.removeEventListener('keydown', tecla)
    }
  }, [menuAbierto])

  const seleccionarSeccion = (id) => {
    setSeccionActiva(id)
    cerrarMenu()
    // Si ya estamos en el ancla, el enlace no cambia la URL;
    // aun así debe poder desplazarnos a esa sección.
    if (rutaActual === '/' && location.hash === `#${id}`) {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  // La URL determina la pantalla. Al recargar, React Router la conserva.
  // Los enlaces a secciones utilizan /#resumen, /#estadisticas y /#modulos.
  useEffect(() => {
    cerrarMenu()
    const id = rutaActual === '/' ? location.hash.slice(1) : ''
    const frame = requestAnimationFrame(() => {
      if (id && ['resumen', 'estadisticas', 'modulos'].includes(id)) {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      } else {
        window.scrollTo({ top: 0, behavior: 'instant' })
      }
    })
    return () => cancelAnimationFrame(frame)
  // Sólo depende de la URL; cerrarMenu no altera la navegación.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rutaActual, location.hash])

  const total = datos?.total_analisis ?? 0
  const cifras = { sofi: datos?.sofi ?? 0, digital_twin: datos?.digital_twin ?? 0, pnl: datos?.pnl ?? 0 }
  const fecha = new Intl.DateTimeFormat('es-MX', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date())
  const horaActualizacion = actualizado
    ? new Intl.DateTimeFormat('es-MX', { hour: '2-digit', minute: '2-digit' }).format(actualizado)
    : null

  return (
    <div className="failnet-app">
      {/* Fuera del encabezado para mantenerlo por encima del panel móvil. */}
      <button type="button"
        className={`mobile-menu-button ${(menuAbierto || arrastrando) ? 'is-hidden' : ''}`}
        aria-label="Abrir menú"
        aria-controls="menu-failnet" aria-expanded={menuAbierto}
        tabIndex={(menuAbierto || arrastrando) ? -1 : 0}
        onClick={alternarMenu}>
        <span className="hamburger-line" />
        <span className="hamburger-line" />
        <span className="hamburger-line" />
      </button>
      {!menuAbierto && (
        <div
          className="mobile-swipe-edge"
          aria-hidden="true"
          onTouchStart={(evento) => iniciarGesto(evento, 'abrir')}
        />
      )}
      <BarraLateral
        abierta={menuAbierto}
        cerrar={cerrarMenu}
        activa={seccionActiva}
        seleccionar={seleccionarSeccion}
        rutaActual={rutaActual}
        arrastrando={arrastrando}
        desplazamiento={desplazamiento}
        iniciarGesto={iniciarGesto}
        moverGesto={moverGesto}
        terminarGesto={terminarGesto}
        cancelarGesto={cancelarGesto}
      />
      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <div className="breadcrumb"><strong>{{ '/': 'GENERAL', '/sofi': 'SOFI', '/digital-twin': 'DIGITAL TWIN', '/pnl': 'PNL', '/blockchain': 'BLOCKCHAIN' }[rutaActual] ?? 'GENERAL'}</strong></div>
          </div>
          <div className="topbar-right">
            <span className="topbar-date">{fecha}</span>
            {pantalla === 'general' && (
              <button type="button" className="refresh-button" onClick={cargarDatos}
                disabled={cargando} aria-label="Actualizar datos" title="Actualizar datos">
                <Icono tipo="actualizar" size={17} className={cargando ? 'animate-spin' : ''} />
              </button>
            )}
          </div>
        </header>

        <main className="page-content">
          <Routes>
            <Route path="/" element={<>

          <section id="resumen" className="intro-section">
            <div className="eyebrow"><span className="eyebrow-line" />CONSOLA DE ANÁLISIS</div>
            <h1>Análisis inteligente,<span> decisiones basadas en datos.</span></h1>
            <p>FailNet centraliza la detección de fallas, el análisis de tráfico y la interpretación de reportes mediante inteligencia artificial, incorporando mecanismos de trazabilidad e integridad de los resultados.</p>
          </section>

          {error && (
            <div className="error-message" role="alert">
              <Icono tipo="alerta" size={20} />
              <div><strong>No fue posible cargar los datos.</strong><p>{error}</p><p>Comprueba que Django esté ejecutándose en el puerto 8000.</p></div>
            </div>
          )}

          <section id="estadisticas" className="overview-section">
            <div className="section-header">
              <div><span className="section-number">RESUMEN</span><h2>Actividad registrada</h2></div>
              <span className="section-aside">{horaActualizacion ? `Actualizado a las ${horaActualizacion}` : 'Historial de análisis'}</span>
            </div>
            <div className="overview-grid">
              <article className="total-panel">
                <div className="total-panel-top"><span>ANÁLISIS TOTALES</span><Icono tipo="enlace" size={20} /></div>
                <div className="total-value tabular-nums">{cargando ? '...' : error ? '—' : total.toLocaleString('es-MX')}</div>
                <div className="total-panel-bottom">
                  <div><strong>Historial acumulado</strong><p>De todos los modelos</p></div>
                  <span>AI</span>
                </div>
              </article>
              <article className="distribution-panel">
                <div className="distribution-heading">
                  <div><span className="panel-kicker">DISTRIBUCIÓN</span><h3>Por módulo</h3></div>
                  <Icono tipo="estadisticas" size={21} />
                </div>
                <FilaEstadistica nombre="SOFI" numero={cifras.sofi} total={total} />
                <FilaEstadistica nombre="Digital Twin" numero={cifras.digital_twin} total={total} />
                <FilaEstadistica nombre="PNL" numero={cifras.pnl} total={total} />
              </article>
            </div>
          </section>

          <section id="modulos" className="modules-section">
            <div className="section-header">
              <div><span className="section-number">COMPONENTES</span><h2>Herramientas de análisis</h2></div>
            </div>
            <div className="modules-table">
              {modulos.map((modulo) => (
                <div key={modulo.numero} className="module-item">
                  <span className="module-number">{modulo.numero}</span>
                  <div className="module-information"><h3>{modulo.nombre}</h3><p>{modulo.descripcion}</p></div>
                    <div className="module-extra">
                      <span className="module-type">{modulo.tipo}</span>
                      <Link to={modulo.ruta} className="module-open-button">Abrir {modulo.nombre} ↗</Link>
                    </div>
                </div>
              ))}
            </div>
          </section>

            </>} />
            <Route path="/sofi" element={<SofiPage onAnalisisGuardado={cargarDatos} />} />
            <Route path="/digital-twin" element={<TwinPage onAnalisisGuardado={cargarDatos} />} />
            <Route path="/pnl" element={<PnlPage onAnalisisGuardado={cargarDatos} />} />
            <Route path="/blockchain" element={<BlockchainPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <footer className="page-footer">
            <span>© {new Date().getFullYear()} FailNet. Todos los derechos reservados.</span>
          </footer>
        </main>
      </div>
    </div>
  )
}

export default App
