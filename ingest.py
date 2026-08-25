import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

API_URL = "https://www.zaragoza.es/sede/servicio/urbanismo-infraestructuras/estacion-bicicleta?rf=markdown&srsname=wgs84&rows=300"
CSV_PATH = "output/bizi-stats.csv"

# Definición explícita de columnas en el ámbito global
COLUMNS = [
    'timestamp', 'dayOfWeek', 'timeSlot', 'stationId', 
    'stationName', 'bikesAvailable', 'slotsAvailable', 
    'isOperational', 'longitude', 'latitude'
]

def get_session_with_retries():
    """Crea una sesión de requests con 3 reintentos automáticos."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
    
def fetch_and_append():
    headers = {
        "Accept": "application/geo+json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BiziStatsBot/1.0"
    }
    
    session = get_session_with_retries()
    
    try:
        response = session.get(API_URL, headers=headers, timeout=45)
        if response.status_code != 200:
            print(f"Error al consultar la API: Código HTTP {response.status_code}")
            return
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"La API de Zaragoza no respondió a tiempo: {e}")
        return

    features = data.get("features", [])
    if not features:
        print("La API respondió pero 'features' está vacío.")
        return
    
    now = datetime.utcnow()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_slot = now.strftime("%H:%M")
    day_of_week = now.isoweekday()

    rows = []
    for item in features:
        props = item.get("properties", {})
        coords = item.get("geometry", {}).get("coordinates", ["", ""])
        
        title = props.get("title", "")
        station_id = props.get("id", "")
        station_name = title

        if "-" in title:
            parts = title.split("-", 1)
            if parts[0].strip().isdigit():
                station_id = parts[0].strip()
                station_name = parts[1].strip()

        estado = str(props.get("estado", "")).upper()
        is_operational = (estado == "IN_SERVICE")

        rows.append({
            "timestamp": timestamp,
            "dayOfWeek": day_of_week,
            "timeSlot": time_slot,
            "stationId": station_id,
            "stationName": station_name,
            "bikesAvailable": props.get("bicisDisponibles", 0),
            "slotsAvailable": props.get("anclajesDisponibles", 0),
            "isOperational": is_operational,
            "longitude": coords[0] if len(coords) > 0 else "",
            "latitude": coords[1] if len(coords) > 1 else ""
        })

    df_new = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

    # Cargar datos antiguos si el archivo existe y no está vacío
    if os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0:
        df_old = pd.read_csv(CSV_PATH, header=None, names=COLUMNS)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_combined = df_new

    # Filtrar manteniendo solo registros de los últimos 7 días
    df_combined['dt_temp'] = pd.to_datetime(df_combined['timestamp'], format="%Y-%m-%dT%H:%M:%SZ", errors='coerce')
    hace_7_dias = now - timedelta(days=7)
    df_filtered = df_combined[df_combined['dt_temp'] >= hace_7_dias].drop(columns=['dt_temp'])

    # Sobrescribir el CSV con los datos limpios
    df_filtered.to_csv(CSV_PATH, mode='w', header=False, index=False)
    print(f"[{timestamp}] ¡Éxito! CSV actualizado. Registros guardados (últimos 7 días): {len(df_filtered)}")

if __name__ == "__main__":
    fetch_and_append()
