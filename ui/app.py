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

# Encontrar si la estación habitual está en el dataset para seleccionarla por defecto
index_defecto = 0
for idx, nombre in enumerate(estaciones_disponibles):
    if FAVORITA_HABITUAL.lower() in nombre.lower():
        index_defecto = idx
        break

# 2. Input de texto para filtrar la lista en tiempo real
busqueda = st.sidebar.text_input("Filtrar por texto (ej: Juan Peña, Delicias...)", "")

if busqueda:
    estaciones_filtradas = [e for e in estaciones_disponibles if busqueda.lower() in e.lower()]
    if not estaciones_filtradas:
        st.sidebar.warning("No se encontraron estaciones con ese nombre.")
        estaciones_filtradas = estaciones_disponibles
else:
    estaciones_filtradas = estaciones_disponibles

# 3. Desplegable con las estaciones filtradas (o la favorita por defecto)
estacion_seleccionada = st.sidebar.selectbox(
    "Selecciona la estación:",
    options=estaciones_filtradas,
    index=index_defecto if not busqueda and index_defecto < len(estaciones_filtradas) else 0
)

# --- CUERPO PRINCIPAL ---
st.title(f"🚲 Estado en tiempo real: {estacion_seleccionada}")

# Filtrar datos de la estación elegida
df_estacion = df[df['stationName'] == estacion_seleccionada].sort_values('timestamp')

if not df_estacion.empty:
    # Métricas rápidas (última lectura)
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
    st.plotly_chart(fig, width='stretch')
else:
    st.info("Aún no hay lecturas registradas para esta parada.")

# Botón manual de recarga al final de la barra lateral
if st.sidebar.button("🔄 Actualizar datos"):
    st.cache_data.clear()