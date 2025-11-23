import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
import time
import numpy as np

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="El Joc de Barris - LA Finder", layout="wide")

# Mantenemos solo el fondo de pantalla, sin los estilos de tarjetas complejas
def add_bg_from_url():
    st.markdown(
         f"""
         <style>
         .stApp {{
             background-image: url("https://images.unsplash.com/photo-1540650490933-d82724082648?q=80&w=2000&auto=format&fit=crop");
             background-attachment: fixed;
             background-size: cover;
         }}
         [data-testid="stAppViewContainer"] > .main {{
             background-color: rgba(0,0,0,0.7); 
         }}
         h1, h2, h3, p, div, span, label, li {{
             color: white !important;
         }}
         </style>
         """,
         unsafe_allow_html=True
     )

add_bg_from_url()

# --- 2. API OPENSTREETMAP ---
@st.cache_data(show_spinner=False)
def get_real_osm_data(lat, lon, radius=1500):
    """Consulta Overpass API."""
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    query = f"""
    [out:json];
    (
      node["amenity"~"bar|pub|nightclub"](around:{radius},{lat},{lon});
      way["amenity"~"bar|pub|nightclub"](around:{radius},{lat},{lon});
    ) -> .bares;
    (
      node["leisure"="park"](around:{radius},{lat},{lon});
      way["leisure"="park"](around:{radius},{lat},{lon});
      node["landuse"="recreation_ground"](around:{radius},{lat},{lon});
    ) -> .parques;
    (
      node["highway"="bus_stop"](around:{radius},{lat},{lon});
      node["railway"~"subway_entrance|station"](around:{radius},{lat},{lon});
    ) -> .transporte;
    
    .bares out count;
    .parques out count;
    .transporte out count;
    """
    
    try:
        response = requests.post(overpass_url, data=query, timeout=25)
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            def extract_count(idx):
                if idx < len(elements):
                    tags = elements[idx].get('tags', {})
                    return int(tags.get('total', 0))
                return 0
            return {
                'bares_count': extract_count(0),
                'parques_count': extract_count(1),
                'transporte_count': extract_count(2)
            }
    except Exception as e:
        pass
    return {'bares_count': 0, 'parques_count': 0, 'transporte_count': 0}

# --- 3. CARGA Y ALGORITMO (LA PARTE NUEVA) ---
@st.cache_data
def load_data_with_api():
    # Datos con POBLACIÓN para el nuevo algoritmo
    barrios = [
        {'barrio': 'Bel Air', 'lat': 34.1002, 'lon': -118.4595, 'poblacion': 5000},
        {'barrio': 'Beverly Hills', 'lat': 34.0736, 'lon': -118.4004, 'poblacion': 15000},
        {'barrio': 'Pasadena', 'lat': 34.1478, 'lon': -118.1445, 'poblacion': 25000},
        {'barrio': 'Santa Monica', 'lat': 34.0195, 'lon': -118.4912, 'poblacion': 30000},
        {'barrio': 'Venice Beach', 'lat': 33.9850, 'lon': -118.4695, 'poblacion': 30000},
        {'barrio': 'Silver Lake', 'lat': 34.0869, 'lon': -118.2702, 'poblacion': 25000},
        {'barrio': 'West Hollywood', 'lat': 34.0900, 'lon': -118.3617, 'poblacion': 35000},
        {'barrio': 'Downtown LA', 'lat': 34.0407, 'lon': -118.2468, 'poblacion': 60000},
        {'barrio': 'Koreatown', 'lat': 34.0618, 'lon': -118.3004, 'poblacion': 70000},
        {'barrio': 'Compton', 'lat': 33.8958, 'lon': -118.2201, 'poblacion': 40000}
    ]
    
    results = []
    progress_text = "📡 Conectando con satélite..."
    my_bar = st.progress(0, text=progress_text)
    
    for i, b in enumerate(barrios):
        real_data = get_real_osm_data(b['lat'], b['lon'])
        b.update({
            'fiesta': real_data['bares_count'],
            'naturaleza': real_data['parques_count'],
            'movilidad': real_data['transporte_count'],
            # Datos estáticos
            'seguridad': {'Beverly Hills': 10, 'Bel Air': 10, 'Pasadena': 8, 'Santa Monica': 7, 'West Hollywood': 7, 'Silver Lake': 6, 'Venice Beach': 5, 'Koreatown': 4, 'Downtown LA': 3, 'Compton': 2}[b['barrio']],
            'lujo_privacidad': {'Beverly Hills': 10, 'Bel Air': 10, 'Santa Monica': 8, 'West Hollywood': 8, 'Pasadena': 7, 'Venice Beach': 6, 'Silver Lake': 5, 'Downtown LA': 4, 'Koreatown': 3, 'Compton': 1}[b['barrio']],
            'silencio_tech': {'Bel Air': 9, 'Pasadena': 8, 'Beverly Hills': 7, 'Silver Lake': 6, 'Santa Monica': 5, 'West Hollywood': 4, 'Venice Beach': 4, 'Koreatown': 3, 'Compton': 3, 'Downtown LA': 2}[b['barrio']],
            'coste_vida': {'Compton': 9, 'Koreatown': 6, 'Downtown LA': 5, 'Pasadena': 5, 'Silver Lake': 4, 'West Hollywood': 3, 'Santa Monica': 2, 'Venice Beach': 2, 'Beverly Hills': 1, 'Bel Air': 1}[b['barrio']]
        })
        results.append(b)
        my_bar.progress((i + 1) / len(barrios), text=f"Analizando {b['barrio']}...")
    
    my_bar.empty()
    df = pd.DataFrame(results)
    
    # --- ALGORITMO HÍBRIDO (Lo que querías mantener) ---
    def calculate_smart_score(row, column, target_ratio_per_10k, min_critical_mass):
        if row[column] < min_critical_mass:
            penalty_factor = row[column] / min_critical_mass if min_critical_mass > 0 else 0
            return penalty_factor * 4.0 
        
        ratio = (row[column] / row['poblacion']) * 10000
        score = (ratio / target_ratio_per_10k) * 10
        return min(10.0, score)

    # Aplicamos el algoritmo
    df['vida_nocturna'] = df.apply(lambda row: calculate_smart_score(row, 'fiesta', 15, 10), axis=1)
    df['naturaleza_score'] = df.apply(lambda row: calculate_smart_score(row, 'naturaleza', 3, 4), axis=1)
    df['movilidad_score'] = df.apply(lambda row: calculate_smart_score(row, 'movilidad', 20, 15), axis=1)
    
    # Calculamos ratio para mostrar info
    df['ratio_fiesta'] = (df['fiesta'] / df['poblacion']) * 10000
    
    return df

try:
    df = load_data_with_api()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 4. SIDEBAR (PERFILES) ---
st.sidebar.header("🏹 Configura tu Perfil")
perfil = st.sidebar.selectbox("Arquetipo", ["Personalizado", "Cersei (Lujo)", "Jon Snow (Naturaleza)", "Tyrion (Fiesta)", "Bran (Tech)", "Arya (Movilidad)"])

defaults = {'seguridad': 5, 'lujo': 5, 'naturaleza': 5, 'fiesta': 5, 'movilidad': 5, 'tech': 5, 'precio': 5}
if perfil == "Cersei (Lujo)": defaults = {'seguridad': 10, 'lujo': 10, 'naturaleza': 2, 'fiesta': 4, 'movilidad': 0, 'tech': 5, 'precio': 0}
elif perfil == "Jon Snow (Naturaleza)": defaults = {'seguridad': 6, 'lujo': 1, 'naturaleza': 10, 'fiesta': 3, 'movilidad': 4, 'tech': 2, 'precio': 8}
elif perfil == "Tyrion (Fiesta)": defaults = {'seguridad': 4, 'lujo': 6, 'naturaleza': 2, 'fiesta': 10, 'movilidad': 8, 'tech': 5, 'precio': 5}
elif perfil == "Bran (Tech)": defaults = {'seguridad': 8, 'lujo': 7, 'naturaleza': 5, 'fiesta': 0, 'movilidad': 2, 'tech': 10, 'precio': 2}
elif perfil == "Arya (Movilidad)": defaults = {'seguridad': 5, 'lujo': 3, 'naturaleza': 4, 'fiesta': 7, 'movilidad': 10, 'tech': 6, 'precio': 6}

st.sidebar.subheader("⚖️ Prioridades (0-10)")
w_seguridad = st.sidebar.slider("Seguridad", 0, 10, defaults['seguridad'])
w_lujo = st.sidebar.slider("Lujo", 0, 10, defaults['lujo'])
w_naturaleza = st.sidebar.slider("Naturaleza", 0, 10, defaults['naturaleza'])
w_fiesta = st.sidebar.slider("Vida Nocturna", 0, 10, defaults['fiesta'])
w_movilidad = st.sidebar.slider("Movilidad", 0, 10, defaults['movilidad'])
w_tech = st.sidebar.slider("Tech/Silencio", 0, 10, defaults['tech'])
w_precio = st.sidebar.slider("Precio", 0, 10, defaults['precio'])

# --- 5. CÁLCULO PUNTUACIÓN FINAL ---
def calcular_puntuacion(row):
    score = (
        (row['seguridad'] * w_seguridad) +
        (row['lujo_privacidad'] * w_lujo) +
        (row['naturaleza_score'] * w_naturaleza) + 
        (row['vida_nocturna'] * w_fiesta) +        
        (row['movilidad_score'] * w_movilidad) +   
        (row['silencio_tech'] * w_tech) +
        (row['coste_vida'] * w_precio)
    )
    total = w_seguridad + w_lujo + w_naturaleza + w_fiesta + w_movilidad + w_tech + w_precio
    return score / total if total > 0 else 0

if not df.empty:
    df['match_score'] = df.apply(calcular_puntuacion, axis=1)
    df['match_percentage'] = (df['match_score'] / 10) * 100
    df['tooltip_match'] = df['match_percentage'].apply(lambda x: f"{x:.1f}")
    df['tooltip_fiesta'] = df['ratio_fiesta'].apply(lambda x: f"{x:.1f}")
    df_sorted = df.sort_values(by='match_percentage', ascending=False)
else:
    st.stop()

# --- 6. LAYOUT PRINCIPAL (VISUALIZACIÓN CLÁSICA) ---
st.title("🏰 El Joc de Barris: LA Edition")
st.caption(f"Algoritmo v2.1: Masa Crítica + Densidad Poblacional. Perfil seleccionado: {perfil}")

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("🗺️ Mapa de Afinidad")
    
    def get_color(score):
        return [int(255 * (1 - (score/10))), int(255 * (score/10)), 0, 160]

    df['color'] = df['match_score'].apply(get_color)

    view_state = pdk.ViewState(latitude=34.0522, longitude=-118.2437, zoom=9.5, pitch=45)
    
    tooltip = {
        "html": "<b>{barrio}</b><br>Match: <b>{tooltip_match}%</b><br>👥 Pob: {poblacion}<br>🍸 Ratio Bares: {tooltip_fiesta}/10k",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    layer = pdk.Layer(
        "ColumnLayer", 
        data=df, 
        get_position='[lon, lat]', 
        get_elevation='match_score', 
        elevation_scale=1000, 
        radius=800, 
        get_fill_color='color', 
        pickable=True, 
        auto_highlight=True
    )
    
    st.pydeck_chart(pdk.Deck(map_provider='carto', map_style='light', initial_view_state=view_state, layers=[layer], tooltip=tooltip))

with col2:
    st.subheader("🏆 Top 3 Recomendaciones")
    
    top_3 = df_sorted.head(3)
    
    # --- AQUÍ ES DONDE HE RESTAURADO LA VISUALIZACIÓN ORIGINAL ---
    for index, row in top_3.iterrows():
        st.markdown(f"### {row['barrio']}")
        st.progress(int(row['match_percentage']))
        st.caption(f"Afinidad: {row['match_percentage']:.1f}%")
        
        # Motor de Justificación (Texto simple, sin HTML raro)
        justificacion = []
        
        # Usamos las métricas del nuevo algoritmo para decidir qué decir
        if row['naturaleza_score'] > 6 and w_naturaleza > 4: justificacion.append("🌳 Muchos parques")
        if row['vida_nocturna'] > 6 and w_fiesta > 4: justificacion.append("🎉 Zona muy activa")
        if row['movilidad_score'] > 6 and w_movilidad > 4: justificacion.append("🚌 Bien comunicado")
        
        if row['seguridad'] > 7 and w_seguridad > 4: justificacion.append("🛡️ Alta seguridad")
        if row['coste_vida'] > 7 and w_precio > 4: justificacion.append("💰 Económico")
        
        if justificacion:
            st.info("Destaca por: " + ", ".join(justificacion))
        else:
            st.write("Una opción equilibrada para tus criterios.")
            
        st.divider()

with st.expander("🛠️ Ver Datos (Algoritmo Híbrido)"):
    st.dataframe(df_sorted[['barrio', 'match_percentage', 'vida_nocturna', 'ratio_fiesta', 'poblacion']])