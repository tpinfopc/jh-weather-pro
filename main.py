"""
JH WEATHER PRO v2 — WEB EDITION
By Juan Heit — Estilo PC Analyzer Pro / Suite JH LAB
Migrado a entorno web con Flet 0.24+

Cambios aplicados:
  1. ft.app con view=ft.AppView.WEB_BROWSER
  2. API Key via os.getenv("OWM_API_KEY") — compatible con Netlify/Vercel env vars
  3. threading.Timer reemplazado por asyncio; geoloc y llamadas HTTP en async threads
  4. Responsividad con wrap=True / expand en filas dinámicas
  5. Persistencia via page.client_storage (sin archivos físicos)

Requiere: pip install flet requests
"""

import asyncio
import datetime
import os
import threading

import flet as ft
import requests

# ─────────────────────────────────────────────────────────────────────────────
# PALETA CYBERPUNK / DARK MODE
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "bg":           "#0a0c10",
    "panel":        "#0f1318",
    "border":       "#1e2a38",
    "accent":       "#00d4ff",
    "accent2":      "#ff6b35",
    "green":        "#39ff14",
    "warn":         "#ffc107",
    "text":         "#c8d8e8",
    "muted":        "#4a6070",
    "label":        "#7a9bb0",
    "red":          "#ff4444",
    "alert_bg":     "#ff8c00",
    "alert_text":   "#ffffff",
    "button_text":  "#000000",
    "rain_color":   "#4dabff",
    "temp_cold":    "#4dabff",
    "temp_cool":    "#6c9eff",
    "temp_mild":    "#ffd966",
    "temp_warm":    "#ffa64d",
    "temp_hot":     "#ff6b35",
    "temp_very_hot":"#ff4444",
    "alert_yellow": "#ffcc00",
    "alert_orange": "#ff8800",
    "alert_red":    "#ff3300",
}

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN API  — ⚠️ NUNCA hardcodear la key en producción
# En Netlify/Vercel: Settings → Environment Variables → OWM_API_KEY
# En local: crea un archivo .env con:  OWM_API_KEY=tu_key_aqui
#           y ejecuta `export $(cat .env)` antes de `flet run --web main.py`
# ─────────────────────────────────────────────────────────────────────────────
API_KEY  = os.getenv("OWM_API_KEY", "5a8a0445802b0a19a3a6bc8b925f8536")          # Vacío → mostrará aviso en UI
BASE_URL = "http://api.openweathermap.org/data/2.5"
IP_API_URL = "http://ip-api.com/json/"

# ─────────────────────────────────────────────────────────────────────────────
# TEXTOS INTERNACIONALIZACIÓN ES / EN
# ─────────────────────────────────────────────────────────────────────────────
TEXTS = {
    "es": {
        "title": "JH WEATHER PRO - BY JH LAB",
        "status_starting":      "● Iniciando...",
        "status_detecting":     "● Detectando ubicación...",
        "status_loading":       "● Obteniendo datos meteorológicos...",
        "status_updated":       "● DATOS ACTUALIZADOS",
        "status_error_location":"● Error de geolocalización",
        "status_error_apikey":  "● Error: API Key inválida o no activada aún",
        "status_copied":        "● Clima copiado al portapapeles ✓",
        "status_showing":       "● Mostrando {} mediciones para {}",
        "status_no_apikey":     "● ⚠ Falta OWM_API_KEY en las variables de entorno",
        "btn_refresh":          "  ACTUALIZAR  ",
        "btn_share":            "  COMPARTIR  ",
        "label_location":       "UBICACIÓN ACTUAL",
        "label_current":        "CLIMA ACTUAL",
        "label_wind_vis":       "VIENTO Y VISIBILIDAD",
        "label_trend":          "TENDENCIA HORARIA",
        "label_temp":           "Temperatura",
        "label_feels":          "Sensación",
        "label_humidity":       "Humedad",
        "label_pressure":       "Presión",
        "label_wind":           "Viento",
        "label_direction":      "Dirección",
        "label_visibility":     "Visibilidad",
        "label_min":            "Min",
        "label_max":            "Max",
        "label_measurements":   "mediciones",
        "label_rain_prob":      "Lluvia",
        "label_precip":         "Precip",
        "label_total_rain":     "Lluvia total",
        "label_alerts":         "⚠️ ALERTAS METEOROLÓGICAS",
        "tip_click":            "💡 Haz clic en cualquier día para ver su tendencia horaria (cada 2h)",
        "footer_ref":           "REFERENCIA — DATOS PROPORCIONADOS POR OPENWEATHERMAP",
        "footer_features":      "Viento • Visibilidad • Tendencia cada 2h • Alertas por niveles",
        "dialog_title_copied":  "CLIMA COPIADO",
        "dialog_text_copied":   "La información del clima ha sido copiada al portapapeles.\nPuedes pegarla en cualquier lugar.",
        "dialog_title_apikey":  "API KEY NO ACTIVADA",
        "dialog_text_apikey":   "La API Key de OpenWeatherMap puede tardar hasta 2 horas en activarse.",
        "dialog_text_pending":  "Estado actual: Pendiente de activación",
        "dialog_suggestions":   "Sugerencias:",
        "dialog_suggestion1":   "• Espera 30-60 minutos y vuelve a intentar",
        "dialog_suggestion2":   "• Verifica que la API Key sea correcta",
        "alert_storm":          "⚠ ALERTA: Tormentas fuertes en tu área. Precaución al salir.",
        "alert_thunder":        "⚠ ALERTA: Condiciones de tormenta eléctrica detectadas.",
        "unit_celsius":         "°C/°F",
        "lang_es":              "ES",
        "lang_en":              "EN",
        "morning":              "mañana",
        "afternoon":            "tarde",
        "night":                "noche",
        "rain_at":              "Lluvia por la {}",
        "alert_yellow":         "ALERTA AMARILLA",
        "alert_orange":         "ALERTA NARANJA",
        "alert_red":            "ALERTA ROJA",
        "alert_yellow_desc":    "Fenómenos meteorológicos con intensidad leve. Posibles afectaciones menores.",
        "alert_orange_desc":    "Fenómenos meteorológicos con intensidad moderada. Riesgo para actividades al aire libre.",
        "alert_red_desc":       "Fenómenos meteorológicos con intensidad severa. Peligro para la población. Tomar medidas preventivas.",
        "alert_storm_warning":  "Tormentas fuertes con ráfagas de viento > 70 km/h",
        "alert_heavy_rain":     "Lluvias intensas con acumulados > 50mm en 24h",
        "alert_extreme_wind":   "Vientos extremos > 90 km/h",
        "alert_hail":           "Posibilidad de granizo de tamaño considerable",
        "no_alerts":            "✅ SIN ALERTAS ACTIVAS",
    },
    "en": {
        "title": "JH WEATHER PRO BY JH LAB",
        "status_starting":      "● Starting...",
        "status_detecting":     "● Detecting location...",
        "status_loading":       "● Getting weather data...",
        "status_updated":       "● DATA UPDATED",
        "status_error_location":"● Geolocation error",
        "status_error_apikey":  "● Error: Invalid API Key or not activated yet",
        "status_copied":        "● Weather copied to clipboard ✓",
        "status_showing":       "● Showing {} measurements for {}",
        "status_no_apikey":     "● ⚠ OWM_API_KEY missing from environment variables",
        "btn_refresh":          "  REFRESH  ",
        "btn_share":            "  SHARE  ",
        "label_location":       "CURRENT LOCATION",
        "label_current":        "CURRENT WEATHER",
        "label_wind_vis":       "WIND & VISIBILITY",
        "label_trend":          "HOURLY TREND",
        "label_temp":           "Temperature",
        "label_feels":          "Feels like",
        "label_humidity":       "Humidity",
        "label_pressure":       "Pressure",
        "label_wind":           "Wind",
        "label_direction":      "Direction",
        "label_visibility":     "Visibility",
        "label_min":            "Min",
        "label_max":            "Max",
        "label_measurements":   "measurements",
        "label_rain_prob":      "Rain",
        "label_precip":         "Precip",
        "label_total_rain":     "Total rain",
        "label_alerts":         "⚠️ WEATHER ALERTS",
        "tip_click":            "💡 Click on any day to see hourly trend (every 2h)",
        "footer_ref":           "REFERENCE — DATA PROVIDED BY OPENWEATHERMAP",
        "footer_features":      "Wind • Visibility • 2h Trend • Level-based alerts",
        "dialog_title_copied":  "WEATHER COPIED",
        "dialog_text_copied":   "Weather information has been copied to clipboard.\nYou can paste it anywhere.",
        "dialog_title_apikey":  "API KEY NOT ACTIVATED",
        "dialog_text_apikey":   "OpenWeatherMap API Key may take up to 2 hours to activate.",
        "dialog_text_pending":  "Current status: Pending activation",
        "dialog_suggestions":   "Suggestions:",
        "dialog_suggestion1":   "• Wait 30-60 minutes and try again",
        "dialog_suggestion2":   "• Verify that the API Key is correct",
        "alert_storm":          "⚠ ALERT: Severe storms in your area. Be careful.",
        "alert_thunder":        "⚠ ALERT: Thunderstorm conditions detected.",
        "unit_celsius":         "°C/°F",
        "lang_es":              "ES",
        "lang_en":              "EN",
        "morning":              "morning",
        "afternoon":            "afternoon",
        "night":                "night",
        "rain_at":              "Rain in the {}",
        "alert_yellow":         "YELLOW ALERT",
        "alert_orange":         "ORANGE ALERT",
        "alert_red":            "RED ALERT",
        "alert_yellow_desc":    "Meteorological phenomena with mild intensity. Possible minor impacts.",
        "alert_orange_desc":    "Meteorological phenomena with moderate intensity. Risk for outdoor activities.",
        "alert_red_desc":       "Meteorological phenomena with severe intensity. Danger to population. Take preventive measures.",
        "alert_storm_warning":  "Severe storms with wind gusts > 70 km/h",
        "alert_heavy_rain":     "Heavy rain with accumulations > 50mm in 24h",
        "alert_extreme_wind":   "Extreme winds > 90 km/h",
        "alert_hail":           "Possibility of significant hail",
        "no_alerts":            "✅ NO ACTIVE ALERTS",
    },
}

FULL_DAY_NAMES = {
    "es": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}
SHORT_DAY_NAMES = {
    "es": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_temp_color(temp_celsius: float) -> str:
    if temp_celsius <= 10:  return C["temp_cold"]
    if temp_celsius <= 15:  return C["temp_cool"]
    if temp_celsius <= 20:  return C["temp_mild"]
    if temp_celsius <= 25:  return C["temp_warm"]
    if temp_celsius <= 30:  return C["temp_hot"]
    return C["temp_very_hot"]


def get_weather_icon(weather_id: int, hour: str = None) -> str:
    is_night = False
    if hour is not None:
        try:
            is_night = int(hour.split(":")[0]) >= 20 or int(hour.split(":")[0]) <= 6
        except ValueError:
            pass

    if 200 <= weather_id <= 232: return "⛈️"
    if 300 <= weather_id <= 321: return "🌧️"
    if 500 <= weather_id <= 531: return "🌧️"
    if 600 <= weather_id <= 622: return "❄️"
    if 700 <= weather_id <= 781: return "🌫️"
    if weather_id == 800: return "🌙" if is_night else "☀️"
    if weather_id == 801: return "☁️🌙" if is_night else "🌤️"
    if weather_id == 802: return "☁️🌙" if is_night else "⛅"
    if weather_id in (803, 804): return "☁️"
    return "🌡️"


def get_rain_indicator(pop, rain_3h=None) -> str:
    if not pop:
        return ""
    pop_pct = int(pop * 100)
    if pop_pct < 30:
        return f"💧 {pop_pct}%"
    if pop_pct < 70:
        return f"🌧️ {pop_pct}%"
    if rain_3h and rain_3h > 0:
        return f"🌧️💧 {pop_pct}% ({rain_3h:.1f}mm)"
    return f"🌧️ {pop_pct}%"


def get_period_from_hour(hour_str: str) -> str:
    hour = int(hour_str.split(":")[0])
    if 6 <= hour < 12: return "morning"
    if 12 <= hour < 18: return "afternoon"
    return "night"


# ─────────────────────────────────────────────────────────────────────────────
# MODELO DE ALERTA
# ─────────────────────────────────────────────────────────────────────────────

class WeatherAlert:
    def __init__(self, level: str, title: str, description: str, icon: str, details=None):
        self.level       = level
        self.title       = title
        self.description = description
        self.icon        = icon
        self.details     = details or []


# ─────────────────────────────────────────────────────────────────────────────
# CLASE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class WeatherPro:
    """
    Aplicación web de clima con temática Cyberpunk/Dark.

    Cambios clave respecto a la versión de escritorio:
      • _load_config / _save_config  → page.client_storage (async)
      • _update_clock               → asyncio.create_task (sin threading.Timer)
      • detect_location / get_weather_by_city → threading.Thread daemon=True
        (Flet web tolera threads daemon; asyncio.run_in_executor también funciona)
      • _reset_status_text          → asyncio.sleep en corrutina
      • top_row / middle_row        → wrap=True para responsividad móvil
      • window_width / height       eliminados (no aplican en web)
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title              = "JH WEATHER PRO — Suite JH LAB"
        self.page.bgcolor            = C["bg"]
        self.page.padding            = 0
        self.page.theme_mode         = ft.ThemeMode.DARK
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.scroll             = ft.ScrollMode.AUTO

        # Estado interno
        self.current_weather      = None
        self.forecast_data        = None
        self.hourly_forecast      = []
        self.daily_forecasts_data = {}
        self.daily_summary        = {}
        self.active_alerts        = []
        self.city_name            = "Detectando..."
        self.current_city         = ""
        self.alert_message        = None
        self.use_celsius          = True
        self.language             = "es"
        self.selected_day         = None
        self._clock_running       = True

        # Textos (se setean después de cargar config)
        self.txt = TEXTS[self.language]

        # Controles UI compartidos entre builds
        self.status_text  = ft.Text(self.txt["status_starting"], color=C["warn"], size=12, weight=ft.FontWeight.BOLD)
        self.clock_text   = ft.Text("", color=C["muted"], size=11)
        self.city_display = ft.Text("Detectando ubicación...", color=C["accent"], size=20, weight=ft.FontWeight.BOLD)
        self.unit_switch  = ft.Switch(value=True,  on_change=self.toggle_units,    active_color=C["accent"])
        self.lang_switch  = ft.Switch(value=False, on_change=self.toggle_language, active_color=C["accent2"])

        # Contenedores dinámicos
        # min_height no existe en Flet <=0.24; se simula con un spacer Container
        # que los métodos _update_* reemplazan al llegar los datos reales.
        self.current_weather_container = ft.Container(
            content=ft.Column(
                controls=[ft.Text("⏳ Detectando...", color=C["muted"], size=12)],
                spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=C["panel"], border_radius=10, padding=20,
        )
        self.forecast_container = ft.Container(
            content=ft.Column(
                controls=[ft.Text("⏳ Detectando...", color=C["muted"], size=12)],
                spacing=10,
            ),
            bgcolor=C["panel"], border_radius=10, padding=20,
        )
        self.trend_container = ft.Container(
            content=ft.Column(
                controls=[ft.Text("⏳ Detectando...", color=C["muted"], size=12)],
                spacing=10,
            ),
            bgcolor=C["panel"], border_radius=10, padding=20, visible=False,
        )
        self.wind_vis_container = ft.Container(
            content=ft.Column(
                controls=[ft.Text("⏳ Detectando...", color=C["muted"], size=12)],
                spacing=10,
            ),
            bgcolor=C["panel"], border_radius=10, padding=20,
        )
        self.alerts_container = ft.Container(
            content=ft.Column(spacing=8),
            bgcolor=C["panel"], border_radius=10, padding=15, visible=False,
        )
        self.alert_banner = ft.Container(
            visible=False, bgcolor=C["alert_bg"], border_radius=5, padding=10,
            content=ft.Row(
                controls=[
                    ft.Text("⚠️", size=20, color=C["alert_text"]),
                    ft.Text("",   color=C["alert_text"], size=12, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.START, spacing=10,
            ),
        )

        # Verificar API key
        if not API_KEY:
            self.status_text.value = self.txt["status_no_apikey"]
            self.status_text.color = C["red"]

        self._build_ui()

        # Lanzar reloj async y carga de config + geolocalización
        page.run_task(self._async_init)

    # ──────────────────────────────────────────────────────────────────────
    # INIT ASÍNCRONO (reemplaza __init__ diferido)
    # ──────────────────────────────────────────────────────────────────────

    async def _async_init(self):
        """Carga config desde client_storage, luego lanza reloj y geoloc."""
        await self._load_config()
        self.txt = TEXTS[self.language]
        self.unit_switch.value = self.use_celsius
        self.lang_switch.value = (self.language == "en")
        self.page.update()

        # Reloj en tiempo real — corrutina sin threading.Timer
        self.page.run_task(self._clock_loop)

        # Geolocalización en thread daemon para no bloquear el event loop
        if API_KEY:
            threading.Thread(target=self._detect_location_thread, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────
    # PERSISTENCIA — page.client_storage  (reemplaza JSON en disco)
    # ──────────────────────────────────────────────────────────────────────

    async def _load_config(self):
        """Lee preferencias desde el localStorage del navegador."""
        try:
            celsius  = await self.page.client_storage.get_async("jh_weather.use_celsius")
            language = await self.page.client_storage.get_async("jh_weather.language")
            if celsius  is not None: self.use_celsius = bool(celsius)
            if language is not None: self.language    = str(language)
        except Exception:
            pass  # Primera visita o storage no disponible

    async def _save_config(self):
        """Persiste preferencias en el localStorage del navegador."""
        try:
            await self.page.client_storage.set_async("jh_weather.use_celsius", self.use_celsius)
            await self.page.client_storage.set_async("jh_weather.language",    self.language)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────
    # RELOJ EN TIEMPO REAL — asyncio (reemplaza threading.Timer recursivo)
    # ──────────────────────────────────────────────────────────────────────

    async def _clock_loop(self):
        """Actualiza el reloj cada segundo sin bloquear el hilo principal."""
        while self._clock_running:
            self.clock_text.value = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
            self.page.update()
            await asyncio.sleep(1)

    # ──────────────────────────────────────────────────────────────────────
    # CONSTRUCCIÓN DE UI
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.txt = TEXTS[self.language]

        # ── Header ──────────────────────────────────────────────────────
        header = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(self.txt["title"], size=20, weight=ft.FontWeight.BOLD, color=C["accent"]),
                    ft.Container(
                        content=ft.Row(
                            controls=[ft.Text("🔧", size=14, color=C["green"]), self.status_text],
                            spacing=5,
                        )
                    ),
                    ft.Row(
                        controls=[
                            ft.Text(self.txt["unit_celsius"], size=11, color=C["label"]),
                            self.unit_switch,
                            ft.Text(self.txt["lang_es"], size=10,
                                    color=C["accent"] if self.language == "es" else C["muted"]),
                            self.lang_switch,
                            ft.Text(self.txt["lang_en"], size=10,
                                    color=C["accent2"] if self.language == "en" else C["muted"]),
                            self.clock_text,
                        ],
                        alignment=ft.MainAxisAlignment.END, spacing=5, wrap=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True,
            ),
            bgcolor="#070a0d",
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
        )

        # ── Barra de botones ─────────────────────────────────────────────
        button_bar = ft.Container(
            content=ft.Row(
                controls=[
                    self._create_button(self.txt["btn_refresh"], self.refresh_data, C["accent"], C["button_text"]),
                    self._create_button(self.txt["btn_share"],   self.share_weather, C["warn"],  C["button_text"]),
                ],
                spacing=10, wrap=True,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

        alert_banner_container = ft.Container(
            content=self.alert_banner,
            padding=ft.padding.symmetric(horizontal=20, vertical=5),
        )

        # ── Filas responsivas (wrap=True para móvil) ─────────────────────
        #    expand= y width= simultáneos colapsan en Flet web → solo width.
        #    Los anchos proporcionales se logran con expand sin width fijo.
        # expand=N dentro de Row con wrap=True no funciona en Flet web;
        # se usan contenedores con width relativo al viewport.
        # En desktop se ven lado a lado; en móvil (wrap=True) se apilan.
        top_row = ft.Row(
            controls=[
                ft.Container(
                    content=self.current_weather_container,
                    width=360,
                ),
                ft.Container(
                    content=self.trend_container,
                    width=780,
                ),
            ],
            spacing=15,
            alignment=ft.MainAxisAlignment.START,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        middle_row = ft.Row(
            controls=[
                ft.Container(
                    content=self.wind_vis_container,
                    width=240,
                ),
                ft.Container(
                    content=self.forecast_container,
                    width=900,
                ),
            ],
            spacing=15,
            alignment=ft.MainAxisAlignment.START,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        alerts_section = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(self.txt["label_alerts"], size=11, color=C["accent2"], weight=ft.FontWeight.BOLD),
                    self.alerts_container,
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
        )

        # ── Bloque de ubicación ──────────────────────────────────────
        location_block = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(self.txt["label_location"], size=11, color=C["label"]),
                    self.city_display,
                ],
                spacing=5,
            ),
            padding=ft.padding.only(left=20, top=20),
        )

        footer = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Divider(color=C["border"]),
                    ft.Text(self.txt["footer_ref"],      size=9, color=C["muted"]),
                    ft.Text(self.txt["footer_features"], size=8, color=C["muted"]),
                ],
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.all(10),
        )

        tip = ft.Container(
            content=ft.Text(self.txt["tip_click"], size=9, color=C["muted"], italic=True),
            padding=ft.padding.only(left=20, top=5, bottom=5),
        )

        # page.scroll = AUTO → page.add() actúa como una lista vertical simple.
        # Cada control se apila sin necesidad de expand ni Column intermedio.
        self.page.add(
            header,
            button_bar,
            alert_banner_container,
            location_block,
            ft.Container(content=top_row,    padding=ft.padding.symmetric(horizontal=20)),
            ft.Container(content=middle_row, padding=ft.padding.symmetric(horizontal=20)),
            alerts_section,
            tip,
            footer,
        )

    def _rebuild_ui(self):
        self.page.controls.clear()
        self._build_ui()
        self.page.update()

    def _create_button(self, text: str, on_click, bg: str, fg: str, border_color: str = None):
        return ft.ElevatedButton(
            text=text,
            on_click=on_click,
            style=ft.ButtonStyle(
                bgcolor=bg, color=fg,
                overlay_color=C["border"],
                shape=ft.RoundedRectangleBorder(radius=5),
                side=ft.BorderSide(1, border_color) if border_color else None,
            ),
        )

    # ──────────────────────────────────────────────────────────────────────
    # GEOLOCALIZACIÓN Y CLIMA
    # ──────────────────────────────────────────────────────────────────────

    def detect_location(self):
        self.status_text.value = self.txt["status_detecting"]
        self.status_text.color = C["warn"]
        self.page.update()
        threading.Thread(target=self._detect_location_thread, daemon=True).start()

    def _detect_location_thread(self):
        try:
            response = requests.get(IP_API_URL, timeout=10)
            data     = response.json()
            if data.get("status") == "success":
                city    = data.get("city", "")
                country = data.get("country", "")
                self.city_name         = f"{city}, {country}"
                self.current_city      = city
                self.city_display.value = self.city_name
                self.page.update()
                self.get_weather_by_city(city)
            else:
                self.city_display.value  = "No se pudo detectar ubicación"
                self.status_text.value   = self.txt["status_error_location"]
                self.status_text.color   = C["red"]
                self.page.update()
        except Exception as exc:
            self.city_display.value = "Error de conexión"
            self.status_text.value  = f"● Error: {str(exc)[:40]}"
            self.status_text.color  = C["red"]
            self.page.update()

    def get_weather_by_city(self, city: str):
        """Lanza la petición HTTP en un thread daemon para no bloquear la UI."""
        self.status_text.value = self.txt["status_loading"]
        self.status_text.color = C["warn"]
        self.page.update()
        threading.Thread(target=self._fetch_weather, args=(city,), daemon=True).start()

    def _fetch_weather(self, city: str):
        try:
            params = {"q": city, "appid": API_KEY, "units": "metric", "lang": "es"}

            r = requests.get(f"{BASE_URL}/weather", params=params, timeout=10)
            if r.status_code == 401:
                self.status_text.value = self.txt["status_error_apikey"]
                self.status_text.color = C["red"]
                self.page.update()
                self._show_api_key_message()
                return
            if r.status_code == 404:
                self.status_text.value = f"● Error: Ciudad '{city}' no encontrada"
                self.status_text.color = C["red"]
                self.page.update()
                return
            r.raise_for_status()
            self.current_weather = r.json()
            self.current_city    = city

            rf = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
            rf.raise_for_status()
            self.forecast_data = rf.json()

            # Datos horarios próximas 24 h
            self.hourly_forecast = []
            for item in self.forecast_data.get("list", [])[:8]:
                dt = datetime.datetime.fromtimestamp(item["dt"])
                rain = 0
                if "rain" in item:
                    rain = item["rain"].get("3h", item["rain"].get("1h", 0) * 3)
                self.hourly_forecast.append({
                    "hour": dt.strftime("%H:00"),
                    "temp": item["main"]["temp"],
                    "weather_id": item["weather"][0]["id"],
                    "pop": item.get("pop", 0),
                    "rain": rain,
                })

            self._process_hourly_data_by_day()
            self._calculate_daily_summary()
            self._analyze_alerts()

            if self.daily_forecasts_data:
                first_day = list(self.daily_forecasts_data.keys())[0]
                self.selected_day = first_day
                self._update_trend_display_for_day(first_day)

            self._check_alerts()
            self._update_current_weather()
            self._update_forecast()
            self._update_wind_visibility()
            self._update_alerts_display()

            self.status_text.value = self.txt["status_updated"]
            self.status_text.color = C["green"]
            self.page.update()

        except requests.exceptions.RequestException as exc:
            msg = str(exc)
            if "401" in msg:
                self.status_text.value = "● Error: API Key inválida"
            elif "404" in msg:
                self.status_text.value = "● Error: Ciudad no encontrada"
            else:
                self.status_text.value = f"● Error: {msg[:40]}"
            self.status_text.color = C["red"]
            self.page.update()
        except Exception as exc:
            self.status_text.value = f"● Error: {str(exc)[:40]}"
            self.status_text.color = C["red"]
            self.page.update()

    # ──────────────────────────────────────────────────────────────────────
    # PROCESAMIENTO DE DATOS
    # ──────────────────────────────────────────────────────────────────────

    def _process_hourly_data_by_day(self):
        if not self.forecast_data:
            return
        self.daily_forecasts_data = {}
        for item in self.forecast_data.get("list", []):
            dt       = datetime.datetime.fromtimestamp(item["dt"])
            date_key = dt.strftime("%Y-%m-%d")
            weekday  = dt.weekday()
            day_name = FULL_DAY_NAMES[self.language][weekday]

            if date_key not in self.daily_forecasts_data:
                self.daily_forecasts_data[date_key] = {"day_name": day_name, "date": dt, "hourly": []}

            rain = 0
            if "rain" in item and "3h" in item["rain"]:
                rain = item["rain"]["3h"]

            self.daily_forecasts_data[date_key]["hourly"].append({
                "hour":         dt.strftime("%H:00"),
                "temp":         item["main"]["temp"],
                "weather_id":   item["weather"][0]["id"],
                "pop":          item.get("pop", 0),
                "rain":         rain,
                "interpolated": False,
            })

        for date_key in self.daily_forecasts_data:
            self.daily_forecasts_data[date_key]["hourly"].sort(key=lambda x: x["hour"])
            self.daily_forecasts_data[date_key]["hourly"] = self._interpolate_temperatures(
                self.daily_forecasts_data[date_key]["hourly"]
            )

    def _interpolate_temperatures(self, hourly_data):
        if not hourly_data:
            return []
        target_hours = [f"{h:02d}:00" for h in range(0, 24, 2)]
        result       = []
        data_dict    = {h["hour"]: h for h in hourly_data}

        for hour in target_hours:
            if hour in data_dict:
                result.append(data_dict[hour])
            else:
                hour_int   = int(hour.split(":")[0])
                prev_hour  = None
                next_hour  = None
                for h in hourly_data:
                    h_int = int(h["hour"].split(":")[0])
                    if h_int < hour_int:
                        if prev_hour is None or h_int > int(prev_hour["hour"].split(":")[0]):
                            prev_hour = h
                    elif h_int > hour_int:
                        if next_hour is None or h_int < int(next_hour["hour"].split(":")[0]):
                            next_hour = h

                if prev_hour and next_hour:
                    ph = int(prev_hour["hour"].split(":")[0])
                    nh = int(next_hour["hour"].split(":")[0])
                    r  = (hour_int - ph) / (nh - ph)
                    result.append({
                        "hour":         hour,
                        "temp":         prev_hour["temp"] + (next_hour["temp"] - prev_hour["temp"]) * r,
                        "weather_id":   prev_hour.get("weather_id", 800) if r < 0.5 else next_hour.get("weather_id", 800),
                        "pop":          prev_hour.get("pop", 0)  + (next_hour.get("pop", 0)  - prev_hour.get("pop", 0))  * r,
                        "rain":         prev_hour.get("rain", 0) + (next_hour.get("rain", 0) - prev_hour.get("rain", 0)) * r,
                        "interpolated": True,
                    })
                elif prev_hour:
                    result.append({**prev_hour, "hour": hour, "interpolated": True})
                elif next_hour:
                    result.append({**next_hour, "hour": hour, "interpolated": True})
        return result

    def _calculate_daily_summary(self):
        self.daily_summary = {}
        for date_key, day_data in self.daily_forecasts_data.items():
            hourly        = day_data["hourly"]
            total_rain    = 0
            max_pop       = 0
            period_w_rain = None

            for hd in hourly:
                total_rain += hd.get("rain", 0)
                pop = hd.get("pop", 0)
                if pop > max_pop:
                    max_pop = pop
                    if pop > 0.3:
                        period_w_rain = get_period_from_hour(hd["hour"])

            max_wid = 800
            for hd in hourly:
                wid = hd.get("weather_id", 800)
                if 200 <= wid <= 232:
                    max_wid = wid; break
                elif 500 <= wid <= 531 and not (200 <= max_wid <= 232):
                    max_wid = wid
                elif 800 <= wid <= 804 and max_wid == 800:
                    max_wid = wid

            if total_rain > 0:
                description = self.txt["rain_at"].format(self.txt[period_w_rain]) if period_w_rain else "Lluvias dispersas"
            elif 200 <= max_wid <= 232: description = "Tormentas"
            elif 500 <= max_wid <= 531: description = "Lluvia"
            elif 600 <= max_wid <= 622: description = "Nieve"
            elif max_wid == 800:        description = "Despejado"
            elif 801 <= max_wid <= 804: description = "Nublado"
            else:                       description = "Variable"

            self.daily_summary[date_key] = {
                "total_rain":  total_rain,
                "description": description,
                "weather_id":  max_wid,
                "period":      period_w_rain,
            }

    # ──────────────────────────────────────────────────────────────────────
    # ALERTAS
    # ──────────────────────────────────────────────────────────────────────

    def _analyze_alerts(self):
        self.active_alerts = []
        if not self.forecast_data or not self.current_weather:
            return

        wind_speed  = self.current_weather.get("wind", {}).get("speed", 0) * 3.6
        weather_id  = self.current_weather.get("weather", [{}])[0].get("id", 800)
        today       = datetime.datetime.now().date()
        tomorrow    = today + datetime.timedelta(days=1)

        total_rain_24h  = 0
        max_wind_24h    = wind_speed
        has_storm       = False
        has_heavy_rain  = False

        for date_key, day_data in self.daily_forecasts_data.items():
            if day_data["date"].date() in (today, tomorrow):
                for hd in day_data["hourly"]:
                    total_rain_24h += hd.get("rain", 0)
                    if 200 <= hd.get("weather_id", 800) <= 232:
                        has_storm = True
                    if hd.get("rain", 0) > 10:
                        has_heavy_rain = True

        for hd in self.hourly_forecast:
            if 200 <= hd.get("weather_id", 800) <= 232:
                has_storm = True

        alert_level   = None
        alert_reasons = []

        if has_storm:
            alert_level = "orange"
            alert_reasons.append(self.txt["alert_storm_warning"])

        if total_rain_24h > 50:
            alert_level = "orange" if alert_level != "red" else alert_level
            alert_reasons.append(f"{self.txt['alert_heavy_rain']} ({total_rain_24h:.0f}mm en 24h)")
        elif total_rain_24h > 30:
            if alert_level is None: alert_level = "yellow"
            alert_reasons.append(f"Lluvias moderadas: {total_rain_24h:.0f}mm en 24h")
        elif total_rain_24h > 15:
            if alert_level is None: alert_level = "yellow"
            alert_reasons.append(f"Lluvias: {total_rain_24h:.0f}mm en 24h")

        if max_wind_24h > 90:
            alert_level = "red"
            alert_reasons.append(self.txt["alert_extreme_wind"])
        elif max_wind_24h > 70:
            if alert_level != "red": alert_level = "orange"
            alert_reasons.append(f"Vientos fuertes: {max_wind_24h:.0f} km/h")
        elif max_wind_24h > 50:
            if alert_level is None: alert_level = "yellow"
            alert_reasons.append(f"Vientos moderados: {max_wind_24h:.0f} km/h")

        if has_storm and (200 <= weather_id <= 232):
            alert_reasons.append(self.txt["alert_hail"])

        if alert_level and alert_reasons:
            titles = {
                "yellow": (self.txt["alert_yellow"], C["alert_yellow"]),
                "orange": (self.txt["alert_orange"], C["alert_orange"]),
                "red":    (self.txt["alert_red"],    C["alert_red"]),
            }
            lvl_title, _ = titles.get(alert_level, (self.txt["alert_yellow"], C["alert_yellow"]))
            self.active_alerts.append(WeatherAlert(
                level=alert_level,
                title=lvl_title,
                description=self.txt[f"alert_{alert_level}_desc"],
                icon="⚠️" if alert_level == "yellow" else "🔶" if alert_level == "orange" else "🔴",
                details=alert_reasons,
            ))

    def _check_alerts(self):
        if not self.current_weather:
            return
        wid  = self.current_weather.get("weather", [{}])[0].get("id", 0)
        wmain = self.current_weather.get("weather", [{}])[0].get("main", "")
        if 200 <= wid <= 232 or wmain in ("Thunderstorm", "Squall"):
            msg = self.txt["alert_storm"] if 200 <= wid <= 232 else self.txt["alert_thunder"]
            self.alert_banner.visible = True
            self.alert_banner.content.controls[1].value = msg
        else:
            self.alert_banner.visible = False
        self.page.update()

    def _update_alerts_display(self):
        self._analyze_alerts()
        if not self.active_alerts:
            self.alerts_container.visible = True
            self.alerts_container.content = ft.Column(
                controls=[ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text("✅", size=20, color=C["green"]),
                            ft.Column(controls=[
                                ft.Text(self.txt["no_alerts"], size=12, weight=ft.FontWeight.BOLD, color=C["green"]),
                                ft.Text("Las condiciones meteorológicas actuales no presentan riesgos significativos.",
                                        size=11, color=C["muted"]),
                            ], spacing=4),
                        ],
                        spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=C["bg"], border_radius=10, padding=12,
                    border=ft.border.all(1, C["border"]),
                )],
                spacing=8,
            )
            self.page.update()
            return

        self.alerts_container.visible = True
        alert_controls = []
        for alert in self.active_alerts:
            if alert.level == "yellow":
                bg_c, tx_c = C["alert_yellow"], "#000000"
            elif alert.level == "orange":
                bg_c, tx_c = C["alert_orange"], "#ffffff"
            else:
                bg_c, tx_c = C["alert_red"],    "#ffffff"

            details_text = "\n".join(f"• {d}" for d in alert.details) if alert.details else ""
            alert_controls.append(ft.Container(
                content=ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Text(alert.icon, size=28),
                        ft.Text(alert.title, size=14, weight=ft.FontWeight.BOLD, color=tx_c),
                    ], spacing=10),
                    ft.Text(alert.description, size=11, color=tx_c),
                    ft.Text(details_text, size=10, color=tx_c) if details_text else ft.Container(),
                ], spacing=8),
                bgcolor=bg_c, border_radius=10, padding=12,
                margin=ft.margin.only(bottom=10),
            ))
        self.alerts_container.content = ft.Column(
            controls=alert_controls, spacing=10,
        )
        self.page.update()

    # ──────────────────────────────────────────────────────────────────────
    # ACTUALIZACIÓN DE WIDGETS
    # ──────────────────────────────────────────────────────────────────────

    def _update_current_weather(self):
        if not self.current_weather:
            self.current_weather_container.content = ft.Column(
                controls=[ft.Text("⏳ Cargando datos...", size=14, color=C["muted"])],
                spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
            self.page.update()
            return
        main        = self.current_weather.get("main", {})
        temp        = main.get("temp", 0)
        feels_like  = main.get("feels_like", 0)
        humidity    = main.get("humidity", 0)
        pressure    = main.get("pressure", 0)
        wdesc       = self.current_weather.get("weather", [{}])[0].get("description", "")
        wid         = self.current_weather.get("weather", [{}])[0].get("id", 800)
        icon        = get_weather_icon(wid, datetime.datetime.now().strftime("%H:00"))
        ctmp        = self._convert_temp(temp)
        cfeel       = self._convert_temp(feels_like)
        tc          = get_temp_color(temp)

        cards = ft.Row(
            controls=[
                self._create_info_card("🌡️", self.txt["label_temp"],     f"{ctmp:.1f}{self._get_temp_unit()}", tc),
                self._create_info_card("🌡️", self.txt["label_feels"],    f"{cfeel:.1f}{self._get_temp_unit()}", C["accent2"]),
                self._create_info_card("💧", self.txt["label_humidity"],  f"{humidity}%", C["green"]),
                self._create_info_card("📊", self.txt["label_pressure"],  f"{pressure} hPa", C["label"]),
            ],
            spacing=15, wrap=True, alignment=ft.MainAxisAlignment.CENTER,
        )
        self.current_weather_container.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(icon, size=48),
                        ft.Column(controls=[
                            ft.Text(f"{ctmp:.1f}{self._get_temp_unit()}", size=36, weight=ft.FontWeight.BOLD, color=tc),
                            ft.Text(wdesc.capitalize(), size=14, color=C["label"]),
                        ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=20,
                ),
                cards,
            ],
            spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.page.update()

    def _create_info_card(self, icon: str, label: str, value: str, color: str):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(icon, size=24),
                    ft.Text(label, size=10, color=C["label"]),
                    ft.Text(value, size=14, weight=ft.FontWeight.BOLD, color=color),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5,
            ),
            bgcolor=C["bg"], border_radius=8, padding=10, width=120,
            border=ft.border.all(1, C["border"]),
        )

    def _update_forecast(self):
        if not self.forecast_data:
            self.forecast_container.content = ft.Column(
                controls=[ft.Text("⏳ Cargando pronóstico...", size=12, color=C["muted"])],
                spacing=11,
            )
            self.page.update()
            return
        forecast_list    = self.forecast_data.get("list", [])
        daily_forecasts  = {}

        for item in forecast_list:
            dt       = datetime.datetime.fromtimestamp(item["dt"])
            date_key = dt.strftime("%Y-%m-%d")
            weekday  = dt.weekday()
            if date_key not in daily_forecasts and len(daily_forecasts) < 5:
                daily_forecasts[date_key] = {
                    "date":         dt,
                    "temp":         item["main"]["temp"],
                    "weather_id":   item["weather"][0]["id"],
                    "weather_desc": item["weather"][0]["description"],
                    "day_name":     SHORT_DAY_NAMES[self.language][weekday],
                }

        forecast_cards = []
        for date_key, data in daily_forecasts.items():
            summary     = self.daily_summary.get(date_key, {})
            total_rain  = summary.get("total_rain", 0)
            description = summary.get("description", data["weather_desc"].capitalize())
            wid         = summary.get("weather_id", data["weather_id"])
            icon        = get_weather_icon(wid, "12:00")
            ctmp        = self._convert_temp(data["temp"])
            tc          = get_temp_color(data["temp"])

            rain_text = ""
            if total_rain > 0:
                rain_text = f"🌧️ {total_rain:.1f}mm"
            elif summary.get("period"):
                rain_text = f"💧 {self.txt['rain_at'].format(self.txt[summary['period']])}"

            desc_text = description[:15] if len(description) > 15 else description

            card = ft.GestureDetector(
                on_tap=lambda e, dk=date_key: self._on_day_click(dk),
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(data["day_name"], size=14, weight=ft.FontWeight.BOLD, color=C["accent"]),
                            ft.Text(data["date"].strftime("%d/%m"), size=10, color=C["label"]),
                            ft.Text(icon, size=32),
                            ft.Text(f"{ctmp:.0f}{self._get_temp_unit()}", size=18,
                                    weight=ft.FontWeight.BOLD, color=tc),
                            ft.Text(desc_text, size=10, color=C["muted"]),
                            ft.Text(rain_text,  size=10, color=C["rain_color"] if total_rain > 0 else C["muted"]),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5,
                    ),
                    bgcolor=C["bg"], border_radius=10, padding=12, width=120,
                    border=ft.border.all(1, C["border"]),
                ),
            )
            forecast_cards.append(card)

        # Re-asignar la Row (puede haber sido Column en init)
        self.forecast_container.content = ft.Row(
            controls=forecast_cards,
            spacing=15, wrap=True, alignment=ft.MainAxisAlignment.CENTER,
        )
        self.page.update()

    def _update_wind_visibility(self):
        if not self.current_weather:
            self.wind_vis_container.content = ft.Column(
                controls=[ft.Text("⏳ Cargando...", size=12, color=C["muted"])],
                spacing=11,
            )
            self.page.update()
            return
        wind    = self.current_weather.get("wind", {})
        wsp     = wind.get("speed", 0)
        wdeg    = wind.get("deg", 0)
        vis     = self.current_weather.get("visibility", 0) / 1000
        dirs    = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        wdir    = dirs[int((wdeg + 22.5) // 45) % 8] if wdeg else "N/A"
        wkmh    = wsp * 3.6

        self.wind_vis_container.content = ft.Column(
            controls=[
                ft.Text(self.txt["label_wind_vis"], size=10, color=C["accent2"], weight=ft.FontWeight.BOLD),
                ft.Divider(color=C["border"]),
                ft.Row(controls=[ft.Text("🌬️", size=24), ft.Column(controls=[
                    ft.Text(f"{wkmh:.1f} km/h", size=16, weight=ft.FontWeight.BOLD, color=C["text"]),
                    ft.Text(f"{self.txt['label_direction']}: {wdir}", size=11, color=C["label"]),
                ], spacing=2)], spacing=10),
                ft.Row(controls=[ft.Text("👁️", size=24), ft.Column(controls=[
                    ft.Text(f"{vis:.1f} km", size=16, weight=ft.FontWeight.BOLD, color=C["text"]),
                    ft.Text(self.txt["label_visibility"], size=11, color=C["label"]),
                ], spacing=2)], spacing=10),
            ],
            spacing=10,
        )
        self.page.update()

    def _update_trend_display_for_day(self, date_key: str):
        if date_key not in self.daily_forecasts_data:
            return
        day_data   = self.daily_forecasts_data[date_key]
        hourly     = day_data["hourly"]
        day_name   = day_data["day_name"]
        date_str   = day_data["date"].strftime("%d/%m")

        if not hourly:
            self.trend_container.visible = False
            return

        self.trend_container.visible = True
        temps_c  = [h["temp"] for h in hourly]
        max_temp = max(temps_c)
        min_temp = min(temps_c)

        bars_row = ft.Row(controls=[], spacing=8,
                          alignment=ft.MainAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)

        for hd in hourly:
            tc   = hd["temp"]
            td   = self._convert_temp(tc)
            icon = get_weather_icon(hd.get("weather_id", 800), hd["hour"])
            pop  = hd.get("pop", 0)
            rain = hd.get("rain", 0)
            ri   = get_rain_indicator(pop, rain)
            col  = get_temp_color(tc)
            h    = 30 + ((tc - min_temp) / (max_temp - min_temp) * 70) if max_temp > min_temp else 65
            op   = 0.8 if hd.get("interpolated") else 1.0

            bars_row.controls.append(ft.Column(
                controls=[
                    ft.Text(icon, size=22),
                    ft.Container(width=40, height=h, bgcolor=col,
                                 border_radius=ft.border_radius.only(top_left=5, top_right=5), opacity=op),
                    ft.Text(f"{td:.0f}{self._get_temp_unit()}", size=12, color=C["text"]),
                    ft.Text(hd["hour"], size=12, color=C["muted"]),
                    ft.Text(ri, size=10, color=C["rain_color"] if pop > 0 else C["muted"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
            ))

        self.trend_container.content = ft.Column(
            controls=[
                ft.Row(controls=[
                    ft.Text(f"📅 {day_name} {date_str}", size=12, color=C["accent"], weight=ft.FontWeight.BOLD),
                    ft.Text(" • ", size=10, color=C["muted"]),
                    ft.Text(f"{self.txt['label_min']}: {self._convert_temp(min_temp):.1f}{self._get_temp_unit()}",
                            size=10, color=C["temp_cold"]),
                    ft.Text(f"{self.txt['label_max']}: {self._convert_temp(max_temp):.1f}{self._get_temp_unit()}",
                            size=10, color=C["temp_hot"]),
                    ft.Text(f"• {len(hourly)} {self.txt['label_measurements']}", size=9, color=C["muted"]),
                ], spacing=5),
                ft.Divider(color=C["border"]),
                bars_row,
            ],
            spacing=10,
        )
        self.page.update()

    def _update_trend_display(self):
        if not self.hourly_forecast:
            self.trend_container.visible = False
            return
        self.trend_container.visible = True
        temps_c  = [h["temp"] for h in self.hourly_forecast]
        max_temp = max(temps_c)
        min_temp = min(temps_c)

        bars_row = ft.Row(controls=[], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
        for hd in self.hourly_forecast:
            tc   = hd["temp"]
            td   = self._convert_temp(tc)
            col  = get_temp_color(tc)
            icon = get_weather_icon(hd.get("weather_id", 800), hd["hour"])
            pop  = hd.get("pop", 0)
            ri   = get_rain_indicator(pop)
            h    = 30 + ((tc - min_temp) / (max_temp - min_temp) * 70) if max_temp > min_temp else 65

            bars_row.controls.append(ft.Column(
                controls=[
                    ft.Text(icon, size=20),
                    ft.Container(width=40, height=h, bgcolor=col,
                                 border_radius=ft.border_radius.only(top_left=5, top_right=5)),
                    ft.Text(f"{td:.0f}{self._get_temp_unit()}", size=9, color=C["text"]),
                    ft.Text(hd["hour"], size=9, color=C["muted"]),
                    ft.Text(ri, size=8, color=C["rain_color"] if pop > 0 else C["muted"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
            ))

        self.trend_container.content = ft.Column(
            controls=[
                ft.Text(f"{self.txt['label_trend']} (24h)", size=10, color=C["accent"], weight=ft.FontWeight.BOLD),
                ft.Text(
                    f"{self.txt['label_min']}: {self._convert_temp(min_temp):.1f}{self._get_temp_unit()}  |  "
                    f"{self.txt['label_max']}: {self._convert_temp(max_temp):.1f}{self._get_temp_unit()}",
                    size=9, color=C["muted"],
                ),
                bars_row,
            ],
            spacing=10,
        )
        self.page.update()

    # ──────────────────────────────────────────────────────────────────────
    # ACCIONES DE USUARIO
    # ──────────────────────────────────────────────────────────────────────

    def toggle_units(self, e):
        self.use_celsius = self.unit_switch.value
        self.page.run_task(self._save_config)
        if self.current_weather:
            self._update_current_weather()
            self._update_forecast()
            if self.selected_day:
                self._update_trend_display_for_day(self.selected_day)
            else:
                self._update_trend_display()

    def toggle_language(self, e):
        self.language = "en" if self.lang_switch.value else "es"
        self.txt      = TEXTS[self.language]
        self.page.run_task(self._save_config)
        self.status_text.value = self.txt["status_updated"]
        if self.current_city:
            self.get_weather_by_city(self.current_city)
        self._rebuild_ui()

    def refresh_data(self, e):
        if self.current_city:
            self.get_weather_by_city(self.current_city)

    def share_weather(self, e):
        if not self.current_weather:
            self.status_text.value = "● No hay datos para compartir"
            self.status_text.color = C["red"]
            self.page.update()
            return
        main  = self.current_weather.get("main", {})
        temp  = main.get("temp", 0)
        desc  = self.current_weather.get("weather", [{}])[0].get("description", "")
        hum   = main.get("humidity", 0)
        share_text = (
            f"🌤️ JH WEATHER PRO - Reporte Meteorológico\n"
            f"📍 {self.city_name}\n"
            f"🌡️ Temperatura: {self._convert_temp(temp):.1f}{self._get_temp_unit()}\n"
            f"☁️ Condición: {desc.capitalize()}\n"
            f"💧 Humedad: {hum}%\n"
            f"📅 {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"Datos proporcionados por OpenWeatherMap"
        )
        self.page.set_clipboard(share_text)
        self.status_text.value = self.txt["status_copied"]
        self.status_text.color = C["green"]
        self.page.update()
        self._show_share_confirmation()

    def _on_day_click(self, date_key: str):
        self.selected_day = date_key
        self._update_trend_display_for_day(date_key)
        num_hours = len(self.daily_forecasts_data[date_key]["hourly"])
        day_name  = self.daily_forecasts_data[date_key]["day_name"]
        self.status_text.value = self.txt["status_showing"].format(num_hours, day_name)
        self.status_text.color = C["accent"]
        self.page.update()
        # Reemplaza threading.Timer con una corrutina async
        self.page.run_task(self._reset_status_after_delay)

    async def _reset_status_after_delay(self, delay: float = 2.5):
        """Reemplaza threading.Timer(2.5, ...) — sin bloquear el navegador."""
        await asyncio.sleep(delay)
        self.status_text.value = self.txt["status_updated"]
        self.status_text.color = C["green"]
        self.page.update()

    # ──────────────────────────────────────────────────────────────────────
    # DIÁLOGOS
    # ──────────────────────────────────────────────────────────────────────

    def _show_share_confirmation(self):
        def close(e):
            dialog.open = False
            self.page.update()
        dialog = ft.AlertDialog(
            title=ft.Text(self.txt["dialog_title_copied"], color=C["green"]),
            content=ft.Text(self.txt["dialog_text_copied"], color=C["text"]),
            actions=[ft.TextButton("Aceptar" if self.language == "es" else "OK", on_click=close)],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _show_api_key_message(self):
        def close(e):
            dialog.open = False
            self.page.update()
        dialog = ft.AlertDialog(
            title=ft.Text(self.txt["dialog_title_apikey"], color=C["warn"], weight=ft.FontWeight.BOLD),
            content=ft.Column(controls=[
                ft.Text(self.txt["dialog_text_apikey"],    color=C["text"]),
                ft.Text(self.txt["dialog_text_pending"],   color=C["warn"], weight=ft.FontWeight.BOLD),
                ft.Text(self.txt["dialog_suggestions"],    color=C["accent"]),
                ft.Text(self.txt["dialog_suggestion1"],    color=C["muted"]),
                ft.Text(self.txt["dialog_suggestion2"],    color=C["muted"]),
            ], spacing=10),
            actions=[ft.TextButton("Cerrar" if self.language == "es" else "Close", on_click=close)],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    # ──────────────────────────────────────────────────────────────────────
    # UTILIDADES
    # ──────────────────────────────────────────────────────────────────────

    def _convert_temp(self, celsius: float) -> float:
        return celsius if self.use_celsius else (celsius * 9 / 5) + 32

    def _get_temp_unit(self) -> str:
        return "°C" if self.use_celsius else "°F"


# ─────────────────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

def main(page: ft.Page):
    WeatherPro(page)


if __name__ == "__main__":
    # ── Modo WEB ──────────────────────────────────────────────────────────
    # Para local:    flet run --web main.py
    # Para producción (Netlify / Vercel): ver guía en README
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        # port=8080,   # descomenta si necesitas un puerto fijo
    )
