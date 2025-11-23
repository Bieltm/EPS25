import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
import time

# Configuración de la página
st.set_page_config(page_title="El Joc de Barris - LA Finder", layout="wide")

# --- 1. INTEGRACIÓN API OPENSTREETMAP (Overpass) ---
# Esta función consulta datos reales.
@st.cache_data(show_spinner=False)
def get_real_osm_data(lat, lon, radius=1500):
    """
    Consulta la API de Overpass para contar elementos en un radio variable.
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

@st.cache_data
def load_data_with_api():
    # Coordenadas base y RADIOS personalizados (según extensión del barrio)
    barrios = [
        # Beverly Hills: Zona amplia de mansiones + Rodeo Drive -> Radio grande (2km)
        {'barrio': 'Beverly Hills', 'lat': 34.0736, 'lon': -118.4004, 'radius': 2000},
        
        # Downtown: Muy denso y vertical -> Radio estándar (1.5km)
        {'barrio': 'Downtown LA', 'lat': 34.0407, 'lon': -118.2468, 'radius': 1500},
        
        # Silver Lake: Alargado a lo largo de Sunset Blvd -> Radio estándar (1.5km)
        {'barrio': 'Silver Lake', 'lat': 34.0869, 'lon': -118.2702, 'radius': 1500},
        
        # Santa Monica: Extenso hacia la playa -> Radio grande (2km)
        {'barrio': 'Santa Monica', 'lat': 34.0195, 'lon': -118.4912, 'radius': 2000},
        
        # Compton: Muy disperso, zona plana y amplia -> Radio MUY grande (3km) para capturar servicios
        {'barrio': 'Compton', 'lat': 33.8958, 'lon': -118.2201, 'radius': 3000},
        
        # Pasadena: Ciudad en sí misma, bastante extendida -> Radio grande (2.5km)
        {'barrio': 'Pasadena', 'lat': 34.1478, 'lon': -118.1445, 'radius': 2500},
        
        # West Hollywood: Denso y caminable -> Radio compacto (1.5km)
        {'barrio': 'West Hollywood', 'lat': 34.0900, 'lon': -118.3617, 'radius': 1500},
        
        # Venice: Denso cerca de la playa -> Radio compacto (1.5km)
        {'barrio': 'Venice Beach', 'lat': 33.9850, 'lon': -118.4695, 'radius': 1500},
        
        # Koreatown: Extremadamente denso -> Radio pequeño (1.2km) para no coger barrios vecinos
        {'barrio': 'Koreatown', 'lat': 34.0618, 'lon': -118.3004, 'radius': 1200},
        
        # Bel Air: Muy disperso, colinas, casas aisladas -> Radio MÁXIMO (3.5km) para encontrar algo
        {'barrio': 'Bel Air', 'lat': 34.1002, 'lon': -118.4595, 'radius': 3500}
    ]
    
    results = []
    
    progress_text = "📡 Escaneando barrios con radio adaptativo..."
    my_bar = st.progress(0, text=progress_text)
    
    total_barrios = len(barrios)
    
    for i, b in enumerate(barrios):
        # Llamada a la API pasando el RADIO ESPECÍFICO (b['radius'])
        real_data = get_real_osm_data(b['lat'], b['lon'], radius=b['radius'])
        
        b.update({
            'fiesta': real_data['bares_count'],
            'naturaleza': real_data['parques_count'],
            'movilidad': real_data['transporte_count'],
            
            # Datos SIMULADOS
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
        my_bar.progress((i + 1) / total_barrios, text=f"Analizando {b['barrio']} (Radio: {b['radius']}m)...")
    
    my_bar.empty()
    df = pd.DataFrame(results)
    
    # --- NORMALIZACIÓN ---
    def normalize(column):
        min_val = df[column].min()
        max_val = df[column].max()
        if max_val == min_val: return 5
        return (df[column] - min_val) / (max_val - min_val) * 10

    df['vida_nocturna'] = normalize('fiesta')
    df['naturaleza_score'] = normalize('naturaleza')
    df['movilidad_score'] = normalize('movilidad')
    
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

defaults = {'seguridad': 5, 'lujo': 5, 'naturaleza': 5, 'fiesta': 5, 'movilidad': 5, 'tech': 5, 'precio': 5}

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
w_fiesta = st.sidebar.slider("Vida Nocturna", 0, 10, defaults['fiesta'])
w_movilidad = st.sidebar.slider("Movilidad", 0, 10, defaults['movilidad'])
w_tech = st.sidebar.slider("Silencio y Tech", 0, 10, defaults['tech'])
w_precio = st.sidebar.slider("Precio Asequible", 0, 10, defaults['precio'])

# --- 3. ALGORITMO ---
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
    if total_weights == 0: return 0
    return score / total_weights

if not df.empty:
    df['match_score'] = df.apply(calcular_puntuacion, axis=1)
    df['match_percentage'] = (df['match_score'] / 10) * 100
    df['tooltip_match'] = df['match_percentage'].apply(lambda x: f"{x:.1f}")
    df_sorted = df.sort_values(by='match_percentage', ascending=False)
else:
    st.error("No se pudieron cargar los datos.")
    st.stop()

# --- 4. LAYOUT ---
st.title("🏰 El Joc de Barris: Los Angeles Edition")
st.write("Descubre tu vecindario ideal con escaneo adaptativo (Radios variables según densidad).")

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Mapa de Afinidad")
    
    def get_color(score):
        r = int(255 * (1 - (score/10)))
        g = int(255 * (score/10))
        return [r, g, 0, 160]

    df['color'] = df['match_score'].apply(get_color)

    view_state = pdk.ViewState(latitude=34.0522, longitude=-118.2437, zoom=9.5, pitch=45)

    tooltip = {
        "html": "<b>{barrio}</b><br>Match: <b>{tooltip_match}%</b><br>📏 Radio analizado: {radius}m<br>🌳 Parques: {naturaleza}<br>🍸 Locales: {fiesta}<br>🚌 Paradas: {movilidad}",
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

    st.pydeck_chart(pdk.Deck(map_provider='carto', map_style='light', initial_view_state=view_state, layers=[layer], tooltip=tooltip))

with col2:
    st.subheader("🏆 Top 3 Barrios")
    top_3 = df_sorted.head(3)
    
    for index, row in top_3.iterrows():
        st.markdown(f"### {row['barrio']}")
        st.progress(int(row['match_percentage'] / 100 * 100))
        st.caption(f"Afinidad: {row['match_percentage']:.1f}%")
        
        justificacion = []
        if row['naturaleza'] > df['naturaleza'].mean() and w_naturaleza > 5: justificacion.append("🌳 Naturaleza")
        if row['fiesta'] > df['fiesta'].mean() and w_fiesta > 5: justificacion.append("🎉 Fiesta")
        if row['movilidad'] > df['movilidad'].mean() and w_movilidad > 5: justificacion.append("🚌 Movilidad")
        if row['seguridad'] > 7 and w_seguridad > 5: justificacion.append("🛡️ Seguridad")
        if row['coste_vida'] > 7 and w_precio > 5: justificacion.append("💰 Precio")
        
        if justificacion: st.info(", ".join(justificacion))
        else: st.write("Opción equilibrada.")
        st.divider()

with st.expander("🕵️ Ver Datos Reales"):
    st.info("Datos extraídos de OSM con radios variables (ver columna 'radius').")
    st.dataframe(df_sorted[['barrio', 'radius', 'match_percentage', 'naturaleza', 'fiesta', 'movilidad']])