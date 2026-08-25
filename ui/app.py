import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Configuración de la página
st.set_page_config(page_title="Bizi Zaragoza Live & Analytics", layout="wide", page_icon="\U0001F6B2")

RAW_CSV_URL = "https://raw.githubusercontent.com/Wei94/bizi-zaragoza-stats/refs/heads/main/output/bizi-stats.csv"

# --- NOMBRES DE DÍAS EN ESPAÑOL ---
DIAS_SEMANA = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
    7: "Domingo"
}

@st.cache_data(ttl=300)
def load_data():
    columnas = [
        'timestamp', 'dayOfWeek', 'timeSlot', 'stationId', 
        'stationName', 'bikesAvailable', 'slotsAvailable', 
        'isOperational', 'longitude', 'latitude'
    ]
    df = pd.read_csv(RAW_CSV_URL, header=None, names=columnas, encoding='latin-1', on_bad_lines='skip')
    
    # Limpieza y conversión de tipos
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df['bikesAvailable'] = pd.to_numeric(df['bikesAvailable'], errors='coerce').fillna(0).astype(int)
    df['slotsAvailable'] = pd.to_numeric(df['slotsAvailable'], errors='coerce').fillna(0).astype(int)
    df['dayName'] = df['dayOfWeek'].map(DIAS_SEMANA)
    
    # Extraer solo la hora de timeSlot para agrupaciones (HH)
    df['hour'] = df['timeSlot'].astype(str).str.split(':').str[0].str.zfill(2)
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error al cargar los datos desde GitHub: {e}")
    st.stop()

# --- FUNCIÓN HAVERSINE PARA DISTANCIAS EN KM ---
def haversine_vectorized(lat1, lon1, lat2_vec, lon2_vec):
    R = 6371.0  # Radio de la Tierra en km
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2_vec)
    lon2_rad = np.radians(lon2_vec)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- BARRA LATERAL: Selección de vista y estación principal ---
st.sidebar.title("\U0001F6B2 Bizi Zaragoza")
st.sidebar.markdown("---")

tab_seleccionada = st.sidebar.radio(
    "Selecciona una funcionalidad:",
    [
        "\U0001F4CD Estación y Plan B",
        "\U0001F52E Predicción y Patrones",
        "\U00001F504 Comparador Origen / Destino",
        "\U0001F5FA Mapa Global Zaragoza"
    ]
)

st.sidebar.markdown("---")
st.sidebar.header("\U00001F50D Estación Principal")

# Configurar estación favorita por defecto
FAVORITA_HABITUAL = "S. Juan Peña"
estaciones_disponibles = sorted(df['stationName'].dropna().unique())

index_defecto = 0
for idx, nombre in enumerate(estaciones_disponibles):
    if FAVORITA_HABITUAL.lower() in nombre.lower():
        index_defecto = idx
        break

busqueda = st.sidebar.text_input("Buscar estación por nombre:", "")

if busqueda:
    estaciones_filtradas = [e for e in estaciones_disponibles if busqueda.lower() in e.lower()]
    if not estaciones_filtradas:
        st.sidebar.warning("No se encontraron coincidencias.")
        estaciones_filtradas = estaciones_disponibles
else:
    estaciones_filtradas = estaciones_disponibles

estacion_principal = st.sidebar.selectbox(
    "Estación seleccionada:",
    options=estaciones_filtradas,
    index=index_defecto if not busqueda and index_defecto < len(estaciones_filtradas) else 0
)

if st.sidebar.button("\U00001F504 Recargar Datos"):
    st.cache_data.clear()
    st.rerun()

# Dataframe de la estación seleccionada
df_estacion = df[df['stationName'] == estacion_principal].sort_values('timestamp')

# ==============================================================================
# TAB 1: ESTACIÓN Y PLAN B (ALTERNATIVAS CERCANAS)
# ==============================================================================
if tab_seleccionada == "\U0001F4CD Estación y Plan B":
    st.title(f"\U0001F4CD Estado en Tiempo Real: {estacion_principal}")
    
    if df_estacion.empty:
        st.info("No hay datos disponibles para esta estación.")
    else:
        ultima_lectura = df_estacion.iloc[-1]
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("\U0001F6B2 Bicis Disponibles", int(ultima_lectura['bikesAvailable']))
        col2.metric("\U0000F513 Anclajes Libres", int(ultima_lectura['slotsAvailable']))
        
        capacidad_total = int(ultima_lectura['bikesAvailable']) + int(ultima_lectura['slotsAvailable'])
        col3.metric("\U0000F4C8 Capacidad Total", capacidad_total)
        col4.metric("\U0000F552 Última Actualización", ultima_lectura['timeSlot'])
        
        st.markdown("---")
        
        # Gráfico de evolución de hoy / reciente
        st.subheader("\U0000F4C8 Evolución de Disponibilidad")
        fig_line = px.line(
            df_estacion,
            x='timeSlot',
            y=['bikesAvailable', 'slotsAvailable'],
            labels={'value': 'Cantidad', 'timeSlot': 'Hora', 'variable': 'Métrica'},
            title=f"Histórico reciente en {estacion_principal}",
            markers=True,
            color_discrete_map={'bikesAvailable': '#e63946', 'slotsAvailable': '#457b9d'}
        )
        fig_line.for_each_trace(lambda t: t.update(name='Bicis' if t.name == 'bikesAvailable' else 'Anclajes'))
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Cálculo de Estaciones Cercanas (Plan B)
        st.markdown("---")
        st.subheader("\U0001F6B6 Estaciones Cercanas (Plan B en caso de saturación)")
        
        lat_curr = ultima_lectura['latitude']
        lon_curr = ultima_lectura['longitude']
        
        if pd.notna(lat_curr) and pd.notna(lon_curr) and lat_curr != 0:
            df_latest_all = df.sort_values('timestamp').groupby('stationName').last().reset_index()
            df_latest_all = df_latest_all[df_latest_all['stationName'] != estacion_principal].copy()
            
            df_latest_all['distancia_km'] = haversine_vectorized(
                lat_curr, lon_curr, 
                df_latest_all['latitude'].values, 
                df_latest_all['longitude'].values
            )
            df_latest_all['distancia_m'] = (df_latest_all['distancia_km'] * 1000).round().astype(int)
            
            cercanas = df_latest_all.sort_values('distancia_m').head(3)
            
            col_map, col_list = st.columns([2, 1])
            
            with col_list:
                st.markdown("### Alternativas a pie:")
                for _, row in cercanas.iterrows():
                    st.success(f"**{row['stationName']}** ({row['distancia_m']} m)")
                    st.write(f"\U0001F6B2 Bicis: **{int(row['bikesAvailable'])}** | \U0000F513 Anclajes: **{int(row['slotsAvailable'])}**")
                    st.markdown("---")
            
            with col_map:
                mapa_data = [
                    {
                        'lat': float(lat_curr),
                        'lon': float(lon_curr),
                        'nombre': f"PRINCIPAL: {estacion_principal}",
                        'tipo': 'Principal',
                        'size': 20,
                        'bicis': int(ultima_lectura['bikesAvailable']),
                        'anclajes': int(ultima_lectura['slotsAvailable'])
                    }
                ]
                
                for _, row in cercanas.iterrows():
                    mapa_data.append({
                        'lat': float(row['latitude']),
                        'lon': float(row['longitude']),
                        'nombre': f"Plan B: {row['stationName']} ({int(row['distancia_m'])}m)",
                        'tipo': 'Cercana',
                        'size': 12,
                        'bicis': int(row['bikesAvailable']),
                        'anclajes': int(row['slotsAvailable'])
                    })
                
                df_mapa = pd.DataFrame(mapa_data)
                
                # Nueva sintaxis con scatter_map y map_style
                fig_map = px.scatter_map(
                    df_mapa,
                    lat='lat',
                    lon='lon',
                    color='tipo',
                    size='size',
                    hover_name='nombre',
                    hover_data={'bicis': True, 'anclajes': True, 'tipo': False, 'size': False, 'lat': False, 'lon': False},
                    color_discrete_map={'Principal': '#e63946', 'Cercana': '#457b9d'},
                    height=400
                )
                fig_map.update_layout(
                    map_style="open-street-map",
                    map_center={"lat": float(lat_curr), "lon": float(lon_curr)},
                    map_zoom=14,
                    margin={"r": 0, "t": 0, "l": 0, "b": 0},
                    showlegend=False
                )
                st.plotly_chart(fig_map, use_container_width=True)
                st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("No hay coordenadas válidas para esta estación.")

# ==============================================================================
# TAB 2: PREDICCIÓN Y PATRONES DE COMMUTE
# ==============================================================================
elif tab_seleccionada == "\U0001F52E Predicción y Patrones":
    st.title(f"\U0001F52E Análisis Predictivo y Patrones: {estacion_principal}")
    st.write("Analiza la disponibilidad histórica según el día de la semana y la franja horaria para planificar tu trayecto con antelación.")
    
    if df_estacion.empty:
        st.info("No hay suficiente histórico registrado para esta estación.")
    else:
        col_filtro1, col_filtro2 = st.columns(2)
        
        with col_filtro1:
            dia_sel = st.selectbox("Selecciona un día de la semana:", list(DIAS_SEMANA.values()), index=0)
        
        with col_filtro2:
            hora_sel = st.slider("Selecciona la hora estimada de tu trayecto (HH:00):", 0, 23, 8)
            hora_str = str(hora_sel).zfill(2)
        
        df_dia = df_estacion[df_estacion['dayName'] == dia_sel]
        df_hora = df_dia[df_dia['hour'] == hora_str]
        
        st.markdown("---")
        st.subheader(f"\U0000F4C8 Diagnóstico para los {dia_sel}s a las {hora_str}:00h")
        
        if df_hora.empty:
            st.warning("Aún no tenemos suficientes datos registrados para esa franja horaria específica.")
        else:
            promedio_bicis = df_hora['bikesAvailable'].mean()
            promedio_anclajes = df_hora['slotsAvailable'].mean()
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Promedio de Bicis Esperadas", f"{promedio_bicis:.1f}")
            col_m2.metric("Promedio de Anclajes Libres", f"{promedio_anclajes:.1f}")
            
            if promedio_bicis < 1.5:
                riesgo_txt = "RIESGO ALTO (Suele estar vacía)"
            elif promedio_bicis < 3.5:
                riesgo_txt = "RIESGO MEDIO (Pocas bicis libres)"
            else:
                riesgo_txt = "RIESGO BAJO (Disponibilidad habitual)"
                
            col_m3.metric("Nivel de Riesgo", riesgo_txt)
        
        st.markdown("---")
        st.subheader(f"\U0000F4C5 Perfil de Disponibilidad Promedio ({dia_sel})")
        
        perfil_dia = df_dia.groupby('hour')[['bikesAvailable', 'slotsAvailable']].mean().reset_index()
        
        if not perfil_dia.empty:
            fig_bar = px.bar(
                perfil_dia,
                x='hour',
                y='bikesAvailable',
                title=f"Promedio de bicis disponibles hora a hora en {estacion_principal} ({dia_sel}s)",
                labels={'hour': 'Hora del día', 'bikesAvailable': 'Promedio Bicis'},
                color_discrete_sequence=['#e63946']
            )
            fig_bar.add_hline(y=2, line_dash="dash", line_color="orange", annotation_text="Umbral crítico (2 bicis)")
            st.plotly_chart(fig_bar, use_container_width=True)

# ==============================================================================
# TAB 3: COMPARADOR ORIGEN / DESTINO
# ==============================================================================
elif tab_seleccionada == "\U00001F504 Comparador Origen / Destino":
    st.title("\U00001F504 Comparador de Trayecto (Origen y Destino)")
    st.write("Verifica simultáneamente si tendrás **bicis al salir** de tu origen y **anclajes libres al llegar** a tu destino.")
    
    col_orig, col_dest = st.columns(2)
    
    with col_orig:
        st.subheader("Estación Origen")
        estacion_origen = st.selectbox("Selecciona origen:", estaciones_disponibles, index=index_defecto, key="origen_sel")
    
    with col_dest:
        st.subheader("Estación Destino")
        index_dest = (index_defecto + 5) % len(estaciones_disponibles)
        estacion_destino = st.selectbox("Selecciona destino:", estaciones_disponibles, index=index_dest, key="destino_sel")
    
    df_origen = df[df['stationName'] == estacion_origen].sort_values('timestamp')
    df_destino = df[df['stationName'] == estacion_destino].sort_values('timestamp')
    
    if not df_origen.empty and not df_destino.empty:
        ult_orig = df_origen.iloc[-1]
        ult_dest = df_destino.iloc[-1]
        
        st.markdown("---")
        col_res1, col_res2 = st.columns(2)
        
        with col_res1:
            st.info(f"**Origen:** {estacion_origen}")
            st.metric("\U0001F6B2 Bicis para coger", int(ult_orig['bikesAvailable']))
            if ult_orig['bikesAvailable'] == 0:
                st.error("Sin bicis disponibles actualmente en el origen.")
            else:
                st.success("Hay bicis disponibles para salir.")
                
        with col_res2:
            st.info(f"**Destino:** {estacion_destino}")
            st.metric("\U0000F513 Anclajes para aparcar", int(ult_dest['slotsAvailable']))
            if ult_dest['slotsAvailable'] == 0:
                st.error("Estación destino LLENA. Busca un Plan B cercano.")
            else:
                st.success("Hay hueco para aparcar al llegar.")
                
        st.markdown("---")
        st.subheader("\U0000F4C8 Gráfico Comparativo en Tiempo Real")
        
        df_origen_sub = df_origen[['timeSlot', 'bikesAvailable']].rename(columns={'bikesAvailable': f'Bicis en Origen ({estacion_origen})'})
        df_destino_sub = df_destino[['timeSlot', 'slotsAvailable']].rename(columns={'slotsAvailable': f'Anclajes en Destino ({estacion_destino})'})
        
        merged_route = pd.merge(df_origen_sub, df_destino_sub, on='timeSlot', how='inner')
        
        if not merged_route.empty:
            fig_route = px.line(
                merged_route,
                x='timeSlot',
                y=[f'Bicis en Origen ({estacion_origen})', f'Anclajes en Destino ({estacion_destino})'],
                title="Compatibilidad del trayecto durante el día",
                markers=True,
                color_discrete_map={
                    f'Bicis en Origen ({estacion_origen})': '#e63946',
                    f'Anclajes en Destino ({estacion_destino})': '#2a9d8f'
                }
            )
            st.plotly_chart(fig_route, use_container_width=True)

# ==============================================================================
# TAB 4: MAPA GLOBAL DE CALOR / ESTADO DE ZARAGOZA
# ==============================================================================
elif tab_seleccionada == "\U0001F5FA Mapa Global Zaragoza":
    st.title("\U0001F5FA Mapa Global de la Red Bizi Zaragoza")
    st.write("Vista completa en tiempo real de las estaciones de la ciudad.")
    
    df_latest = df.sort_values('timestamp').groupby('stationName').last().reset_index()
    
    df_latest = df_latest[
        pd.notna(df_latest['latitude']) & 
        pd.notna(df_latest['longitude']) & 
        (df_latest['latitude'] != 0) & 
        (df_latest['longitude'] != 0)
    ].copy()
    
    df_latest['bikesAvailable'] = df_latest['bikesAvailable'].fillna(0).astype(int)
    df_latest['slotsAvailable'] = df_latest['slotsAvailable'].fillna(0).astype(int)
    
    modo_mapa = st.radio("Mostrar en el mapa por:", ["Bicis Disponibles", "Anclajes Libres"], horizontal=True)
    
    col_var = 'bikesAvailable' if modo_mapa == "Bicis Disponibles" else 'slotsAvailable'
    color_scale = "Reds" if modo_mapa == "Bicis Disponibles" else "Blues"
    
    df_latest['marker_size'] = df_latest[col_var].apply(lambda x: max(int(x), 3))
    
    # Nueva sintaxis con scatter_map y map_style
    fig_global = px.scatter_map(
        df_latest,
        lat='latitude',
        lon='longitude',
        size='marker_size',
        color=col_var,
        hover_name='stationName',
        hover_data={'bikesAvailable': True, 'slotsAvailable': True, 'marker_size': False, 'latitude': False, 'longitude': False},
        color_continuous_scale=color_scale,
        size_max=15,
        height=600,
        title=f"Distribución global de {modo_mapa.lower()} en Zaragoza"
    )
    
    fig_global.update_layout(
        map_style="open-street-map",
        map_center={"lat": 41.65606, "lon": -0.87734},
        map_zoom=12,
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    
    st.plotly_chart(fig_global, use_container_width=True)
    
    st.plotly_chart(fig_global, use_container_width=True)
    
    st.markdown("---")
    st.subheader("\U0000F4C8 Métricas Globales del Sistema")
    c_g1, c_g2, c_g3 = st.columns(3)
    c_g1.metric("Estaciones Operativas", len(df_latest))
    c_g2.metric("Total Bicis en Circulación/Estaciones", int(df_latest['bikesAvailable'].sum()))
    c_g3.metric("Total Anclajes Libres en la Red", int(df_latest['slotsAvailable'].sum()))
