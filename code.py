import streamlit as st
import pandas as pd
import pydeck as pdk

st.title("Barris de Los Angeles")

# --- 1. DEFINICIÓN DE DATOS (Lo movemos al principio para poder filtrar) ---
data = {
    'lat': [34.0736, 34.0195, 34.0407, 34.0869, 
            33.8958, 34.1478, 34.1002, 33.9850, 
            34.0900, 34.0259, 34.0782, 34.0618],

    'lon': [-118.4004, -118.4912, -118.2468, -118.2702, 
            -118.2201, -118.1445, -118.4595, -118.4695, 
            -118.3617, -118.7798, -118.2606, -118.3004],

    'barrio': ['Beverly Hills', 'Santa Monica', 'Downtown LA', 'Silver Lake', 
                'Compton', 'Pasadena', 'Bel Air', 'Venice Beach', 
                'West Hollywood', 'Malibu', 'Echo Park', 'Koreatown'],

    'puntuacion': [10, 2, 5, 8, 3, 7, 9, 6, 8, 10, 4, 7]
}
df = pd.DataFrame(data)

# --- 2. BARRA LATERAL (PREFERENCIAS) ---
st.sidebar.title("Preferencies")

# Filtro 1: Slider para puntuación mínima
min_puntuacion = st.sidebar.slider(
    "Puntuación mínima:", 
    min_value=0, 
    max_value=10, 
    value=0 # Valor inicial
)

# Filtro 2: Multiselect para elegir barrios específicos
barrios_seleccionados = st.sidebar.multiselect(
    "Filtrar por barrio:",
    options=df['barrio'].unique(),
    default=df['barrio'].unique() # Por defecto todos seleccionados
)
# Filtro 3: Slider para puntuación de lujo
min_puntuacion_lujo = st.sidebar.slider(
    "Nivel de lujo:", 
    min_value=0, 
    max_value=5, 
    value=0 # Valor inicial
)

# --- 3. APLICAR FILTROS ---
# Filtramos el DataFrame basándonos en los inputs de arriba
df_filtrado = df[
    (df['puntuacion'] >= min_puntuacion) & 
    (df['barrio'].isin(barrios_seleccionados))
]

# --- 4. LAYOUT PRINCIPAL ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader(f"Mapa ({len(df_filtrado)} visibles)")

    # Definimos la vista inicial
    view_state = pdk.ViewState(
        latitude=34.0522,
        longitude=-118.2437,
        zoom=9,
        pitch=50,
    )

    # Definimos la capa usando df_filtrado
    layer = pdk.Layer(
        "ColumnLayer",
        data=df_filtrado, # IMPORTANTE: Usamos los datos filtrados
        get_position='[lon, lat]',
        get_elevation='puntuacion',
        elevation_scale=1000,
        radius=1000,
        get_fill_color=[255, 0, 0, 140],
        pickable=True,
        auto_highlight=True,
    )

    # Renderizamos el mapa
    st.pydeck_chart(pdk.Deck(
        map_provider='carto',
        map_style='light',
        initial_view_state=view_state,
        layers=[layer],
        tooltip={"text": "{barrio}\nPuntuación: {puntuacion}"}
    ))

with col2:
    st.write("Datos del filtro actual:")
    # Mostramos la tabla dinámica que cambia según los filtros
    st.dataframe(df_filtrado[['barrio', 'puntuacion']])

with col3:
    st.metric("Puntuación Media", round(df_filtrado['puntuacion'].mean(), 2))