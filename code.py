import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
import time

# Configuración de la página
st.set_page_config(page_title="El Joc de Barris - LA Finder", layout="wide")

# --- 1. INTEGRACIÓN API OPENSTREETMAP (Overpass) ---
@st.cache_data(show_spinner=False)
def get_real_osm_data(lat, lon, radius=1500):
    """
    Consulta la API de Overpass para contar elementos en un radio de 'radius' metros.
    Devuelve un diccionario con los conteos reales.
    """
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Consulta en lenguaje Overpass QL
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
                    total = int(tags.get('total', 0))
                    return total
                return 0

            bares = extract_count(0)
            parques = extract_count(1)
            transporte = extract_count(2)
            
            return {
                'bares_count': bares,
                'parques_count': parques,
                'transporte_count': transporte
            }
    except Exception as e:
        pass
    
    return {'bares_count': 0, 'parques_count': 0, 'transporte_count': 0}

@st.cache_data
def load_data_with_api():
    # Coordenadas y estimación de POBLACIÓN (en radio de 1.5km)
    # Esto es crucial para el cálculo "per cápita"
    barrios = [
        # Bel Air: Muy baja densidad
        {'barrio': 'Bel Air', 'lat': 34.1002, 'lon': -118.4595, 'poblacion': 5000},
        # Beverly Hills: Baja densidad
        {'barrio': 'Beverly Hills', 'lat': 34.0736, 'lon': -118.4004, 'poblacion': 15000},
        # Pasadena: Media densidad
        {'barrio': 'Pasadena', 'lat': 34.1478, 'lon': -118.1445, 'poblacion': 25000},
        # Santa Monica: Media-Alta
        {'barrio': 'Santa Monica', 'lat': 34.0195, 'lon': -118.4912, 'poblacion': 30000},
        # Venice: Media-Alta
        {'barrio': 'Venice Beach', 'lat': 33.9850, 'lon': -118.4695, 'poblacion': 30000},
        # Silver Lake: Media
        {'barrio': 'Silver Lake', 'lat': 34.0869, 'lon': -118.2702, 'poblacion': 25000},
        # West Hollywood: Alta densidad
        {'barrio': 'West Hollywood', 'lat': 34.0900, 'lon': -118.3617, 'poblacion': 35000},
        # Downtown: Muy alta densidad
        {'barrio': 'Downtown LA', 'lat': 34.0407, 'lon': -118.2468, 'poblacion': 60000},
        # Koreatown: Extremadamente alta densidad
        {'barrio': 'Koreatown', 'lat': 34.0618, 'lon': -118.3004, 'poblacion': 70000},
        # Compton: Media-Alta
        {'barrio': 'Compton', 'lat': 33.8958, 'lon': -118.2201, 'poblacion': 40000}
    ]
    
    results = []
    
    progress_text = "📡 Analizando densidad demográfica y servicios..."
    my_bar = st.progress(0, text=progress_text)
    
    total_barrios = len(barrios)
    
    for i, b in enumerate(barrios):
        real_data = get_real_osm_data(b['lat'], b['lon'])
        
        b.update({
            # Datos REALES de la API
            'fiesta': real_data['bares_count'],
            'naturaleza': real_data['parques_count'],
            'movilidad': real_data['transporte_count'],
            
            # Datos SIMULADOS (0-10)
            'seguridad': { 
                'Beverly Hills': 10, 'Bel Air': 10, 'Pasadena': 8, 'Santa Monica': 7,
                'West Hollywood': 7, 'Silver Lake': 6, 'Venice Beach': 5, 
                'Koreatown': 4, 'Downtown LA': 3, 'Compton': 2 
            }[b['barrio']],
            
            'lujo_privacidad': {
                'Beverly Hills': 10, 'Bel Air': 10, 'Santa Monica': 8, 'West Hollywood': 8,
                'Pasadena': 7, 'Venice Beach': 6, 'Silver Lake': 5, 'Downtown LA': 4,
                'Koreatown': 3, 'Compton': 1
            }[b['barrio']],
            
            'silencio_tech': {
                'Bel Air': 9, 'Pasadena': 8, 'Beverly Hills': 7, 'Silver Lake': 6,
                'Santa Monica': 5, 'West Hollywood': 4, 'Venice Beach': 4,
                'Koreatown': 3, 'Compton': 3, 'Downtown LA': 2
            }[b['barrio']],
             
            'coste_vida': { 
                'Compton': 9, 'Koreatown': 6, 'Downtown LA': 5, 'Pasadena': 5,
                'Silver Lake': 4, 'West Hollywood': 3, 'Santa Monica': 2, 
                'Venice Beach': 2, 'Beverly Hills': 1, 'Bel Air': 1
            }[b['barrio']]
        })
        results.append(b)
        my_bar.progress((i + 1) / total_barrios, text=f"Escaneando {b['barrio']}...")
    
    my_bar.empty()
    df = pd.DataFrame(results)
    
    # --- NORMALIZACIÓN PER CÁPITA ---
    # Calculamos: (Cantidad / Población) * 10,000
    # Esto nos da "Bares por cada 10k habitantes"
    
    def calculate_per_capita_score(row, column, target_ratio_per_10k):
        # 1. Calcular ratio real
        ratio = (row[column] / row['poblacion']) * 10000
        # 2. Normalizar sobre el objetivo (si llegas al objetivo, tienes un 10)
        score = (ratio / target_ratio_per_10k) * 10
        return min(10, score) # Cap en 10

    # OBJETIVOS DE RATIO (Para sacar un 10/10):
    # - Fiesta: 15 bares por cada 10k personas (suficiente para no estar saturado)
    # - Naturaleza: 3 parques por cada 10k personas
    # - Movilidad: 20 paradas por cada 10k personas
    
    df['vida_nocturna'] = df.apply(lambda row: calculate_per_capita_score(row, 'fiesta', 15), axis=1)
    df['naturaleza_score'] = df.apply(lambda row: calculate_per_capita_score(row, 'naturaleza', 3), axis=1)
    df['movilidad_score'] = df.apply(lambda row: calculate_per_capita_score(row, 'movilidad', 20), axis=1)

    # Guardamos los ratios reales para mostrarlos en el tooltip (informativo)
    df['ratio_fiesta'] = (df['fiesta'] / df['poblacion']) * 10000
    
    return df

# Cargar datos
try:
    df = load_data_with_api()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

# --- 2. INTERFAZ DE USUARIO (SIDEBAR) ---
st.sidebar.header("🏹 Configura tu Perfil")
st.sidebar.markdown("Define qué es importante para ti para encontrar tu *Trono* en LA.")

perfil = st.sidebar.selectbox(
    "¿Te identificas con algún arquetipo?",
    ["Personalizado", "Cersei (Lujo y Seguridad)", "Jon Snow (Naturaleza y Comunidad)", "Tyrion (Fiesta y Cultura)", "Bran (Silencio y Tech)", "Arya (Movilidad y Anonimato)"]
)

defaults = {
    'seguridad': 5, 'lujo': 5, 'naturaleza': 5, 'fiesta': 5, 'movilidad': 5, 'tech': 5, 'precio': 5
}

if perfil == "Cersei (Lujo y Seguridad)":
    defaults = {'seguridad': 10, 'lujo': 10, 'naturaleza': 2, 'fiesta': 4, 'movilidad': 0, 'tech': 5, 'precio': 0}
elif perfil == "Jon Snow (Naturaleza y Comunidad)":
    defaults = {'seguridad': 6, 'lujo': 1, 'naturaleza': 10, 'fiesta': 3, 'movilidad': 4, 'tech': 2, 'precio': 8}
elif perfil == "Tyrion (Fiesta y Cultura)":
    defaults = {'seguridad': 4, 'lujo': 6, 'naturaleza': 2, 'fiesta': 10, 'movilidad': 8, 'tech': 5, 'precio': 5}
elif perfil == "Bran (Silencio y Tech)":
    defaults = {'seguridad': 8, 'lujo': 7, 'naturaleza': 5, 'fiesta': 0, 'movilidad': 2, 'tech': 10, 'precio': 2}
elif perfil == "Arya (Movilidad y Anonimato)":
    defaults = {'seguridad': 5, 'lujo': 3, 'naturaleza': 4, 'fiesta': 7, 'movilidad': 10, 'tech': 6, 'precio': 6}

st.sidebar.subheader("⚖️ Tus Prioridades (0-10)")
w_seguridad = st.sidebar.slider("Seguridad", 0, 10, defaults['seguridad'])
w_lujo = st.sidebar.slider("Lujo y Privacidad", 0, 10, defaults['lujo'])
w_naturaleza = st.sidebar.slider("Naturaleza", 0, 10, defaults['naturaleza'])
w_fiesta = st.sidebar.slider("Vida Nocturna (per cápita)", 0, 10, defaults['fiesta'])
w_movilidad = st.sidebar.slider("Movilidad", 0, 10, defaults['movilidad'])
w_tech = st.sidebar.slider("Silencio y Tech", 0, 10, defaults['tech'])
w_precio = st.sidebar.slider("Precio Asequible", 0, 10, defaults['precio'])

# --- 3. ALGORITMO DE RECOMENDACIÓN ---
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
    
    total_weights = w_seguridad + w_lujo + w_naturaleza + w_fiesta + w_movilidad + w_tech + w_precio
    if total_weights == 0:
        return 0
    
    return score / total_weights

# Aplicar cálculo
if not df.empty:
    df['match_score'] = df.apply(calcular_puntuacion, axis=1)
    df['match_percentage'] = (df['match_score'] / 10) * 100
    df['tooltip_match'] = df['match_percentage'].apply(lambda x: f"{x:.1f}")
    df['tooltip_fiesta'] = df['ratio_fiesta'].apply(lambda x: f"{x:.1f}") # Para mostrar en tooltip
    df_sorted = df.sort_values(by='match_percentage', ascending=False)
else:
    st.error("No se pudieron cargar los datos.")
    st.stop()

# --- 4. LAYOUT PRINCIPAL ---
st.title("🏰 El Joc de Barris: Los Angeles Edition")
st.write("Descubre tu vecindario ideal. **Nuevo:** Ahora usamos métricas 'per cápita' para evitar la saturación.")

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Mapa de Afinidad (Densidad Ajustada)")
    
    def get_color(score):
        r = int(255 * (1 - (score/10)))
        g = int(255 * (score/10))
        return [r, g, 0, 160]

    df['color'] = df['match_score'].apply(get_color)

    view_state = pdk.ViewState(
        latitude=34.0522,
        longitude=-118.2437,
        zoom=9.5,
        pitch=45,
    )

    tooltip = {
        "html": "<b>{barrio}</b><br>Match: <b>{tooltip_match}%</b><br>👥 Población est: {poblacion}<br>🍸 Bares/10k hab: {tooltip_fiesta}<br>🌳 Parques (Total): {naturaleza}",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position='[lon, lat]',
        get_elevation='match_score',
        elevation_scale=1000, 
        radius=1000,
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
    )

    st.pydeck_chart(pdk.Deck(
        map_provider='carto',
        map_style='light',
        initial_view_state=view_state,
        layers=[layer],
        tooltip=tooltip
    ))

with col2:
    st.subheader("🏆 Top 3 (Ajustado por Gente)")
    
    top_3 = df_sorted.head(3)
    
    for index, row in top_3.iterrows():
        st.markdown(f"### {row['barrio']}")
        
        contributions = {
            'Seguridad 🛡️': row['seguridad'] * w_seguridad,
            'Lujo ✨': row['lujo_privacidad'] * w_lujo,
            'Naturaleza 🌳': row['naturaleza_score'] * w_naturaleza,
            'Fiesta/Habitante 🍸': row['vida_nocturna'] * w_fiesta,
            'Movilidad 🚌': row['movilidad_score'] * w_movilidad,
            'Tech 💻': row['silencio_tech'] * w_tech,
            'Precio 💰': row['coste_vida'] * w_precio
        }
        
        sorted_factors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        top_reasons = [factor[0] for factor in sorted_factors if factor[1] > 0][:2]
        
        if top_reasons:
            text_reasons = f"Destaca por **{top_reasons[0]}**"
            if len(top_reasons) > 1:
                text_reasons += f" y **{top_reasons[1]}**"
            st.markdown(f"{text_reasons}.")
        else:
            st.markdown("Equilibrado en densidad y servicios.")

        val_progress = int(row['match_percentage'])
        st.progress(max(0, min(100, val_progress)))
        st.caption(f"Afinidad total: {row['match_percentage']:.1f}%")
        
        st.divider()

with st.expander("🕵️ Ver Datos de Densidad"):
    st.info("Cálculo: (Instalaciones / Población Estimada) * 10,000. Esto premia barrios con buenos servicios pero menos masificados.")
    st.dataframe(df_sorted[['barrio', 'match_percentage', 'poblacion', 'fiesta', 'ratio_fiesta']])