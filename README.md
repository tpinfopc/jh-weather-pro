# JH WEATHER PRO v2 — Guía de Despliegue Web

## ─── Estructura del proyecto ───────────────────────────────────────────────

```
jh-weather-pro/
├── main.py
├── requirements.txt
└── .env              ← Solo para desarrollo local (NO subir a git)
```

---

## ─── 1. Desarrollo local ───────────────────────────────────────────────────

### Paso 1 — Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 2 — Configurar la API Key (sin exponer en el código)

Crea un archivo `.env` en la raíz del proyecto:

```
OWM_API_KEY=tu_api_key_de_openweathermap_aqui
```

Luego exporta la variable antes de ejecutar (Linux/macOS):

```bash
export $(cat .env)
```

En Windows (PowerShell):

```powershell
$env:OWM_API_KEY = "tu_api_key_aqui"
```

### Paso 3 — Ejecutar en modo web local

```bash
flet run --web main.py
```

Abre el navegador en **http://localhost:8550**

Para cambiar el puerto:

```bash
flet run --web --port 3000 main.py
```

---

## ─── 2. Despliegue en producción ──────────────────────────────────────────

### ⚠️ Nota importante sobre Flet en Netlify/Vercel

Flet genera una **aplicación Python con servidor WebSocket**, no un sitio estático
como React o Vue. Eso significa que necesita un servidor Python corriendo en
producción. Las opciones recomendadas son:

| Plataforma       | Plan gratuito | Fácil de usar | Recomendado |
|-----------------|---------------|---------------|-------------|
| **Fly.io**       | ✅            | ✅✅✅         | ⭐ MEJOR    |
| **Railway**      | ✅            | ✅✅✅         | ⭐⭐         |
| **Render**       | ✅            | ✅✅           | ⭐⭐         |
| Netlify/Vercel   | Solo estático | ❌            | No aplica   |

---

### Opción A — Fly.io (RECOMENDADO — gratis y simple)

#### 1. Instalar flyctl

```bash
curl -L https://fly.io/install.sh | sh
fly auth signup   # o fly auth login
```

#### 2. Crear `Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 8080
CMD ["python", "main.py"]
```

Asegúrate de que en `main.py` el entrypoint tenga `port=8080`:

```python
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8080)
```

#### 3. Desplegar

```bash
fly launch          # Sigue el wizard, elige región más cercana
fly secrets set OWM_API_KEY=tu_api_key_aqui
fly deploy
```

Tu app quedará en: `https://tu-app.fly.dev`

---

### Opción B — Railway

1. Crea cuenta en https://railway.app
2. "New Project" → "Deploy from GitHub Repo"
3. Conecta tu repositorio con `main.py` y `requirements.txt`
4. En **Variables** del proyecto: agrega `OWM_API_KEY = tu_key`
5. En **Settings → Start Command**: `python main.py`
6. Railway asigna un dominio automáticamente

---

### Opción C — Render

1. Crea cuenta en https://render.com
2. "New" → "Web Service" → conecta GitHub
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `python main.py`
5. En **Environment**: agrega `OWM_API_KEY`
6. Elige plan **Free**

---

## ─── 3. Variables de entorno ───────────────────────────────────────────────

| Variable      | Descripción                              | Dónde configurar               |
|---------------|------------------------------------------|-------------------------------|
| `OWM_API_KEY` | API Key de OpenWeatherMap                | `.env` local / panel de la nube|

Obtén tu API Key gratuita en: https://openweathermap.org/api
(Las keys nuevas tardan hasta 2 horas en activarse)

---

## ─── 4. Verificar que todo funciona ───────────────────────────────────────

```bash
# Verifica que la key está cargada
python -c "import os; print('KEY OK' if os.getenv('OWM_API_KEY') else 'KEY FALTANTE')"

# Ejecuta en web local
flet run --web main.py
```

---

## ─── 5. Resumen de cambios aplicados al código ────────────────────────────

| # | Cambio                    | Antes                              | Después                              |
|---|---------------------------|------------------------------------|--------------------------------------|
| 1 | Modo web                  | `ft.app(target=main)`              | `ft.app(..., view=WEB_BROWSER)`      |
| 2 | API Key                   | Hardcodeada en el código           | `os.getenv("OWM_API_KEY")`           |
| 3 | Reloj                     | `threading.Timer(1.0, ...)`        | `async def _clock_loop` + `asyncio.sleep` |
| 4 | Reset status              | `threading.Timer(2.5, ...)`        | `async def _reset_status_after_delay` |
| 5 | Config persistencia       | `open("weather_pro_config.json")`  | `page.client_storage.get/set_async`  |
| 6 | Layout responsivo         | Filas fijas                        | `wrap=True` + `min_width` en containers |
| 7 | Geolocalización           | Thread daemon (se mantiene)        | Thread daemon (compatible con web)   |
