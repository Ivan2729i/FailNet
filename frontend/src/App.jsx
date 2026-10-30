
import { useCallback, useEffect, useState } from 'react'

// ==================================================
// ICONOS SVG PROPIOS DE FAILNET
// ==================================================

function Icono({ tipo, size = 18, strokeWidth = 1.8, className = '' }) {
  const formas = {
    panel: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),

    estadisticas: (
      <path d="M4 20V12M10 20V5M16 20V9M22 20V3" />
    ),

    modulos: (
      <>
        <rect x="3" y="3" width="8" height="8" rx="1" />
        <rect x="13" y="3" width="8" height="8" rx="1" />
        <rect x="3" y="13" width="8" height="8" rx="1" />
        <rect x="13" y="13" width="8" height="8" rx="1" />
      </>
    ),

    sofi: (
      <>
        <path d="M12 2 20 6v6c0 5-3.4 8.5-8 10-4.6-1.5-8-5-8-10V6l8-4Z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),

    twin: (
      <>
        <circle cx="5" cy="12" r="2" />
        <circle cx="19" cy="5" r="2" />
        <circle cx="19" cy="19" r="2" />
        <path d="M7 11 17 6M7 13l10 5" />
      </>
    ),

    pnl: (
      <>
        <path d="M6 2h9l4 4v16H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z" />
        <path d="M14 2v5h5M8 12h8M8 16h8" />
      </>
    ),

    blockchain: (
      <>
        <rect x="3" y="4" width="7" height="7" rx="1" />
        <rect x="14" y="13" width="7" height="7" rx="1" />
        <path d="M10 7h4M14 7l3 3v3M10 17H7v-6" />
      </>
    ),

    menu: <path d="M4 7h16M4 12h16M4 17h16" />,

    cerrar: <path d="M5 5 19 19M19 5 5 19" />,

    actualizar: (
      <>
        <path d="M20 7v5h-5M4 17v-5h5" />
        <path d="M5.5 9a7 7 0 0 1 12-2L20 12M4 12l2.5 5a7 7 0 0 0 12-2" />
      </>
    ),

    alerta: (
      <>
        <path d="m12 3 10 18H2L12 3Z" />
        <path d="M12 9v5M12 18h.01" />
      </>
    ),

    enlace: <path d="M7 17 17 7M9 7h8v8" />,

    datos: (
      <>
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5M3 12c0 1.7 4 3 9 3s9-1.3 9-3" />
      </>
    ),
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {formas[tipo] ?? <circle cx="12" cy="12" r="8" />}
    </svg>
  )
}


// ==================================================
// NAVEGACIÓN
// ==================================================

const navegacion = [
  { nombre: 'Vista general', enlace: '#resumen', icono: 'panel' },
  { nombre: 'Estadísticas', enlace: '#estadisticas', icono: 'estadisticas' },
  { nombre: 'Módulos', enlace: '#modulos', icono: 'modulos' },
]

const herramientas = [
  { nombre: 'SOFI', icono: 'sofi' },
  { nombre: 'Digital Twin', icono: 'twin' },
  { nombre: 'PNL', icono: 'pnl' },
  { nombre: 'Blockchain', icono: 'blockchain' },
]

const definicionModulos = [
  {
    numero: '01',
    nombre: 'SOFI',
    tipo: 'Detección de fallas',
    descripcion: 'Clasificación de registros normales y eventos de falla.',
  },
  {
    numero: '02',
    nombre: 'Digital Twin',
    tipo: 'Análisis de tráfico',
    descripcion: 'Clasificación de cinco niveles de intensidad de tráfico.',
  },
  {
    numero: '03',
    nombre: 'PNL',
    tipo: 'Análisis de reportes',
    descripcion: 'Clasificación de texto, entidades y resumen técnico.',
  },
]


// ==================================================
// BARRA LATERAL
// ==================================================

function BarraLateral({ abierta, cerrar }) {
  return (
    <>
      {abierta && (
        <button
          type="button"
          className="mobile-overlay"
          aria-label="Cerrar navegación"
          onClick={cerrar}
        />
      )}

      <aside
        className={`sidebar ${abierta ? 'sidebar-open' : ''}`}
        aria-label="Navegación principal"
      >
        <div className="sidebar-brand">
          <div className="brand-icon" aria-hidden="true">
            F<span>.</span>
          </div>

          <div className="brand-text">
            <strong>FAILNET</strong>
            <small>NETWORK ANALYSIS</small>
          </div>

          <button
            type="button"
            className="sidebar-close"
            onClick={cerrar}
            aria-label="Cerrar menú"
          >
            <Icono tipo="cerrar" size={19} />
          </button>
        </div>

        <div className="sidebar-content">

          <div className="sidebar-group">
            <p className="sidebar-heading">
              ESPACIO DE TRABAJO
            </p>

            <nav className="sidebar-links">
              {navegacion.map((item, index) => (
                <a
                  key={item.nombre}
                  href={item.enlace}
                  onClick={cerrar}
                  className={`sidebar-link ${
                    index === 0 ? 'sidebar-link-active' : ''
                  }`}
                >
                  <Icono tipo={item.icono} size={17} />
                  <span>{item.nombre}</span>
                </a>
              ))}
            </nav>
          </div>

          <div className="sidebar-group">
            <p className="sidebar-heading">
              HERRAMIENTAS
            </p>

            <div className="sidebar-links">
              {herramientas.map((item) => (
                <div
                  key={item.nombre}
                  className="sidebar-link sidebar-link-disabled"
                  title="Interfaz en desarrollo"
                >
                  <Icono tipo={item.icono} size={17} />
                  <span>{item.nombre}</span>
                  <span className="sidebar-pending" />
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="sidebar-bottom">
          <span className="sidebar-bottom-mark" />

          <div>
            <strong>FAILNET / LAB</strong>
            <small>Entorno de desarrollo</small>
          </div>
        </div>
      </aside>
    </>
  )
}


// ==================================================
// ESTADÍSTICAS
// ==================================================

function FilaEstadistica({ nombre, numero, total }) {
  const porcentaje = total > 0
    ? (numero / total) * 100
    : 0

  return (
    <div className="stat-row">
      <div className="stat-row-top">
        <span>{nombre}</span>

        <strong className="tabular-nums">
          {numero.toLocaleString('es-MX')}
        </strong>
      </div>

      <div
        className="stat-track"
        role="progressbar"
        aria-label={`Proporción de ${nombre}`}
        aria-valuenow={Math.round(porcentaje)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="stat-fill"
          style={{ width: `${porcentaje}%` }}
        />
      </div>

      <p className="stat-percentage">
        {porcentaje.toFixed(1)}% del total
      </p>
    </div>
  )
}


// ==================================================
// COMPONENTE PRINCIPAL
// ==================================================

function App() {
  const [datos, setDatos] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [menuAbierto, setMenuAbierto] = useState(false)
  const [actualizado, setActualizado] = useState(null)

  // ------------------------------------------------
  // CONSULTAR API DE DJANGO
  // ------------------------------------------------

  const cargarDatos = useCallback(async () => {
    setCargando(true)
    setError('')

    try {
      const respuesta = await fetch('/api/resumen/')

      if (!respuesta.ok) {
        throw new Error(
          `No se pudo consultar el historial (HTTP ${respuesta.status}).`
        )
      }

      const resultado = await respuesta.json()

      setDatos(resultado)
      setActualizado(new Date())

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Ocurrió un error al cargar los datos.'
      )

    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    cargarDatos()
  }, [cargarDatos])

  // ------------------------------------------------
  // NAVEGACIÓN RESPONSIVA
  // ------------------------------------------------

  useEffect(() => {
    if (!menuAbierto) return

    const cerrarConEscape = (evento) => {
      if (evento.key === 'Escape') {
        setMenuAbierto(false)
      }
    }

    window.addEventListener('keydown', cerrarConEscape)

    return () => {
      window.removeEventListener('keydown', cerrarConEscape)
    }
  }, [menuAbierto])

  // ------------------------------------------------
  // DATOS PARA EL DASHBOARD
  // ------------------------------------------------

  const total = datos?.total_analisis ?? 0

  const cifras = {
    sofi: datos?.sofi ?? 0,
    digital_twin: datos?.digital_twin ?? 0,
    pnl: datos?.pnl ?? 0,
  }

  const fecha = new Intl.DateTimeFormat('es-MX', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  }).format(new Date())

  const horaActualizacion = actualizado
    ? new Intl.DateTimeFormat('es-MX', {
        hour: '2-digit',
        minute: '2-digit',
      }).format(actualizado)
    : null

  // ------------------------------------------------
  // INTERFAZ
  // ------------------------------------------------

  return (
    <div className="failnet-app">

      <BarraLateral
        abierta={menuAbierto}
        cerrar={() => setMenuAbierto(false)}
      />

      <div className="main-area">

        <header className="topbar">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="mobile-menu-button"
              onClick={() => setMenuAbierto(true)}
              aria-label="Abrir navegación"
              aria-expanded={menuAbierto}
            >
              <Icono tipo="menu" size={21} />
            </button>

            <div className="breadcrumb">
              <span>FAILNET</span>
              <span className="breadcrumb-separator">/</span>
              <strong>GENERAL</strong>
            </div>
          </div>

          <div className="topbar-right">
            <span className="topbar-date">{fecha}</span>

            <button
              type="button"
              className="refresh-button"
              onClick={cargarDatos}
              disabled={cargando}
              aria-label="Actualizar datos"
              title="Actualizar datos"
            >
              <Icono
                tipo="actualizar"
                size={17}
                className={cargando ? 'animate-spin' : ''}
              />
            </button>
          </div>
        </header>

        <main className="page-content">

          {/* PRESENTACIÓN */}
          <section id="resumen" className="intro-section">
            <div className="eyebrow">
              <span className="eyebrow-line" />
              CONSOLA DE ANÁLISIS
            </div>

            <h1>
              Información de red,
              <span> sin ruido.</span>
            </h1>

            <p>
              Una vista centralizada de los análisis realizados
              en FailNet. Explora los resultados de Machine Learning,
              procesamiento de lenguaje natural y los registros
              de integridad.
            </p>
          </section>

          {/* ERRORES DE API */}
          {error && (
            <div className="error-message" role="alert">
              <Icono tipo="alerta" size={20} />

              <div>
                <strong>No fue posible cargar los datos.</strong>
                <p>{error}</p>
                <p>
                  Comprueba que Django esté ejecutándose
                  en el puerto 8000.
                </p>
              </div>
            </div>
          )}

          {/* ESTADÍSTICAS */}
          <section
            id="estadisticas"
            className="overview-section"
          >
            <div className="section-header">
              <div>
                <span className="section-number">
                  01 / RESUMEN
                </span>

                <h2>Actividad registrada</h2>
              </div>

              <span className="section-aside">
                {horaActualizacion
                  ? `Actualizado a las ${horaActualizacion}`
                  : 'Historial de análisis'}
              </span>
            </div>

            <div className="overview-grid">

              <article className="total-panel">
                <div className="total-panel-top">
                  <span>ANÁLISIS TOTALES</span>
                  <Icono tipo="enlace" size={20} />
                </div>

                <div className="total-value tabular-nums">
                  {cargando
                    ? '...'
                    : error
                      ? '—'
                      : total.toLocaleString('es-MX')}
                </div>

                <div className="total-panel-bottom">
                  <div>
                    <strong>Historial acumulado</strong>
                    <p>
                      Registros almacenados en MongoDB Atlas
                    </p>
                  </div>

                  <span>FN / 001</span>
                </div>
              </article>

              <article className="distribution-panel">
                <div className="distribution-heading">
                  <div>
                    <span className="panel-kicker">
                      DISTRIBUCIÓN
                    </span>

                    <h3>Por módulo</h3>
                  </div>

                  <Icono tipo="estadisticas" size={21} />
                </div>

                <FilaEstadistica
                  nombre="SOFI"
                  numero={cifras.sofi}
                  total={total}
                />

                <FilaEstadistica
                  nombre="Digital Twin"
                  numero={cifras.digital_twin}
                  total={total}
                />

                <FilaEstadistica
                  nombre="PNL"
                  numero={cifras.pnl}
                  total={total}
                />
              </article>

            </div>
          </section>

          {/* MÓDULOS */}
          <section id="modulos" className="modules-section">
            <div className="section-header">
              <div>
                <span className="section-number">
                  02 / COMPONENTES
                </span>

                <h2>Herramientas de análisis</h2>
              </div>
            </div>

            <div className="modules-table">
              {definicionModulos.map((modulo) => (
                <div
                  key={modulo.numero}
                  className="module-item"
                >
                  <span className="module-number">
                    {modulo.numero}
                  </span>

                  <div className="module-information">
                    <h3>{modulo.nombre}</h3>
                    <p>{modulo.descripcion}</p>
                  </div>

                  <div className="module-extra">
                    <span className="module-type">
                      {modulo.tipo}
                    </span>

                    <span className="module-state">
                      Interfaz en desarrollo
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* INFRAESTRUCTURA */}
          <section className="architecture-section">
            <div className="architecture-heading">
              <Icono tipo="datos" size={22} />

              <div>
                <h3>Infraestructura de FailNet</h3>
                <p>React + Django + MongoDB Atlas</p>
              </div>
            </div>

            <div className="architecture-tags">
              <span>REACT</span>
              <span>DJANGO</span>
              <span>MONGODB</span>
              <span>SHA-256</span>
            </div>
          </section>

          <footer className="page-footer">
            <span>FAILNET</span>
            <span>PLATAFORMA DE ANÁLISIS DE REDES</span>
          </footer>

        </main>
      </div>
    </div>
  )
}

export default App
