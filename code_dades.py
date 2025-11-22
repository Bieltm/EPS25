import pandas as pd
import os

def carregar_totes_les_dades():
    """
    Llegeix tots els CSVs de la carpeta i retorna un diccionari amb els DataFrames.
    Gestiona errors individualment per a cada arxiu.
    """
    carpeta_del_codi = os.path.dirname(os.path.abspath(__file__))
    
    # Diccionari de rutes (Clau: Nom identificatiu, Valor: Nom de l'arxiu)
    # He mantingut els teus noms d'arxius originals (compte amb els typos si els corregeixes manualment)
    arxius = {
        "activities": "Activities.csv",
        "demographic_economic": "Demographic_and_Economic_Graphs.csv",
        "demographic_data": "Dempgraphic_data.csv",  # Compte: aquí posa 'Dempgraphic'
        "offenses": "Offenses_dataset.csv",
        "residential": "Residential_Builidings.csv" # Compte: aquí posa 'Builidings'
    }

    # Diccionari on guardarem les dades carregades
    dades_carregades = {}

    print("--- INICIANT CÀRREGA DE DADES ---")

    for clau, nom_arxiu in arxius.items():
        ruta_completa = os.path.join(carpeta_del_codi, nom_arxiu)
        
        if os.path.exists(ruta_completa):
            try:
                # low_memory=False és clau per evitar errors de tipus mixtes en arxius grans
                df = pd.read_csv(ruta_completa, sep=',', index_col=None, na_values=['NA'], low_memory=False)
                dades_carregades[clau] = df
                print(f"✅ {clau}: Carregat correctament ({len(df)} files)")
            except Exception as e:
                print(f"❌ {clau}: Error llegint l'arxiu ({e})")
                dades_carregades[clau] = None
        else:
            print(f"⚠️ {clau}: No trobat a {nom_arxiu}")
            dades_carregades[clau] = None

    return dades_carregades

# --- BLOC DE PROVA ---
# Això permet provar aquest fitxer sol sense obrir la web
if __name__ == "__main__":
    dades = carregar_totes_les_dades()
    # Exemple d'accés
    if dades['offenses'] is not None:
        print("\nExemple de dades de crims:")
        print(dades['offenses'].head(3))