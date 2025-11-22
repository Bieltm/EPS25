import pandas as pd
import os

print("--- INICI DEL PROGRAMA ---")

# --- PART 1: Càlcul de la ruta automàtica (Portable) ---
# Això substitueix la ruta fixa "C:\Users\BIEL..."
# Li diu a Python: "Busca la carpeta on està aquest fitxer .py"
carpeta_del_codi = os.path.dirname(os.path.abspath(__file__))
ruta = os.path.join(carpeta_del_codi, 'Activities.csv')

# --- PART 2: El teu codi de lectura i comprovació ---
if os.path.exists(ruta):
    print(f"1. He trobat l'arxiu a: {ruta}")
    
    try:
        
        df = pd.read_csv(ruta, index_col=None, na_values=['NA'])
        
        print(df.head())
        
    except Exception as e:
        print(f"Error llegint l'arxiu: {e}")
else:
    print("NO trobo l'arxiu 'Activities.csv'.")
    print(f"Assegura't que l'arxiu estigui dins de: {carpeta_del_codi}")

print("--- FINAL DEL PROGRAMA ---")