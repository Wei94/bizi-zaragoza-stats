import os
import requests
import pandas as pd
from datetime import datetime

# URL de la API de Bizi Zaragoza
API_URL = "https://www.zaragoza.es/sede/servicio/urbanismo-infraestructuras/estacion-bicicleta?rf=markdown&srsname=wgs84&rows=300"
CSV_PATH = "output/bizi-stats.csv"

def fetch_and_append():
    headers = {"Accept": "application/geo+json"}
    response = requests.get(API_URL, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"Error al consultar la API: {response.status_code}")
        return

    data = response.json()
    features = data.get("result", [])
    
    now = datetime.utcnow()
    timestamp = now.strftime("%Y-%m-%d handT%H:%M:%SZ").replace(" hand", "")
    time_slot = now.strftime("%H:%M")
    day_of_week = now.isoweekday() # 1 = Lunes, 7 = Domingo

    rows = []
    for item in features:
        # Extracción compatible con la estructura de Zaragoza
        props = item if "title" in item else item.get("properties", {})
        coords = item.get("geometry", {}).get("coordinates", ["", ""]) if "geometry" in item else ["", ""]
        
        title = props.get("title", "")
        station_id = props.get("id", "")
        station_name = title

        # Si el título viene en formato "81-Tauromaquia", separar ID y Nombre
        if "-" in title:
            parts = title.split("-", 1)
            if parts[0].isdigit():
                station_id = parts[0]
                station_name = parts[1].strip()

        estado = str(props.get("estadoEstacion", "")).lower()
        is_operational = "no-operativa" not in estado

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

    # Asegurar que la carpeta existe
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

    # Anexar al CSV existente sin escribir cabeceras
    df_new.to_csv(CSV_PATH, mode='a', header=False, index=False)
    print(f"[{timestamp}] Se han añadido {len(rows)} registros a {CSV_PATH}")

if __name__ == "__main__":
    fetch_and_append()
