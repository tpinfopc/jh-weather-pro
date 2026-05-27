"""
JH WEATHER PRO v3 — WEB EDITION
By Juan Heit — Estilo PC Analyzer Pro / Suite JH LAB
Migrado a entorno web con Flet 0.24+

Cambios aplicados v3:
  1. Sistema de alertas mejorado con API One Call 3.0 oficial
  2. Scroll horizontal en contenedor de alertas para móviles
  3. Método heurístico de respaldo mejorado (detección precisa de lluvia extrema)
  4. Cálculo correcto de precipitación acumulada en 24h
  5. Alertas por niveles con información oficial de OWM
  6. Corrección visibilidad: lógica heurística basada en weather_id para
     estimar visibilidad real cuando OWM devuelve el tope genérico de 10.000m
"""

import asyncio
import datetime
import os
import threading
import math

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
# ─────────────────────────────────────────────────────────────────────────────
API_KEY  = os.getenv("OWM_API_KEY", "5a8a0445802b0a19a3a6bc8b925f8536")
BASE_URL = "http://api.openweathermap.org/data/2.5"
ONE_CALL_URL = "https://api.openweathermap.org/data/3.0/onecall"
IP_API_URL = "http://ip-api.com/json/"

# Umbrales para alertas heurísticas mejoradas
THRESHOLDS = {
    "rain_extreme": 150.0,    # mm en 24h - ALERTA ROJA
    "rain_heavy": 80.0,       # mm en 24h - ALERTA NARANJA
    "rain_moderate": 40.0,    # mm en 24h - ALERTA AMARILLA
    "wind_extreme": 90.0,     # km/h - ALERTA ROJA
    "wind_heavy": 70.0,       # km/h - ALERTA NARANJA
    "wind_moderate": 50.0,    # km/h - ALERTA AMARILLA
}

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
        "status_alert_official": "● ⚠ ALERTAS OFICIALES ACTIVAS",
        "btn_refresh":          "  ACTUALIZAR  ",
        "btn_share":            "  COMPARTIR  ",
        "btn_search":           "  BUSCAR  ",
        "search_placeholder":   "Ingresá una ciudad (ej: Buenos Aires)",
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
        "footer_features":      "Viento • Visibilidad • Tendencia cada 2h • Alertas oficiales + heurísticas",
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
        "alert_yellow_desc":    "Fenómenos meteorológicos con intensidad moderada. Posibles afectaciones.",
        "alert_orange_desc":    "Fenómenos meteorológicos con intensidad fuerte. Riesgo para actividades.",
        "alert_red_desc":       "Fenómenos meteorológicos con intensidad severa. Peligro para la población.",
        "alert_storm_warning":  "Tormentas fuertes con ráfagas de viento > 70 km/h",
        "alert_heavy_rain":     "Lluvias intensas con acumulados > {}mm en 24h",
        "alert_extreme_rain":   "Lluvias extremas con acumulados > {}mm en 24h",
        "alert_extreme_wind":   "Vientos extremos > 90 km/h",
        "alert_hail":           "Posibilidad de granizo de tamaño considerable",
        "no_alerts":            "✅ SIN ALERTAS ACTIVAS",
        "official_alert":       "ALERTA OFICIAL",
        "from_agency":          "Fuente: {}",
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
        "status_alert_official": "● ⚠ OFFICIAL ALERTS ACTIVE",
        "btn_refresh":          "  REFRESH  ",
        "btn_share":            "  SHARE  ",
        "btn_search":           "  SEARCH  ",
        "search_placeholder":   "Enter a city (e.g., London)",
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
        "footer_features":      "Wind • Visibility • 2h Trend • Official + heuristic alerts",
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
        "alert_yellow_desc":    "Moderate intensity weather phenomena. Possible impacts.",
        "alert_orange_desc":    "Strong intensity weather phenomena. Risk for outdoor activities.",
        "alert_red_desc":       "Severe intensity weather phenomena. Danger to population.",
        "alert_storm_warning":  "Severe storms with wind gusts > 70 km/h",
        "alert_heavy_rain":     "Heavy rain with accumulations > {}mm in 24h",
        "alert_extreme_rain":   "Extreme rain with accumulations > {}mm in 24h",
        "alert_extreme_wind":   "Extreme winds > 90 km/h",
        "alert_hail":           "Possibility of significant hail",
        "no_alerts":            "✅ NO ACTIVE ALERTS",
        "official_alert":       "OFFICIAL ALERT",
        "from_agency":          "Source: {}",
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
    def __init__(self, level: str, title: str, description: str, icon: str, details=None, is_official=False, sender=None):
        self.level = level  # "yellow", "orange", "red"
        self.title = title
        self.description = description
        self.icon = icon
        self.details = details or []
        self.is_official = is_official
        self.sender = sender


# ─────────────────────────────────────────────────────────────────────────────
# CLASE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class WeatherPro:
    """
    Aplicación web de clima con temática Cyberpunk/Dark.
    Sistema de alertas mejorado con API One Call 3.0 oficial.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "JH WEATHER PRO — Suite JH LAB"
        self.page.bgcolor = C["bg"]
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.scroll = ft.ScrollMode.AUTO

        # Geolocator nativo (se agrega al overlay)
        self.geolocator = ft.Geolocator()
        self.page.overlay.append(self.geolocator)

        # Estado interno
        self.current_weather = None
        self.forecast_data = None
        self.one_call_data = None  # Datos de One Call API
        self.hourly_forecast = []
        self.daily_forecasts_data = {}
        self.daily_summary = {}
        self.active_alerts = []
        self.city_name = "Detectando..."
        self.current_city = ""
        self.alert_message = None
        self.use_celsius = True
        self.language = "es"
        self.selected_day = None
        self._clock_running = True
        self.lat = None
        self.lon = None

        # Textos
        self.txt = TEXTS[self.language]

        # Controles UI
        self.status_text = ft.Text(self.txt["status_starting"], color=C["warn"], size=12, weight=ft.FontWeight.BOLD)
        self.clock_text = ft.Text("", color=C["muted"], size=11)
        self.city_display = ft.Text("Detectando ubicación...", color=C["accent"], size=20, weight=ft.FontWeight.BOLD)

        # Búsqueda manual
        self.search_input = ft.TextField(
            hint_text=self.txt["search_placeholder"],
            width=250,
            bgcolor=C["bg"],
            border_color=C["border"],
            color=C["text"],
            text_size=13,
            on_submit=self._on_search_submit,
        )
        self.search_button = self._create_button(self.txt["btn_search"], self._search_city, C["accent"], C["button_text"])

        self.unit_switch = ft.Switch(value=True, on_change=self.toggle_units, active_color=C["accent"])
        self.lang_switch = ft.Switch(value=False, on_change=self.toggle_language, active_color=C["accent2"])

        # Contenedores dinámicos
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
        # Contenedor de alertas CON SCROLL HORIZONTAL para móviles
        self.alerts_scroll = ft.Row(
            spacing=12,
            scroll=ft.ScrollMode.AUTO,  # Esto permite scroll horizontal
        )
        self.alerts_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(self.txt["label_alerts"], size=11, color=C["accent2"], weight=ft.FontWeight.BOLD),
                    ft.Container(content=self.alerts_scroll, padding=ft.padding.only(top=8)),
                ],
                spacing=8,
            ),
            bgcolor=C["panel"], border_radius=10, padding=15, visible=True,
        )
        self.alert_banner = ft.Container(
            visible=False, bgcolor=C["alert_bg"], border_radius=5, padding=10,
            content=ft.Row(
                controls=[
                    ft.Text("⚠️", size=20, color=C["alert_text"]),
                    ft.Text("", color=C["alert_text"], size=12, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.START, spacing=10,
            ),
        )

        if not API_KEY:
            self.status_text.value = self.txt["status_no_apikey"]
            self.status_text.color = C["red"]

        self._build_ui()
        self.page.run_task(self._async_init)

    # ──────────────────────────────────────────────────────────────────────
    # INIT ASÍNCRONO
    # ──────────────────────────────────────────────────────────────────────

    async def _async_init(self):
        await self._load_config()
        self.txt = TEXTS[self.language]
        self.unit_switch.value = self.use_celsius
        self.lang_switch.value = (self.language == "en")
        self.search_input.hint_text = self.txt["search_placeholder"]
        self.search_button.text = self.txt["btn_search"]
        self.page.update()

        self.page.run_task(self._clock_loop)
        await self._request_browser_location()

    # ──────────────────────────────────────────────────────────────────────
    # GEOLOCALIZACIÓN
    # ──────────────────────────────────────────────────────────────────────

    async def _request_browser_location(self):
        self.status_text.value = self.txt["status_detecting"]
        self.status_text.color = C["warn"]
        self.city_display.value = "Solicitando permisos de ubicación..."
        self.page.update()

        is_secure = self.page.web_launch_url.startswith("https") if self.page.web_launch_url else False
        if not is_secure:
            self.status_text.value = "● HTTPS requerido para ubicación precisa"
            self.status_text.color = C["red"]
            self.city_display.value = "Usá la búsqueda manual para obtener el clima"
            self.page.update()
            return

        try:
            pos = await self.geolocator.get_current_position()
            self.lat = pos.latitude
            self.lon = pos.longitude
            self.get_weather_by_coords(self.lat, self.lon)
        except Exception as e:
            self.status_text.value = self.txt["status_error_location"]
            self.status_text.color = C["warn"]
            self.city_display.value = "No se pudo obtener ubicación. Usá la búsqueda manual."
            self.page.update()

    def get_weather_by_coords(self, lat: float, lon: float):
        self.status_text.value = self.txt["status_loading"]
        self.status_text.color = C["warn"]
        self.page.update()
        threading.Thread(target=self._fetch_weather_by_coords, args=(lat, lon), daemon=True).start()

    def _fetch_weather_by_coords(self, lat: float, lon: float):
        try:
            # Obtener clima actual y pronóstico (5 días / 3 horas)
            params = {"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric", "lang": "es"}
            r = requests.get(f"{BASE_URL}/weather", params=params, timeout=10)
            if r.status_code == 401:
                self.status_text.value = self.txt["status_error_apikey"]
                self.status_text.color = C["red"]
                self.page.update()
                self._show_api_key_message()
                return
            r.raise_for_status()
            weather_data = r.json()
            city_name = weather_data.get("name", f"Coordenadas {lat}, {lon}")
            self.current_city = city_name
            self.city_name = city_name
            self.city_display.value = city_name
            self.current_weather = weather_data

            # Pronóstico extendido
            rf = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
            rf.raise_for_status()
            self.forecast_data = rf.json()

            # One Call API 3.0 para alertas oficiales
            self._fetch_one_call_alerts(lat, lon)

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
            self._analyze_alerts_enhanced()  # Versión mejorada con One Call + heurística

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
        except Exception as exc:
            self.status_text.value = f"● Error: {str(exc)[:40]}"
            self.status_text.color = C["red"]
            self.page.update()

    def _fetch_one_call_alerts(self, lat: float, lon: float):
        """Obtiene alertas oficiales de la API One Call 3.0"""
        try:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": API_KEY,
                "exclude": "minutely,hourly,daily",
                "units": "metric"
            }
            response = requests.get(ONE_CALL_URL, params=params, timeout=10)
            if response.status_code == 200:
                self.one_call_data = response.json()
            else:
                self.one_call_data = None
        except Exception as e:
            print(f"Error fetching One Call alerts: {e}")
            self.one_call_data = None

    # ──────────────────────────────────────────────────────────────────────
    # BÚSQUEDA MANUAL
    # ──────────────────────────────────────────────────────────────────────

    def _search_city(self, e):
        city = self.search_input.value.strip()
        if not city:
            self.status_text.value = "● Ingresá el nombre de una ciudad"
            self.status_text.color = C["warn"]
            self.page.update()
            return
        self.get_weather_by_city(city)

    def _on_search_submit(self, e):
        self._search_city(e)

    def get_weather_by_city(self, city: str):
        self.status_text.value = self.txt["status_loading"]
        self.status_text.color = C["warn"]
        self.page.update()
        threading.Thread(target=self._fetch_weather_by_city, args=(city,), daemon=True).start()

    def _fetch_weather_by_city(self, city: str):
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
            weather_data = r.json()
            city_name = weather_data.get("name", city)
            self.current_city = city_name
            self.city_name = city_name
            self.city_display.value = city_name
            self.current_weather = weather_data

            # Guardar coordenadas para One Call
            self.lat = weather_data.get("coord", {}).get("lat")
            self.lon = weather_data.get("coord", {}).get("lon")

            rf = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
            rf.raise_for_status()
            self.forecast_data = rf.json()

            # One Call API para alertas
            if self.lat and self.lon:
                self._fetch_one_call_alerts(self.lat, self.lon)

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
            self._analyze_alerts_enhanced()

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
        except Exception as exc:
            self.status_text.value = f"● Error: {str(exc)[:40]}"
            self.status_text.color = C["red"]
            self.page.update()

    # ──────────────────────────────────────────────────────────────────────
    # PERSISTENCIA
    # ──────────────────────────────────────────────────────────────────────

    async def _load_config(self):
        try:
            celsius = await self.page.client_storage.get_async("jh_weather.use_celsius")
            language = await self.page.client_storage.get_async("jh_weather.language")
            if celsius is not None: self.use_celsius = bool(celsius)
            if language is not None: self.language = str(language)
        except Exception:
            pass

    async def _save_config(self):
        try:
            await self.page.client_storage.set_async("jh_weather.use_celsius", self.use_celsius)
            await self.page.client_storage.set_async("jh_weather.language", self.language)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────
    # RELOJ
    # ──────────────────────────────────────────────────────────────────────

    async def _clock_loop(self):
        while self._clock_running:
            self.clock_text.value = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
            self.page.update()
            await asyncio.sleep(1)

    # ──────────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.txt = TEXTS[self.language]

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

        button_bar = ft.Container(
            content=ft.Row(
                controls=[
                    self._create_button(self.txt["btn_refresh"], self._refresh_weather, C["accent"], C["button_text"]),
                    self._create_button(self.txt["btn_share"], self.share_weather, C["warn"], C["button_text"]),
                    self.search_input,
                    self.search_button,
                ],
                spacing=10, wrap=True,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

        alert_banner_container = ft.Container(
            content=self.alert_banner,
            padding=ft.padding.symmetric(horizontal=20, vertical=5),
        )

        top_row = ft.Row(
            controls=[
                ft.Container(content=self.current_weather_container, width=360),
                ft.Container(content=self.trend_container, width=780),
            ],
            spacing=15, alignment=ft.MainAxisAlignment.START, wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        middle_row = ft.Row(
            controls=[
                ft.Container(content=self.wind_vis_container, width=240),
                ft.Container(content=self.forecast_container, width=900),
            ],
            spacing=15, alignment=ft.MainAxisAlignment.START, wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

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
                    ft.Text(self.txt["footer_ref"], size=9, color=C["muted"]),
                    ft.Text(self.txt["footer_features"], size=8, color=C["muted"]),
                ],
                spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.all(10),
        )

        tip = ft.Container(
            content=ft.Text(self.txt["tip_click"], size=9, color=C["muted"], italic=True),
            padding=10,
        )

        self.page.add(
            header,
            button_bar,
            alert_banner_container,
            location_block,
            ft.Container(content=top_row, padding=ft.padding.symmetric(horizontal=20)),
            ft.Container(content=middle_row, padding=ft.padding.symmetric(horizontal=20)),
            self.alerts_container,
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

    def _refresh_weather(self, e):
        if self.current_city:
            self.get_weather_by_city(self.current_city)
        elif self.lat and self.lon:
            self.get_weather_by_coords(self.lat, self.lon)
        else:
            self.city_display.value = "No hay ciudad seleccionada. Usá la búsqueda."
            self.page.update()

    # ──────────────────────────────────────────────────────────────────────
    # PROCESAMIENTO DE DATOS
    # ──────────────────────────────────────────────────────────────────────

    def _process_hourly_data_by_day(self):
        if not self.forecast_data:
            return
        self.daily_forecasts_data = {}
        for item in self.forecast_data.get("list", []):
            dt = datetime.datetime.fromtimestamp(item["dt"])
            date_key = dt.strftime("%Y-%m-%d")
            weekday = dt.weekday()
            day_name = FULL_DAY_NAMES[self.language][weekday]

            if date_key not in self.daily_forecasts_data:
                self.daily_forecasts_data[date_key] = {"day_name": day_name, "date": dt, "hourly": []}

            rain = 0
            if "rain" in item and "3h" in item["rain"]:
                rain = item["rain"]["3h"]
            elif "rain" in item and "1h" in item["rain"]:
                rain = item["rain"]["1h"] * 3

            self.daily_forecasts_data[date_key]["hourly"].append({
                "hour": dt.strftime("%H:00"),
                "temp": item["main"]["temp"],
                "weather_id": item["weather"][0]["id"],
                "pop": item.get("pop", 0),
                "rain": rain,
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
        result = []
        data_dict = {h["hour"]: h for h in hourly_data}

        for hour in target_hours:
            if hour in data_dict:
                result.append(data_dict[hour])
            else:
                hour_int = int(hour.split(":")[0])
                prev_hour = None
                next_hour = None
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
                    r = (hour_int - ph) / (nh - ph)
                    result.append({
                        "hour": hour,
                        "temp": prev_hour["temp"] + (next_hour["temp"] - prev_hour["temp"]) * r,
                        "weather_id": prev_hour.get("weather_id", 800) if r < 0.5 else next_hour.get("weather_id", 800),
                        "pop": prev_hour.get("pop", 0) + (next_hour.get("pop", 0) - prev_hour.get("pop", 0)) * r,
                        "rain": prev_hour.get("rain", 0) + (next_hour.get("rain", 0) - prev_hour.get("rain", 0)) * r,
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
            hourly = day_data["hourly"]
            total_rain = 0
            max_pop = 0
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
                    max_wid = wid
                    break
                elif 500 <= wid <= 531 and not (200 <= max_wid <= 232):
                    max_wid = wid
                elif 800 <= wid <= 804 and max_wid == 800:
                    max_wid = wid

            # Determinar descripción basada en la precipitación real
            if total_rain > THRESHOLDS["rain_heavy"]:
                description = f"Lluvia extrema: {total_rain:.0f}mm"
            elif total_rain > THRESHOLDS["rain_moderate"]:
                description = f"Lluvia intensa: {total_rain:.0f}mm"
            elif total_rain > 10:
                description = f"Lluvia: {total_rain:.0f}mm"
            elif total_rain > 0:
                description = self.txt["rain_at"].format(self.txt[period_w_rain]) if period_w_rain else "Lluvias dispersas"
            elif 200 <= max_wid <= 232:
                description = "Tormentas"
            elif 500 <= max_wid <= 531:
                description = "Lluvia"
            elif 600 <= max_wid <= 622:
                description = "Nieve"
            elif max_wid == 800:
                description = "Despejado"
            elif 801 <= max_wid <= 804:
                description = "Nublado"
            else:
                description = "Variable"

            self.daily_summary[date_key] = {
                "total_rain": total_rain,
                "description": description,
                "weather_id": max_wid,
                "period": period_w_rain,
            }

    # ──────────────────────────────────────────────────────────────────────
    # SISTEMA DE ALERTAS MEJORADO
    # ──────────────────────────────────────────────────────────────────────

    def _analyze_alerts_enhanced(self):
        """Versión mejorada: combina alertas oficiales de One Call con heurística avanzada"""
        self.active_alerts = []

        # 1. Obtener alertas oficiales de One Call API 3.0
        if self.one_call_data and "alerts" in self.one_call_data:
            for alert in self.one_call_data["alerts"]:
                # Determinar nivel de alerta basado en el contenido
                alert_text = f"{alert.get('event', '')} {alert.get('description', '')}".lower()
                level = self._determine_alert_level_from_text(alert_text)

                self.active_alerts.append(WeatherAlert(
                    level=level,
                    title=alert.get("event", self.txt["official_alert"]),
                    description=alert.get("description", "")[:300],
                    icon="🔴" if level == "red" else ("🟠" if level == "orange" else "🟡"),
                    details=[alert.get("tags", "")] if alert.get("tags") else [],
                    is_official=True,
                    sender=alert.get("sender_name", "Agencia Meteorológica")
                ))

        # 2. Si hay alertas oficiales, mostrar también la heurística como complemento
        self._analyze_heuristic_alerts()

    def _determine_alert_level_from_text(self, text: str) -> str:
        """Determina nivel de alerta basado en el texto de la alerta oficial"""
        text_lower = text.lower()
        if "red" in text_lower or "extreme" in text_lower or "severe" in text_lower:
            return "red"
        if "orange" in text_lower or "heavy" in text_lower or "strong" in text_lower:
            return "orange"
        return "yellow"

    def _analyze_heuristic_alerts(self):
        """Método heurístico mejorado para detectar alertas cuando no hay datos oficiales"""
        if not self.forecast_data or not self.current_weather:
            return

        # Calcular precipitación total en 24h desde los datos de forecast
        total_rain_24h = 0
        max_wind_24h = 0
        has_storm = False
        max_hail_risk = False

        # Obtener velocidad del viento actual
        current_wind = self.current_weather.get("wind", {}).get("speed", 0) * 3.6
        max_wind_24h = current_wind

        # Analizar cada entrada del forecast (cada 3 horas)
        for item in self.forecast_data.get("list", []):
            # Acumular lluvia
            if "rain" in item:
                if "3h" in item["rain"]:
                    total_rain_24h += item["rain"]["3h"]
                elif "1h" in item["rain"]:
                    total_rain_24h += item["rain"]["1h"] * 3

            # Verificar tormentas
            weather_id = item["weather"][0]["id"]
            if 200 <= weather_id <= 232:
                has_storm = True

            # Velocidad del viento en el forecast (convertir de m/s a km/h)
            wind_speed = item.get("wind", {}).get("speed", 0) * 3.6
            if wind_speed > max_wind_24h:
                max_wind_24h = wind_speed

            # Riesgo de granizo en tormentas severas
            if 200 <= weather_id <= 232 and item.get("main", {}).get("temp", 0) < 10:
                max_hail_risk = True

        # Evaluar nivel de alerta por precipitación
        alert_level = None
        alert_reasons = []
        rain_details = []

        # ALERTA ROJA: Lluvia extrema > 150mm
        if total_rain_24h >= THRESHOLDS["rain_extreme"]:
            alert_level = "red"
            rain_details.append(self.txt["alert_extreme_rain"].format(int(THRESHOLDS["rain_extreme"])))
            rain_details.append(f"Acumulado: {total_rain_24h:.1f}mm en 24h")

        # ALERTA NARANJA: Lluvia intensa > 80mm
        elif total_rain_24h >= THRESHOLDS["rain_heavy"]:
            if alert_level is None:
                alert_level = "orange"
            rain_details.append(self.txt["alert_heavy_rain"].format(int(THRESHOLDS["rain_heavy"])))
            rain_details.append(f"Acumulado: {total_rain_24h:.1f}mm en 24h")

        # ALERTA AMARILLA: Lluvia moderada > 40mm
        elif total_rain_24h >= THRESHOLDS["rain_moderate"]:
            if alert_level is None:
                alert_level = "yellow"
            rain_details.append(f"Lluvias significativas: {total_rain_24h:.1f}mm en 24h")

        # Tormentas - eleva el nivel si corresponde
        if has_storm:
            if alert_level is None:
                alert_level = "yellow"
            alert_reasons.append(self.txt["alert_storm_warning"])
            if max_hail_risk:
                alert_reasons.append(self.txt["alert_hail"])

        # Vientos extremos
        if max_wind_24h >= THRESHOLDS["wind_extreme"]:
            alert_level = "red"
            alert_reasons.append(self.txt["alert_extreme_wind"])
            alert_reasons.append(f"Velocidad: {max_wind_24h:.0f} km/h")
        elif max_wind_24h >= THRESHOLDS["wind_heavy"]:
            if alert_level != "red":
                alert_level = "orange"
            alert_reasons.append(f"Vientos fuertes: {max_wind_24h:.0f} km/h")
        elif max_wind_24h >= THRESHOLDS["wind_moderate"]:
            if alert_level is None:
                alert_level = "yellow"
            alert_reasons.append(f"Vientos moderados: {max_wind_24h:.0f} km/h")

        # Agregar razones de lluvia
        alert_reasons.extend(rain_details)

        # Crear alerta heurística si hay condiciones
        if alert_level and alert_reasons:
            titles = {
                "yellow": (self.txt["alert_yellow"], "🟡"),
                "orange": (self.txt["alert_orange"], "🟠"),
                "red": (self.txt["alert_red"], "🔴"),
            }
            lvl_title, icon = titles.get(alert_level, (self.txt["alert_yellow"], "🟡"))

            self.active_alerts.append(WeatherAlert(
                level=alert_level,
                title=lvl_title,
                description=self.txt[f"alert_{alert_level}_desc"],
                icon=icon,
                details=alert_reasons,
                is_official=False
            ))

    def _check_alerts(self):
        if not self.current_weather:
            return
        wid = self.current_weather.get("weather", [{}])[0].get("id", 0)
        wmain = self.current_weather.get("weather", [{}])[0].get("main", "")
        if 200 <= wid <= 232 or wmain in ("Thunderstorm", "Squall"):
            msg = self.txt["alert_storm"] if 200 <= wid <= 232 else self.txt["alert_thunder"]
            self.alert_banner.visible = True
            self.alert_banner.content.controls[1].value = msg
        else:
            self.alert_banner.visible = False
        self.page.update()

    # ──────────────────────────────────────────────────────────────────────
    # ACTUALIZACIÓN DE ALERTAS CON SCROLL HORIZONTAL
    # ──────────────────────────────────────────────────────────────────────

    def _update_alerts_display(self):
        self._analyze_alerts_enhanced()

        # Limpiar el contenedor scrollable
        self.alerts_scroll.controls.clear()

        if not self.active_alerts:
            # Mostrar mensaje de "sin alertas"
            no_alerts_card = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text("✅", size=24, color=C["green"]),
                        ft.Column(controls=[
                            ft.Text(self.txt["no_alerts"], size=14, weight=ft.FontWeight.BOLD, color=C["green"]),
                            ft.Text("Las condiciones meteorológicas actuales no presentan riesgos significativos.",
                                    size=11, color=C["muted"]),
                        ], spacing=4),
                    ],
                    spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=C["bg"], border_radius=10, padding=12,
                border=ft.border.all(1, C["border"]),
                width=900,  # Ancho fijo para que el scroll tenga sentido
            )
            self.alerts_scroll.controls.append(no_alerts_card)
            self.alerts_container.visible = True
            self.page.update()
            return

        # Crear tarjetas de alerta (una por cada alerta)
        for alert in self.active_alerts:
            if alert.level == "yellow":
                bg_c, tx_c = C["alert_yellow"], "#000000"
            elif alert.level == "orange":
                bg_c, tx_c = C["alert_orange"], "#ffffff"
            else:
                bg_c, tx_c = C["alert_red"], "#ffffff"

            # Construir contenido de la alerta
            alert_controls = [
                ft.Row(controls=[
                    ft.Text(alert.icon, size=32),
                    ft.Column(controls=[
                        ft.Row(controls=[
                            ft.Text(alert.title, size=14, weight=ft.FontWeight.BOLD, color=tx_c),
                            ft.Text("📢" if alert.is_official else "⚠️", size=12, color=tx_c),
                        ], spacing=5),
                        ft.Text(alert.description, size=11, color=tx_c),
                    ], spacing=4, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
            ]

            # Añadir detalles si existen
            if alert.details:
                details_text = "\n".join(f"• {d}" for d in alert.details if d)
                if details_text:
                    alert_controls.append(
                        ft.Text(details_text, size=10, color=tx_c)
                    )

            # Añadir fuente si es alerta oficial
            if alert.is_official and alert.sender:
                alert_controls.append(
                    ft.Text(self.txt["from_agency"].format(alert.sender), size=9, color=tx_c, italic=True)
                )

            alert_card = ft.Container(
                content=ft.Column(controls=alert_controls, spacing=8),
                bgcolor=bg_c, border_radius=10, padding=12,
                width=320,  # Ancho fijo para cada tarjeta
            )
            self.alerts_scroll.controls.append(alert_card)

        self.alerts_container.visible = True
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
        main = self.current_weather.get("main", {})
        temp = main.get("temp", 0)
        feels_like = main.get("feels_like", 0)
        humidity = main.get("humidity", 0)
        pressure = main.get("pressure", 0)
        wdesc = self.current_weather.get("weather", [{}])[0].get("description", "")
        wid = self.current_weather.get("weather", [{}])[0].get("id", 800)
        icon = get_weather_icon(wid, datetime.datetime.now().strftime("%H:00"))
        ctmp = self._convert_temp(temp)
        cfeel = self._convert_temp(feels_like)
        tc = get_temp_color(temp)

        cards = ft.Row(
            controls=[
                self._create_info_card("🌡️", self.txt["label_temp"], f"{ctmp:.1f}{self._get_temp_unit()}", tc),
                self._create_info_card("🌡️", self.txt["label_feels"], f"{cfeel:.1f}{self._get_temp_unit()}", C["accent2"]),
                self._create_info_card("💧", self.txt["label_humidity"], f"{humidity}%", C["green"]),
                self._create_info_card("📊", self.txt["label_pressure"], f"{pressure} hPa", C["label"]),
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
        forecast_list = self.forecast_data.get("list", [])
        daily_forecasts = {}

        for item in forecast_list:
            dt = datetime.datetime.fromtimestamp(item["dt"])
            date_key = dt.strftime("%Y-%m-%d")
            weekday = dt.weekday()
            if date_key not in daily_forecasts and len(daily_forecasts) < 5:
                daily_forecasts[date_key] = {
                    "date": dt,
                    "temp": item["main"]["temp"],
                    "weather_id": item["weather"][0]["id"],
                    "weather_desc": item["weather"][0]["description"],
                    "day_name": SHORT_DAY_NAMES[self.language][weekday],
                }

        forecast_cards = []
        for date_key, data in daily_forecasts.items():
            summary = self.daily_summary.get(date_key, {})
            total_rain = summary.get("total_rain", 0)
            description = summary.get("description", data["weather_desc"].capitalize())
            wid = summary.get("weather_id", data["weather_id"])
            icon = get_weather_icon(wid, "12:00")
            ctmp = self._convert_temp(data["temp"])
            tc = get_temp_color(data["temp"])

            rain_text = ""
            if total_rain > 0:
                if total_rain > 80:
                    rain_text = f"🔴 {total_rain:.0f}mm"
                elif total_rain > 40:
                    rain_text = f"🟠 {total_rain:.0f}mm"
                elif total_rain > 10:
                    rain_text = f"🟡 {total_rain:.0f}mm"
                else:
                    rain_text = f"💧 {total_rain:.1f}mm"
            elif summary.get("period"):
                rain_text = f"💧 {self.txt['rain_at'].format(self.txt[summary['period']])}"

            desc_text = description[:20] if len(description) > 20 else description

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
                            ft.Text(rain_text, size=10, color=C["rain_color"] if total_rain > 0 else C["muted"]),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5,
                    ),
                    bgcolor=C["bg"], border_radius=10, padding=12, width=120,
                    border=ft.border.all(1, C["border"]),
                ),
            )
            forecast_cards.append(card)

        self.forecast_container.content = ft.Row(
            controls=forecast_cards,
            spacing=15, wrap=True, alignment=ft.MainAxisAlignment.CENTER,
        )
        self.page.update()

    def _get_real_visibility(self) -> str:
        """
        Calcula la visibilidad real de forma inteligente.
        OWM devuelve 'visibility' en metros con tope de 10.000 m (10 km)
        cuando no tiene datos precisos. Se complementa con el weather_id
        actual para estimar visibilidad real segun condicion meteorologica.
        """
        raw_vis = self.current_weather.get("visibility", None)
        wid = self.current_weather.get("weather", [{}])[0].get("id", 800)

        # Estimar visibilidad segun condicion meteorologica
        estimated = {
            range(200, 233): 2.0,   # Tormenta electrica
            range(300, 322): 4.0,   # Llovizna
            range(500, 502): 6.0,   # Lluvia ligera
            range(502, 532): 3.0,   # Lluvia moderada/intensa
            range(600, 613): 3.0,   # Nieve ligera
            range(613, 623): 1.0,   # Nieve intensa
            range(700, 782): 0.5,   # Niebla, bruma, polvo, arena
            range(800, 801): None,  # Cielo despejado -> usar dato real
            range(801, 805): None,  # Nubes -> usar dato real
        }

        vis_km = None
        if raw_vis is not None:
            vis_km = raw_vis / 1000.0

        # Si OWM devuelve el tope generico (10.000 m), verificar si
        # la condicion climatica sugiere una visibilidad diferente
        if vis_km is not None and raw_vis == 10000:
            for rng, est in estimated.items():
                if wid in rng and est is not None:
                    vis_km = est
                    break

        if vis_km is None:
            return "N/D"

        if vis_km >= 10.0:
            return ">=10 km"
        elif vis_km >= 1.0:
            return f"{vis_km:.1f} km"
        else:
            return f"{int(vis_km * 1000)} m"

    def _update_wind_visibility(self):
        if not self.current_weather:
            self.wind_vis_container.content = ft.Column(
                controls=[ft.Text("⏳ Cargando...", size=12, color=C["muted"])],
                spacing=11,
            )
            self.page.update()
            return
        wind = self.current_weather.get("wind", {})
        wsp = wind.get("speed", 0)
        wdeg = wind.get("deg", 0)
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        wdir = dirs[int((wdeg + 22.5) // 45) % 8] if wdeg else "N/A"
        wkmh = wsp * 3.6
        vis_str = self._get_real_visibility()

        self.wind_vis_container.content = ft.Column(
            controls=[
                ft.Text(self.txt["label_wind_vis"], size=10, color=C["accent2"], weight=ft.FontWeight.BOLD),
                ft.Divider(color=C["border"]),
                ft.Row(controls=[ft.Text("🌬️", size=24), ft.Column(controls=[
                    ft.Text(f"{wkmh:.1f} km/h", size=16, weight=ft.FontWeight.BOLD, color=C["text"]),
                    ft.Text(f"{self.txt['label_direction']}: {wdir}", size=11, color=C["label"]),
                ], spacing=2)], spacing=10),
                ft.Row(controls=[ft.Text("👁️", size=24), ft.Column(controls=[
                    ft.Text(vis_str, size=16, weight=ft.FontWeight.BOLD, color=C["text"]),
                    ft.Text(self.txt["label_visibility"], size=11, color=C["label"]),
                ], spacing=2)], spacing=10),
            ],
            spacing=10,
        )
        self.page.update()

    def _update_trend_display_for_day(self, date_key: str):
        if date_key not in self.daily_forecasts_data:
            return
        day_data = self.daily_forecasts_data[date_key]
        hourly = day_data["hourly"]
        day_name = day_data["day_name"]
        date_str = day_data["date"].strftime("%d/%m")

        if not hourly:
            self.trend_container.visible = False
            return

        self.trend_container.visible = True
        temps_c = [h["temp"] for h in hourly]
        max_temp = max(temps_c)
        min_temp = min(temps_c)

        bars_row = ft.Row(controls=[], spacing=8,
                          alignment=ft.MainAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)

        for hd in hourly:
            tc = hd["temp"]
            td = self._convert_temp(tc)
            icon = get_weather_icon(hd.get("weather_id", 800), hd["hour"])
            pop = hd.get("pop", 0)
            rain = hd.get("rain", 0)
            ri = get_rain_indicator(pop, rain)
            col = get_temp_color(tc)
            h = 30 + ((tc - min_temp) / (max_temp - min_temp) * 70) if max_temp > min_temp else 65
            op = 0.8 if hd.get("interpolated") else 1.0

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
        temps_c = [h["temp"] for h in self.hourly_forecast]
        max_temp = max(temps_c)
        min_temp = min(temps_c)

        bars_row = ft.Row(controls=[], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
        for hd in self.hourly_forecast:
            tc = hd["temp"]
            td = self._convert_temp(tc)
            col = get_temp_color(tc)
            icon = get_weather_icon(hd.get("weather_id", 800), hd["hour"])
            pop = hd.get("pop", 0)
            ri = get_rain_indicator(pop)
            h = 30 + ((tc - min_temp) / (max_temp - min_temp) * 70) if max_temp > min_temp else 65

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
        self.txt = TEXTS[self.language]
        self.page.run_task(self._save_config)
        self.status_text.value = self.txt["status_updated"]
        self.search_input.hint_text = self.txt["search_placeholder"]
        self.search_button.text = self.txt["btn_search"]
        if self.current_city:
            self.get_weather_by_city(self.current_city)
        self._rebuild_ui()

    def share_weather(self, e):
        if not self.current_weather:
            self.status_text.value = "● No hay datos para compartir"
            self.status_text.color = C["red"]
            self.page.update()
            return
        main = self.current_weather.get("main", {})
        temp = main.get("temp", 0)
        desc = self.current_weather.get("weather", [{}])[0].get("description", "")
        hum = main.get("humidity", 0)

        # Añadir información de alertas si las hay
        alert_text = ""
        if self.active_alerts:
            alert_text = f"\n⚠️ ALERTAS: {', '.join([a.title for a in self.active_alerts])}"

        share_text = (
            f"🌤️ JH WEATHER PRO - Reporte Meteorológico\n"
            f"📍 {self.city_name}\n"
            f"🌡️ Temperatura: {self._convert_temp(temp):.1f}{self._get_temp_unit()}\n"
            f"☁️ Condición: {desc.capitalize()}\n"
            f"💧 Humedad: {hum}%{alert_text}\n"
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
        day_name = self.daily_forecasts_data[date_key]["day_name"]
        self.status_text.value = self.txt["status_showing"].format(num_hours, day_name)
        self.status_text.color = C["accent"]
        self.page.update()
        self.page.run_task(self._reset_status_after_delay)

    async def _reset_status_after_delay(self, delay: float = 2.5):
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
                ft.Text(self.txt["dialog_text_apikey"], color=C["text"]),
                ft.Text(self.txt["dialog_text_pending"], color=C["warn"], weight=ft.FontWeight.BOLD),
                ft.Text(self.txt["dialog_suggestions"], color=C["accent"]),
                ft.Text(self.txt["dialog_suggestion1"], color=C["muted"]),
                ft.Text(self.txt["dialog_suggestion2"], color=C["muted"]),
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
    port = int(os.getenv("PORT", 8000))
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        port=port,
    )
    
