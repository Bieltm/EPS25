import streamlit as st
import pandas as pd
import pydeck as pdk

# Configuración de la página
st.set_page_config(page_title="El Joc de Barris - LA Finder", layout="wide")

# --- 1. DATOS SIMULADOS DE LOS ANGELES (Basado en el PDF) ---
# En un caso real, aquí conectarías con las APIs (OpenStreetMap, Census, LAPD)
@st.cache_data
def load_data():
    data = {
        'barrio': [
            'Beverly Hills', 'Downtown LA', 'Silver Lake', 'Santa Monica', 
            'Compton', 'Pasadena', 'West Hollywood', 'Venice Beach', 
            'Koreatown', 'Bel Air'
        ],
        # Coordenadas aproximadas
        'lat': [34.0736, 34.0407, 34.0869, 34.0195, 33.8958, 34.1478, 34.0900, 33.9850, 34.0618, 34.1002],
        'lon': [-118.4004, -118.2468, -118.2702, -118.4912, -118.2201, -118.1445, -118.3617, -118.4695, -118.3004, -118.4595],
        
        # Métricas normalizadas (0-10) según las áreas del PDF
        'seguridad':      [10, 3, 6, 7, 2, 8, 7, 5, 4, 10], # Criminalidad inversa
        'lujo_privacidad':[10, 4, 5, 8, 1, 7, 8, 6, 3, 10], # Cersei metrics
        'naturaleza':     [8, 1, 5, 9, 2, 7, 3, 9, 1, 9],   # Jon Snow metrics
        'vida_nocturna':  [4, 10, 9, 8, 3, 6, 10, 9, 9, 1], # Tyrion metrics
        'movilidad':      [3, 10, 6, 7, 5, 5, 8, 5, 9, 2],  # Arya metrics (Transporte público/Walkability)
        'silencio_tech':  [7, 2, 6, 5, 3, 8, 4, 4, 3, 9],   # Bran metrics (Fibra + Silencio)
        'coste_vida':     [1, 5, 4, 2, 9, 5, 3, 2, 6, 1]    # 1 = Muy caro, 10 = Muy barato
    }
    return pd.DataFrame(data)

df = load_data()

# --- 2. INTERFAZ DE USUARIO (SIDEBAR) ---
st.sidebar.header("🏹 Configura tu Perfil")
st.sidebar.markdown("Define qué es importante para ti para encontrar tu *Trono* en LA.")

# Preajustes basados en los personajes del PDF
perfil = st.sidebar.selectbox(
    "¿Te identificas con algún arquetipo?",
    ["Personalizado", "Cersei (Lujo y Seguridad)", "Jon Snow (Naturaleza y Comunidad)", "Tyrion (Fiesta y Cultura)", "Bran (Silencio y Tech)", "Arya (Movilidad y Anonimato)"]
)

# Valores por defecto de los sliders según el perfil
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

# Sliders de preferencias (Pesos)
st.sidebar.subheader("⚖️ Tus Prioridades (0-10)")
w_seguridad = st.sidebar.slider("Seguridad (Baja criminalidad)", 0, 10, defaults['seguridad'])
w_lujo = st.sidebar.slider("Lujo y Privacidad", 0, 10, defaults['lujo'])
w_naturaleza = st.sidebar.slider("Naturaleza y Aire Libre", 0, 10, defaults['naturaleza'])
w_fiesta = st.sidebar.slider("Vida Nocturna y Cultura", 0, 10, defaults['fiesta'])
w_movilidad = st.sidebar.slider("Movilidad (Transporte/Andar)", 0, 10, defaults['movilidad'])
w_tech = st.sidebar.slider("Silencio y Tech (Home Office)", 0, 10, defaults['tech'])
w_precio = st.sidebar.slider("Precio Asequible", 0, 10, defaults['precio'])

# --- 3. ALGORITMO DE RECOMENDACIÓN (Weighted Scoring) ---
def calcular_puntuacion(row):
    # Suma de productos (Valor * Peso)
    score = (
        (row['seguridad'] * w_seguridad) +
        (row['lujo_privacidad'] * w_lujo) +
        (row['naturaleza'] * w_naturaleza) +
        (row['vida_nocturna'] * w_fiesta) +
        (row['movilidad'] * w_movilidad) +
        (row['silencio_tech'] * w_tech) +
        (row['coste_vida'] * w_precio)
    )
    
    # Evitar división por cero
    total_weights = w_seguridad + w_lujo + w_naturaleza + w_fiesta + w_movilidad + w_tech + w_precio
    if total_weights == 0:
        return 0
    
    return score / total_weights

# Aplicar cálculo
df['match_score'] = df.apply(calcular_puntuacion, axis=1)
# Escalar a 0-100 para mejor visualización
df['match_percentage'] = (df['match_score'] / 10) * 100
df_sorted = df.sort_values(by='match_percentage', ascending=False)

# --- 4. LAYOUT PRINCIPAL ---
st.title("🏰 El Joc de Barris: Los Angeles Edition")
st.write("Descubre tu vecindario ideal basado en tus necesidades reales (o las de tu personaje).")

col1, col2 = st.columns([3, 1])

with col1:
    # --- MAPA VISUAL (PYDECK) ---
    st.subheader("Mapa de Afinidad")
    
    # Color dinámico basado en el score (Rojo a Verde)
    # Verde para alto match, Rojo para bajo match
    # Formato RGBA. Usaremos una función simple para esto en el front no se puede,
    # así que precalculamos el color en el dataframe.
    
    def get_color(score):
        # Score 0-10. 
        # Bajo (0-5): Rojo dominante. Alto (5-10): Verde dominante.
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

    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position='[lon, lat]',
        get_elevation='match_score',
        elevation_scale=500,
        radius=800,
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
    )

    tooltip = {
        "html": "<b>{barrio}</b><br>Match: <b>{match_percentage:.1f}%</b><br>Seguridad: {seguridad}<br>Fiesta: {vida_nocturna}",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=view_state,
        layers=[layer],
        tooltip=tooltip
    ))

with col2:
    # --- TOP RECOMENDACIONES ---
    st.subheader("🏆 Top 3 Barrios")
    
    top_3 = df_sorted.head(3)
    
    for index, row in top_3.iterrows():
        st.markdown(f"### {row['barrio']}")
        st.progress(int(row['match_percentage']))
        st.caption(f"Afinidad: {row['match_percentage']:.1f}%")
        
        # Motor de Justificación (básico)
        justificacion = []
        if row['seguridad'] > 7 and w_seguridad > 5: justificacion.append("🛡️ Alta seguridad")
        if row['vida_nocturna'] > 7 and w_fiesta > 5: justificacion.append("🎉 Gran vida nocturna")
        if row['coste_vida'] > 7 and w_precio > 5: justificacion.append("💰 Económico")
        if row['lujo_privacidad'] > 7 and w_lujo > 5: justificacion.append("💎 Exclusivo")
        
        if justificacion:
            st.info("Por qué encaja contigo: " + ", ".join(justificacion))
        st.divider()

# --- 5. TABLA DETALLADA ---
with st.expander("Ver datos detallados de todos los barrios"):
    st.dataframe(df_sorted[['barrio', 'match_percentage', 'seguridad', 'lujo_privacidad', 'vida_nocturna', 'coste_vida', 'movilidad']])