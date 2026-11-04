# NEIRO YOMI • API Backend

Backend central de streaming de audio en alta fidelidad y catálogo musical para **NEIRO YOMI**.
Desarrollado con **FastAPI (Python 3.12)**, **FFmpeg**, **SQLAlchemy**, **Supabase** y **yt-dlp**.

---

## 🗄️ Conexión con Supabase (Base de Datos & Storage)

### Paso 1: Crear proyecto en Supabase
1. Ingresa a **[Supabase.com](https://supabase.com)** y crea un proyecto nuevo (ej. `neiro-yomi`).
2. Guarda la contraseña de base de datos que elijas.

### Paso 2: Ejecutar el script SQL de inicialización
1. En tu panel de Supabase, entra a la pestaña **SQL Editor**.
2. Haz clic en **"New query"** y copia el contenido completo del archivo:
   [`database/supabase_init.sql`](./database/supabase_init.sql)
3. Haz clic en **Run**. Esto creará:
   - Todas las tablas (`users`, `tracks`, `albums`, `artists`, `favorites`, `playlists`, `listening_history`).
   - Los índices de búsqueda difusa Trigram (`pg_trgm`).
   - Los buckets de almacenamiento `neiro-audio` y `neiro-artwork`.
   - Las políticas públicas de lectura de carátulas y audio.
   - Pista master inicial de demostración (*Kanazawa Rain*).

### Paso 3: Configurar las variables de entorno
En tu archivo `.env` o en las variables de tu servidor cloud (Railway/Render):

```env
# URL de conexión directa PostgreSQL de Supabase
DATABASE_URL=postgresql://postgres:[TU_PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres?sslmode=require

# Credenciales de API y Almacenamiento Supabase (Backend Service Role)
SUPABASE_URL=https://[PROJECT_REF].supabase.co
SUPABASE_SERVICE_ROLE_KEY=[TU_SERVICE_ROLE_KEY]
STORAGE_PROVIDER=supabase
```

---

## 🚀 Opciones de Despliegue en Producción

### 1. Railway (Recomendada)
1. Conecta tu repositorio de GitHub en [Railway.app](https://railway.app).
2. Selecciona **New Project** > **Deploy from GitHub repo**.
3. Railway detectará automáticamente `railway.json` y `api/Dockerfile`.
4. En **Variables**, agrega `DATABASE_URL` (de Supabase), `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y `CORS_ORIGINS`.
5. El servicio se desplegará con un dominio público HTTPS (ej. `https://api-neiro-yomi.up.railway.app`).

### 2. Render
1. En [Render.com](https://render.com), crea un **New Web Service**.
2. Conecta tu repositorio y selecciona el runtime **Docker**.
3. Usa el archivo `render.yaml` desde Blueprints.

### 3. Fly.io
```bash
fly launch
fly deploy
```

---

## 📡 Endpoints Principales

- `GET /health`: Verificación de salud del servicio (healthcheck).
- `GET /docs`: Documentación interactiva Swagger UI.
- `GET /api/v1/tracks`: Catálogo de pistas master.
- `GET /api/v1/search?q={query}`: Búsqueda unificada local + Spotify / YouTube Music.
- `GET /api/v1/tracks/{id}/stream`: Streaming de audio con soporte de HTTP Range chunks.
- `POST /api/v1/auth/login`: Autenticación y generación de JWT Bearer tokens.
- `POST /api/v1/auth/register`: Registro de nuevos usuarios audiófilos.
