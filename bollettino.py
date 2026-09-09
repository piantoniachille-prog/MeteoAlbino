from datetime import datetime, timedelta
import json
import os
import requests

application_key = "DF17C440A062FE7D1DC11419C07C5289"
api_key = "573239e6-94f0-4e5c-a2bf-140661231809"
mac_address = "24:4C:AB:74:89:71"

url_ecowitt = "https://api.ecowitt.net/api/v3/device/real_time"
params_ecowitt = {
    "application_key": application_key,
    "api_key": api_key,
    "mac": mac_address,
    "call_back": "all",
}

def raccogli_dati_meteo():
    try:
        response = requests.get(url_ecowitt, params=params_ecowitt, timeout=10)
        if response.status_code == 200:
            risultato = response.json()
            if risultato.get("code") == 0:
                data = risultato.get("data", {})
                
                # Estrazioni base
                temp_raw = float(data.get("outdoor", {}).get("temperature", {}).get("value", 0))
                humidity = data.get("outdoor", {}).get("humidity", {}).get("value", 0)
                pressure_raw = float(data.get("pressure", {}).get("relative", {}).get("value", 0))
                wind_val = data.get("wind", {}).get("wind_speed", {}).get("value")
                wind_speed = float(wind_val) if wind_val is not None else 0.0

                # Estrazione precipitazioni (gestione sicura del blocco rain)
                rain_data = data.get("rainfall", {})
                # Di solito Ecowitt fornisce il dato giornaliero o l'intensità (hourly/daily)
                rain_val = rain_data.get("daily", {}).get("value", "0")
                rain_mm = float(rain_val) if rain_val is not None else 0.0

                temp_celsius = (temp_raw - 32) * 5 / 9
                pressure_hpa = pressure_raw * 33.8639
                
                ora_italiana = datetime.utcnow() + timedelta(hours=2)
                timestamp_str = ora_italiana.strftime("%Y-%m-%d %H:%M:%S")

                # Analisi ecologica di valle
                if pressure_hpa > 1020 and wind_speed < 1.5:
                    indice_aria = "CRITICO (Ristagno potenziale nei bassi strati)"
                elif pressure_hpa < 1010 or wind_speed > 3.0:
                    indice_aria = "OTTIMA (Buon rimescolamento e ventilazione)"
                else:
                    indice_aria = "BUONA / NORMALE"

                rilevazione = {
                    "timestamp": timestamp_str,
                    "temperatura_c": round(temp_celsius, 1),
                    "umidita_pct": humidity,
                    "pressione_hpa": round(pressure_hpa, 1),
                    "vento_kmh": round(wind_speed, 1),
                    "pioggia_mm": round(rain_mm, 1),
                    "qualita_aria_stimata": indice_aria,
                }
                return rilevazione
    except Exception as e:
        print(f"Errore di connessione: {e}")
    return None

dati_correnti = raccogli_dati_meteo()

if dati_correnti:
    print("Dati rilevati con successo:")
    print(json.dumps(dati_correnti, indent=4, ensure_ascii=False))

    with open("ultimo_stato.json", "w", encoding="utf-8") as f:
        json.dump(dati_correnti, f, indent=4, ensure_ascii=False)

    with open("storico_albanello.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(dati_correnti, ensure_ascii=False) + "\n")

    print("[OK] File aggiornati per la pubblicazione web.")
else:
    print("Impossibile recuperare i dati dalla centralina.")
