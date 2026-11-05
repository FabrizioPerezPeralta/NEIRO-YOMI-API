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

## 🌐 Cómo Consumir e Integrar esta API en Otros Proyectos

Esta API fue diseñada como un **motor de streaming y catálogo agnóstico e interoperable**. Cualquier desarrollador o aplicación externa (sitios web de terceros, aplicaciones móviles en Flutter/React Native/Swift/Kotlin, bots de Discord/Telegram, clientes de escritorio o scripts de automatización) puede integrarse y consumir sus servicios.

### 1. Requisitos Previos y URL Base

- **URL Base en Desarrollo:** `http://localhost:8000`
- **URL Base en Producción:** `https://tu-api.up.railway.app` (o el dominio asignado en tu hosting)
- **Documentación Interactiva:** Visita `/docs` (Swagger) o `/redoc` para probar peticiones en vivo y ver los contratos JSON exactos.

#### Política de CORS (Cross-Origin Resource Sharing)
Para que aplicaciones web alojadas en otros dominios (ej. `https://mi-otra-app.com`, `http://localhost:3000`) puedan consumir la API sin bloqueos de seguridad en el navegador:
- Configura en el archivo `.env` de la API:
  ```env
  CORS_ORIGINS=*
  ```
  *(O especifica los dominios separados por coma: `https://mi-app.com,https://dashboard.externo.com`)*.

---

### 2. Flujo de Autenticación (Bearer JWT)

Los endpoints de catálogo público, búsqueda y streaming pueden consumirse libremente, mientras que funciones de biblioteca personal (favoritos, creación de playlists, perfil) requieren autenticación por token.

1. **Obtener el Token (`POST /api/v1/auth/login`):**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username_or_email": "usuario", "password": "tu_password"}'
   ```
   **Respuesta JSON:**
   ```json
   {
     "user": {
       "id": "a0000000-0000-0000-0000-000000000001",
       "email": "usuario@ejemplo.com",
       "username": "usuario",
       "displayName": "Usuario",
       "role": "user",
       "avatarUrl": null,
       "createdAt": "2026-11-05T12:00:00Z"
     },
     "accessToken": "eyJhbGciOiJIUzI1NiIsIn...",
     "tokenType": "bearer"
   }
   ```

2. **Enviar el Token en peticiones protegidas:**
   Incluye la cabecera HTTP estándar en cada petición subsecuente:
   ```http
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsIn...
   ```

---

### 3. Reproducción de Audio en Clientes Externos (HTML5 / Móvil)

El endpoint de streaming soporta **HTTP Range Requests** (`206 Partial Content`). Esto permite que los reproductores nativos reproduzcan instantáneamente sin esperar a que el archivo descargue por completo, y soporta rebobinado fluido (*seek*).

#### En HTML5 / React / Vue:
```html
<audio controls preload="metadata">
  <source src="https://tu-api.up.railway.app/api/v1/tracks/{TRACK_ID}/stream" type="audio/flac">
  Tu navegador no soporta el elemento de audio.
</audio>
```

---

### 4. Ejemplos de Integración por Lenguaje / Framework

#### A. JavaScript / TypeScript (Fetch API / React / Next.js / Node.js)

```typescript
// neiro-client.ts
const API_BASE_URL = "https://tu-api.up.railway.app";

// 1. Obtener catálogo de pistas Master
export async function getTracks() {
  const response = await fetch(`${API_BASE_URL}/api/v1/tracks`);
  if (!response.ok) throw new Error("Error obteniendo catálogo");
  return await response.json();
}

// 2. Búsqueda federada (Colección local + YouTube Music)
export async function searchMusic(query: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/search?q=${encodeURIComponent(query)}`);
  return await response.json();
}

// 3. Obtener URL directa de streaming para un reproductor de audio
export function getStreamUrl(trackId: string): string {
  return `${API_BASE_URL}/api/v1/tracks/${trackId}/stream`;
}

// 4. Petición autenticada (ej. listar favoritos del usuario)
export async function getFavorites(token: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/favorites`, {
    headers: {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/json"
    }
  });
  return await response.json();
}
```

#### B. Python (Scripts, Automatizaciones o Bots de Discord/Telegram)

```python
import requests

API_BASE = "https://tu-api.up.railway.app"

# 1. Iniciar sesión y obtener token
login_res = requests.post(
    f"{API_BASE}/api/v1/auth/login",
    json={"username_or_email": "audiophile", "password": "password123"}
)
token = login_res.json()["accessToken"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Consultar pistas en alta resolución (Hi-Res)
tracks_res = requests.get(f"{API_BASE}/api/v1/tracks")
tracks = tracks_res.json()

for track in tracks:
    print(f"🎵 {track['title']} - {track['codec'].upper()} {track['sampleRate']}Hz/{track['bitDepth']}bit")

# 3. URL de streaming lista para VLC, pygame, discord.py o ffmpeg
stream_url = f"{API_BASE}/api/v1/tracks/{tracks[0]['id']}/stream"
print("Stream URL:", stream_url)
```

#### C. Dart / Flutter (Aplicaciones Móviles Android / iOS)

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart'; // O audioplayers

class NeiroApiClient {
  static const String baseUrl = 'https://tu-api.up.railway.app';

  // Obtener catálogo de canciones
  static Future<List<dynamic>> fetchTracks() async {
    final response = await http.get(Uri.parse('$baseUrl/api/v1/tracks'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Error al cargar canciones');
  }

  // Reproducir pista directamente en just_audio
  static Future<void> playTrack(AudioPlayer player, String trackId) async {
    final streamUrl = '$baseUrl/api/v1/tracks/$trackId/stream';
    await player.setUrl(streamUrl);
    player.play();
  }
}
```

#### D. cURL / Terminal / Scripts de Bash

```bash
# 1. Comprobar salud del servicio
curl -s http://localhost:8000/health

# 2. Búsqueda de canciones
curl -s "http://localhost:8000/api/v1/search?q=ambient" | jq .

# 3. Inspeccionar streaming por rangos (debe devolver HTTP 206 Partial Content)
curl -I -r 0-1024 "http://localhost:8000/api/v1/tracks/{TRACK_ID}/stream"
```

---

### 5. Códigos de Respuesta y Manejo de Errores

La API utiliza códigos de estado HTTP estándar y respuestas JSON con la propiedad `detail`:

| Código | Significado | Explicación |
| :--- | :--- | :--- |
| `200 OK` | Petición exitosa | Devuelve el recurso solicitado en formato JSON. |
| `201 Created` | Recurso creado | Registro o creación de playlist/favorito completado. |
| `206 Partial Content` | Streaming por rangos | Se transmite el fragmento de audio solicitado (`Range: bytes=x-y`). |
| `400 Bad Request` | Parámetros inválidos | La petición carece de campos obligatorios o formato erróneo. |
| `401 Unauthorized` | No autenticado | Token ausente, vencido o credenciales inválidas. |
| `403 Forbidden` | Prohibido | No tienes permisos suficientes para realizar esta acción. |
| `404 Not Found` | No encontrado | La pista, artista, álbum o recurso solicitado no existe. |
| `422 Unprocessable Entity`| Error de validación | El cuerpo JSON no cumple con el esquema requerido por Pydantic. |
| `500 Internal Error` | Error de servidor | Fallo interno en la base de datos o el motor de procesamiento. |

Ejemplo de respuesta de error:
```json
{
  "detail": "Pista no encontrada o archivo de audio inaccesible"
}
```

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
