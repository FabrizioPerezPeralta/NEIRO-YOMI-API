# NEIRO YOMI • Audio Engine & Streaming API

> **Hear Every Detail. The Art of Listening. 音を感じる。**  
> Backend central de streaming de audio en alta fidelidad y motor de catálogo para la plataforma musical **NEIRO YOMI**.

Desarrollado con **Python 3.12**, **FastAPI**, **SQLAlchemy ORM**, **Supabase (PostgreSQL & Storage)**, **FFmpeg** y **yt-dlp**.

---

## 📌 ¿Qué hace este Backend?

1. **Streaming Audiófilo Bit-Perfect:**
   - Transmisión de audio en búferes de baja latencia con soporte completo para cabeceras HTTP `Range: bytes=inicio-fin` (reproducción continua, rebobinado instantáneo y *gapless playback*).
   - Preservación estricta de la frecuencia de muestreo nativa (hasta 24-bit / 192,000 Hz) en formatos sin pérdida (**FLAC**, **ALAC**, **WAV**, **AIFF**), así como códecs eficientes (**OPUS**, **AAC**, **MP3**).
2. **Motor de Búsqueda Global Híbrido:**
   - Búsqueda federada que indexa simultáneamente tu colección local Master y catálogos mundiales de streaming en línea (YouTube Music y Jamendo Creative Commons).
3. **Auditoría e Integridad Acústica:**
   - Extracción de metadatos profundos con `mutagen` y cálculo de firmas criptográficas **SHA-256** por cada pista almacenada, garantizando cero alteración (*anti-transcoding fraud*).
4. **Almacenamiento en la Nube (Supabase Storage):**
   - Carga y distribución de carátulas y pistas de audio hacia buckets CDN con permisos de lectura pública y subida administrativa mediante `service_role`.
5. **Autenticación y Sesiones Seguras:**
   - Registro de usuarios, gestión de perfiles, colecciones de favoritos y listas de reproducción protegidas por tokens **JWT (Bearer HS256)** y contraseñas hasheadas con **Bcrypt**.

---

## 🏗️ Arquitectura de Componentes

La API está diseñada siguiendo los principios de arquitectura en capas desacopladas (*Clean Layered Architecture*), permitiendo que múltiples clientes consuman el mismo contrato de interfaz REST:

```mermaid
flowchart TD
    subgraph Clients["Clientes Frontend"]
        Web["Web Client (React / Next.js)"]
        Desktop["Desktop Client (Tauri / Rust)"]
        Mobile["Mobile Client (Flutter / Dart)"]
    end

    subgraph Gateway["Capa de Entrada & Seguridad"]
        CORS["CORS Middleware"]
        AuthMiddleware["JWT Authentication Guard"]
        Router["FastAPI Application Router"]
    end

    subgraph Services["Capa de Servicios de Negocio"]
        StreamService["Audio Stream Engine (HTTP Range Chunks)"]
        MetaExtractor["Metadata & SHA-256 Analyzer (FFmpeg / Mutagen)"]
        SpotubeService["Global Catalog Sync (yt-dlp & Jamendo CC)"]
        StorageService["Hybrid Storage Service (Supabase & Local)"]
    end

    subgraph Data["Capa de Persistencia"]
        ORM["SQLAlchemy ORM (Connection Pooler)"]
        SupabaseDB["Supabase PostgreSQL (Database)"]
        SupabaseBucket["Supabase Storage (Buckets: neiro-audio & neiro-artwork)"]
    end

    Clients --> Gateway
    Gateway --> Services
    Services --> Data
```

---

## ☁️ Diagrama de Despliegue en Producción

El backend está optimizado para ejecutarse en contenedores Docker y comunicarse con el ecosistema de Supabase y frontends serverless:

```mermaid
flowchart LR
    subgraph Users["Usuarios Finales"]
        Browser["Navegador Web / App"]
    end

    subgraph FrontendHost["Alojamiento Web"]
        Vercel["Vercel / Netlify (Next.js 14)"]
    end

    subgraph BackendHost["Servidor de Aplicación"]
        Container["Docker Container (Python 3.12 + FFmpeg)"]
        Uvicorn["Uvicorn ASGI Server (Port 8000)"]
    end

    subgraph CloudServices["Servicios en la Nube (Supabase)"]
        Postgres["PostgreSQL Database (Tablas, RLS, Indices Trigram)"]
        CDN["Supabase Object Storage (Audio & Caratulas)"]
    end

    subgraph ExternalAudio["Fuentes de Audio Externas"]
        OnlineStream["YouTube Music / Jamendo CDN"]
    end

    Browser -->|HTTPS| Vercel
    Vercel -->|REST API /api/v1| Container
    Container --> Uvicorn
    Uvicorn -->|SQL Port 5432/6543| Postgres
    Uvicorn -->|S3 Upload / REST| CDN
    Uvicorn -->|Audio Fetch| OnlineStream
    Browser -->|Direct Audio Stream| CDN
```

---

## 🗄️ Modelo de Datos y Base de Datos (Supabase)

La base de datos utiliza **PostgreSQL** administrado en **Supabase** con extensiones de búsqueda difusa:

- `users`: Cuentas, roles (`user`, `admin`, `artist`) y credenciales seguras.
- `artists`: Artistas, países, géneros y biografía.
- `albums`: Álbumes discográficos, año, total de pistas e indicador `is_hires`.
- `tracks`: Metadatos técnicos audiófilos (códec, tasa de muestreo en Hz, profundidad en bits, tasa de bits, checksum SHA-256).
- `audio_assets`: Mapeo de almacenamiento binario y tamaños de archivo en bytes.
- `playlists` y `playlist_tracks`: Listas de reproducción de usuarios y posiciones ordenadas.
- `favorites`: Relación muchos a muchos para canciones marcadas con corazón por usuario.
- `listening_history`: Registro de actividad de escucha para recomendaciones.

### Inicialización en 1 Clic
Copia el script SQL incluido en el repositorio:
[`database/supabase_init.sql`](./database/supabase_init.sql)  
Pégalo en el **SQL Editor** de tu panel de Supabase y haz clic en **Run**.

---

## ⚙️ Variables de Entorno (`.env`)

Crea un archivo `.env` en la raíz de la carpeta `api/` (puedes basarte en `.env.example`):

| Variable | Tipo | Descripción | Ejemplo |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | String | Entorno de ejecución (`development` o `production`) | `production` |
| `PORT` | Integer | Puerto de escucha HTTP | `8000` |
| `SECRET_KEY` | String | Clave secreta criptográfica para firmar JWT | `547af011685...` |
| `CORS_ORIGINS` | String | Orígenes permitidos (separados por coma o `*`) | `*` o `https://tuapp.vercel.app` |
| `DATABASE_URL` | String | Cadena de conexión URI de Supabase PostgreSQL | `postgresql://postgres:[PWD]@db.[REF].supabase.co:5432/postgres?sslmode=require` |
| `SUPABASE_URL` | String | URL del proyecto Supabase | `https://[PROJECT_REF].supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | String | Clave secreta `service_role` (acceso administrativo) | `eyJhbGciOi...` |
| `STORAGE_PROVIDER` | String | Proveedor de archivos (`supabase` o `local`) | `supabase` |
| `SUPABASE_BUCKET_AUDIO` | String | Nombre del bucket para audios | `neiro-audio` |
| `SUPABASE_BUCKET_ARTWORK` | String | Nombre del bucket para carátulas | `neiro-artwork` |

---

## 📡 Referencia de Endpoints Principales

Todos los endpoints están documentados interactivamente mediante **Swagger UI** en `/docs`.

### Sistema & Salud
- `GET /health` → Estado del servicio (`status: "healthy"`).
- `GET /` o `/api/info` → Metadatos y versión de la API.
- `GET /docs` → Documentación Swagger UI interactiva.

### Autenticación & Perfil
- `POST /api/v1/auth/register` → Registrar nuevo usuario audiófilo.
- `POST /api/v1/auth/login` → Iniciar sesión (retorna token Bearer JWT).
- `GET /api/v1/auth/me` → Obtener perfil del usuario autenticado.

### Catálogo de Pistas & Streaming
- `GET /api/v1/tracks` → Listar pistas de la colección Master.
- `GET /api/v1/tracks/{id}` → Detalles de una pista y fidelidad técnica.
- `GET /api/v1/tracks/{id}/stream` → **Streaming de audio bit-perfect** con soporte `Range: bytes=x-y`.
- `POST /api/v1/tracks/upload` → Subir archivo de audio (FLAC, WAV, MP3) con extracción automática de metadatos y carátula.
- `POST /api/v1/tracks/import-directory` → Escaneo e indexación por lotes de una carpeta local en la PC.

### Búsqueda Global en Línea
- `GET /api/v1/search?q={query}` → Búsqueda unificada (Master local + YouTube Music online).
- `GET /api/v1/tracks/online/trending` → Pistas en tendencia global.
- `GET /api/v1/tracks/online/category/{cat}` → Explorar por género (`city_pop`, `jazz`, `classical`, `lofi`, etc.).
- `POST /api/v1/tracks/online-save/{videoId}` → Guardar pista online en tu casillero local permanente.

### Favoritos & Playlists
- `GET /api/v1/favorites` → Lista de favoritos del usuario.
- `POST /api/v1/favorites/{trackId}/toggle` → Marcar / desmarcar pista favorita.
- `GET /api/v1/playlists` → Listar playlists públicas o del usuario.
- `POST /api/v1/playlists` → Crear nueva playlist.

---

## 🚀 Despliegue en Producción

### Opción 1: Railway (Recomendada)
1. Conecta este repositorio en [Railway.app](https://railway.app).
2. Railway detectará automáticamente el archivo `railway.json` y compilará el contenedor con `Dockerfile` (incluyendo **FFmpeg**).
3. Añade en **Variables** tu `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y `SECRET_KEY`.
4. En **Settings > Networking**, genera tu dominio público HTTPS.

### Opción 2: Render
1. Crea un **Web Service** en [Render.com](https://render.com) conectando este repositorio.
2. Selecciona entorno **Docker** (detectará automáticamente `render.yaml`).
3. Configura tus variables de entorno y despliega.

### Opción 3: Docker Local
```bash
docker build -t neiro-yomi-api .
docker run -p 8000:8000 --env-file .env neiro-yomi-api
```

### Opción 4: Ejecución Local Directa
```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # En Windows
# source venv/bin/activate  # En Linux/macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Arrancar servidor de desarrollo
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Accede a **[http://localhost:8000/docs](http://localhost:8000/docs)** para interactuar con la API.
