import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Bizi Zaragoza Live", layout="wide")

RAW_CSV_URL = "https://raw.githubusercontent.com/Wei94/bizi-zaragoza-stats/refs/heads/main/output/bizi-stats.csv"

@st.cache_data(ttl=300)
def load_data():
    columnas = [
        'timestamp', 'dayOfWeek', 'timeSlot', 'stationId', 
        'stationName', 'bikesAvailable', 'slotsAvailable', 
        'isOperational', 'longitude', 'latitude'
    ]
    return pd.read_csv(RAW_CSV_URL, header=None, names=columnas)

df = load_data()

# --- BARRA LATERAL: Filtros y Búsqueda ---
st.sidebar.header("🔍 Buscar Estación")

# 1. Acceso rápido a Favoritas
FAVORITA_HABITUAL = "S. Juan Peña"
estaciones_disponibles = sorted(df['stationName'].unique())

index_defecto = 0
for idx, nombre in enumerate(estaciones_disponibles):
    if FAVORITA_HABITUAL.lower() in nombre.lower():
        index_defecto = idx
        break

# 2. Input de texto para filtrar la lista
busqueda = st.sidebar.text_input("Filtrar por texto (ej: Juan Peña, Delicias...)", "")

if busqueda:
    estaciones_filtradas = [e for e in estaciones_disponibles if busqueda.lower() in e.lower()]
    if not estaciones_filtradas:
        st.sidebar.warning("No se encontraron estaciones con ese nombre.")
        estaciones_filtradas = estaciones_disponibles
else:
    estaciones_filtradas = estaciones_disponibles

# 3. Desplegable
estacion_seleccionada = st.sidebar.selectbox(
    "Selecciona la estación:",
    options=estaciones_filtradas,
    index=index_defecto if not busqueda and index_defecto < len(estaciones_filtradas) else 0
)

# --- CUERPO PRINCIPAL ---
st.title(f"🚲 Estado en tiempo real: {estacion_seleccionada}")

df_estacion = df[df['stationName'] == estacion_seleccionada].sort_values('timestamp')

if not df_estacion.empty:
    # Métricas rápidas
    ultima_lectura = df_estacion.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Bicis Disponibles", int(ultima_lectura['bikesAvailable']))
    col2.metric("Anclajes Libres", int(ultima_lectura['slotsAvailable']))
    col3.metric("Última Actualización", ultima_lectura['timeSlot'])

    # Gráfico de disponibilidad
    fig = px.line(
        df_estacion, 
        x='timeSlot', 
        y='bikesAvailable', 
        markers=True,
        title=f"Evolución de bicis disponibles en {estacion_seleccionada}",
        labels={'timeSlot': 'Hora', 'bikesAvailable': 'Bicis disponibles'}
    )
    fig.update_traces(line_color='#e63946')
    st.plotly_chart(fig, use_container_width=True)

    # MAPA DE UBICACIÓN
    st.markdown("---")
    st.subheader("📍 Ubicación de la Estación")

    lat = ultima_lectura['latitude']
    lon = ultima_lectura['longitude']

    if pd.notna(lat) and pd.notna(lon) and str(lat).strip() != "" and str(lon).strip() != "":
        df_mapa = pd.DataFrame([{
            'lat': float(lat),
            'lon': float(lon),
            'estacion': estacion_seleccionada,
            'bicis': int(ultima_lectura['bikesAvailable']),
            'anclajes': int(ultima_lectura['slotsAvailable'])
        }])

        fig_map = px.scatter_mapbox(
            df_mapa,
            lat='lat',
            lon='lon',
            hover_name='estacion',
            hover_data={'bicis': True, 'anclajes': True, 'lat': False, 'lon': False},
            zoom=15,
            height=350
        )

        fig_map.update_layout(
            mapbox_style="carto-positron",
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )

        fig_map.update_traces(
            marker=dict(size=18, color='#e63946')
        )

        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning("Esta estación no tiene coordenadas geográficas registradas.")

else:
    st.info("Aún no hay lecturas registradas para esta parada.")

# Botón manual de recarga al final de la barra lateral
if st.sidebar.button("🔄 Actualizar datos"):
    st.cache_data.clear()
