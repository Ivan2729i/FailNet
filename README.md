
<div align="center">

# 🌐 FailNet

**Análisis inteligente de redes y verificación de integridad**

Plataforma web para detectar posibles fallas, clasificar tráfico de red y analizar reportes mediante inteligencia artificial.

[![FailNet CI](https://github.com/Ivan2729i/FailNet/actions/workflows/ci.yml/badge.svg)](https://github.com/Ivan2729i/FailNet/actions)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![React](https://img.shields.io/badge/React-19-149ECA?logo=react&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white)

</div>

---

## 🚀 Funcionalidades

| Módulo | Descripción |
|---|---|
| 🛡️ **SOFI** | Detecta posibles fallas a partir de mediciones de dos switches. |
| 📊 **Digital Twin** | Clasifica registros en cinco niveles de intensidad de tráfico. |
| 📝 **PNL** | Clasifica reportes, extrae entidades de red y genera resúmenes. |
| 🔗 **Blockchain** | Registra huellas SHA-256 y verifica la integridad de los análisis. |

Incluye dashboard, historial de resultados, tablas paginadas y exportación de análisis.

## 🧰 Tecnologías

**Backend:** Python 3.13 · Django 6.1 · scikit-learn · MongoDB Atlas

**Frontend:** React · Vite · Tailwind CSS · pnpm

**Calidad:** GitHub Actions · Ruff

## ⚙️ Instalación

**Requisitos:** Git, Python 3.13, Node.js 24, pnpm 10 y una instancia de MongoDB Atlas accesible.

### 1. Clonar el repositorio

```powershell
git clone https://github.com/Ivan2729i/FailNet.git
cd FailNet
```

### 2. Instalar el backend

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. Configurar las variables de entorno

```powershell
Copy-Item .env.example .env
```

En el archivo `.env`, define `DJANGO_SECRET_KEY`, `MONGODB_HOST`, `MONGODB_USER`, `MONGODB_PASSWORD` y `MONGODB_DB_NAME` con los valores de tu entorno.

El host de MongoDB debe comenzar con `mongodb+srv://`.

Para utilizar Vite localmente, incluye `http://127.0.0.1:5173` en `DJANGO_CSRF_TRUSTED_ORIGINS`.

> 🔒 Nunca subas el archivo `.env` ni credenciales reales al repositorio.

### 4. Preparar la base de datos

```powershell
python manage.py migrate
python manage.py check
```

### 5. Instalar el frontend

```powershell
cd frontend
pnpm install --frozen-lockfile
```

## ▶️ Ejecución

Abre dos terminales desde la raíz del proyecto.

**Terminal 1 · Backend**

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8000
```

**Terminal 2 · Frontend**

```powershell
cd frontend
pnpm dev
```

Abre la aplicación en:

**http://127.0.0.1:5173**

> **Modelos y datos:** los archivos `.joblib`, datasets y resultados de análisis no se incluyen en el repositorio. Para ejecutar las inferencias debes disponer de los modelos entrenados en `models/` y cargar archivos compatibles con cada módulo.

---

<div align="center">

**FailNet · Network Analysis**

Desarrollado con Python, Django, React e inteligencia artificial.

</div>

---

## 👨‍💻👤 Contacto

Desarrollado por **Ivan Paz Valladares**.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-blue?style=for-the-badge\&logo=linkedin\&logoColor=white)](https://www.linkedin.com/in/ivan-paz-valladares-b8886a343)

---
