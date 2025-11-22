import streamlit as st
import code_dades # Importem el fitxer que acabem de crear

# @st.cache_data fa que només es carreguin les dades UNA vegada
# Si no ho poses, l'app anirà lenta cada cop que facis click
@st.cache_data
def obtenir_dades_memoria():
    return code_dades.carregar_totes_les_dades()

# Cridem la funció
totes_les_dades = obtenir_dades_memoria()

# Ara recuperem cada DataFrame pel seu nom (les claus del diccionari)
act_df = totes_les_dades['activities']
dem_ec_df = totes_les_dades['demographic_economic']
dem_data_df = totes_les_dades['demographic_data']
dataset_df = totes_les_dades['offenses']
residential_df = totes_les_dades['residential']

# Ja pots fer servir les variables normalment!
if act_df is not None:
    st.write("Activitats carregades!", act_df.head())