import json
import os
import requests
from datetime import datetime

# --- 1. CREDENZIALI ECOWITT ---
application_key = "DF17C440A062FE7D1DC11419C07C5289"
api_key = "573239e6-94f0-4e5c-a2bf-140661231809"
mac_address = "24:4C:AB:74:89:71"

url_ecowitt = "https://api.ecowitt.net/api/v3/device/real_time"

# Parametri aggiornati: chiediamo all'API di fornirci nativamente 
# Celsius (1), hPa (3) e km/h (7) per evitare errori di conversione manuale
params_ecowitt = {
    "application_key": application_key,
    "api_key": api_key,
    "mac": mac_address,
    "call_back": "all",
    "temp_unitid": 1,
    "pressure_unitid": 3,
    "wind_speed_unitid": 7
}

def raccogli_dati_meteo():
    try:
        response = requests.get(url_ecowitt, params=params_ecowitt, timeout=10)
        if response.status_code == 200:
            risultato = response.json()
            if risultato.get("code") == 0:
                data = risultato.get("data", {})

                # Estrazione sicura dei dati
                temp_val = data.get("outdoor", {}).get("temperature", {}).get("value", 0)
                humidity_val = data.get("outdoor", {}).get("humidity", {}).get("value", 0)
                pressure_val = data.get("pressure", {}).get("relative", {}).get("value", 0)
                wind_val = data.get("wind", {}).get("wind_speed", {}).get("value", 0)

                # Parsing robusto con fallback a 0.0 in caso di dati nulli dal sensore
                temp_celsius = float(temp_val) if temp_val is not None else 0.0
                humidity = int(humidity_val) if humidity_val is not None else 0
                pressure_hpa = float(pressure_val) if pressure_val is not None else 0.0
                wind_speed = float(wind_val) if wind_val is not None else 0.0
                
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Analisi ecologica di valle
                if pressure_hpa > 1020 and wind_speed < 1.5:
                    indice_aria = "CRITICO (Ristagno potenziale nei bassi strati)"
                elif pressure_hpa < 1010 or wind_speed > 3.0:
                    indice_aria = "OTTIMA (Buon rimescolamento e ventilazione)"
                else:
                    indice_aria = "BUONA / NORMALE"

                # Struttura dati pronta per un sito web (JSON)
                rilevazione = {
                    "timestamp": timestamp_str,
                    "temperatura_c": round(temp_celsius, 1),
                    "umidita_pct": humidity,
                    "pressione_hpa": round(pressure_hpa, 1),
                    "vento_kmh": round(wind_speed, 1),
                    "qualita_aria_stimata": indice_aria,
                }

                return rilevazione
            else:
                print(f"Errore dall'API Ecowitt: {risultato.get('msg')}")
    except Exception as e:
        print(f"Errore di connessione: {e}")
    return None

# Esecuzione del raccoglitore
dati_correnti = raccogli_dati_meteo()

if dati_correnti:
    print("Dati rilevati con successo:")
    print(json.dumps(dati_correnti, indent=4, ensure_ascii=False))

    # Salvataggio in un file JSON
    with open("ultimo_stato.json", "w", encoding="utf-8") as f:
        json.dump(dati_correnti, f, indent=4, ensure_ascii=False)

    # Salvataggio storico in append
    with open("storico_albanello.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(dati_correnti, ensure_ascii=False) + "\n")

    print("[OK] File aggiornati per la pubblicazione web.")
else:
    print("Impossibile recuperare i dati dalla centralina.")
