import pandas as pd
import os

carpeta_del_codi = os.path.dirname(os.path.abspath(__file__))
ruta = os.path.join(carpeta_del_codi, 'Activities.csv')

if os.path.exists(ruta):
    print(f"1. He trobat l'arxiu a: {ruta}")
    try:
        act_df = pd.read_csv(ruta, index_col=None, na_values=['NA'])
        
        print(act_df.head())
        
    except Exception as e:
        print(f"Error llegint l'arxiu: {e}")
else:
    print("NO trobo l'arxiu 'Activities.csv'.")
    print(f"Assegura't que l'arxiu estigui dins de: {carpeta_del_codi}")

