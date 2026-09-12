"""Raccoglie osservazioni Ecowitt. Non contiene credenziali né stime di inquinamento."""
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

BASE = Path(__file__).resolve().parent
URL = "https://api.ecowitt.net/api/v3/device/real_time"
MAX_AGE_SECONDS = 90 * 60


def iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def field_time(field):
    raw = field.get("time")
    if raw is None:
        return None
    try:
        return datetime.fromtimestamp(float(raw), timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def value(data, group, key, kind, now):
    field = data.get(group, {}).get(key, {})
    if not isinstance(field, dict):
        return None, None
    raw = field.get("value")
    if raw is None or raw == "" or isinstance(raw, bool):
        return None, None
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None, None
    measured = field_time(field)
    if measured and not -300 <= (now - measured).total_seconds() <= MAX_AGE_SECONDS:
        return None, measured
    # Non interpretare un'unità sconosciuta come quella richiesta.
    unit = str(field.get("unit", "")).strip().lower().replace(" ", "")
    converters = {
        "temperature": {"℃": lambda x: x, "°c": lambda x: x, "c": lambda x: x,
                        "℉": lambda x: (x-32)*5/9, "°f": lambda x: (x-32)*5/9, "f": lambda x: (x-32)*5/9},
        "humidity": {"%": lambda x: x},
        "pressure": {"hpa": lambda x: x, "mb": lambda x: x, "inhg": lambda x: x*33.8638866667},
        "wind": {"km/h": lambda x: x, "kph": lambda x: x, "m/s": lambda x: x*3.6,
                 "mph": lambda x: x*1.609344, "knots": lambda x: x*1.852},
    }
    convert = converters[kind].get(unit)
    if convert is None:
        return None, measured
    number = convert(number)
    bounds = {"temperature": (-80, 65), "humidity": (0, 100),
              "pressure": (800, 1100), "wind": (0, 400)}
    low, high = bounds[kind]
    if not math.isfinite(number) or not low <= number <= high:
        return None, measured
    return round(number, 1), measured


def parse_payload(payload, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(payload, dict) or str(payload.get("code")) != "0":
        raise ValueError("Ecowitt non ha restituito una risposta valida. Verifica configurazione e stato del servizio.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Dati Ecowitt assenti.")
    result = {"schema_version": 2, "timestamp": iso(now), "fetched_at": iso(now),
              "source": "Ecowitt", "observed_at": None}
    fields = [
        ("temperatura_c", "outdoor", "temperature", "temperature"),
        ("umidita_pct", "outdoor", "humidity", "humidity"),
        ("pressione_hpa", "pressure", "relative", "pressure"),
        ("vento_kmh", "wind", "wind_speed", "wind"),
    ]
    observed = {}
    for dest, group, key, kind in fields:
        number, measured = value(data, group, key, kind, now)
        result[dest] = number
        observed[dest] = iso(measured) if measured else None
    if result["temperatura_c"] is None:
        raise ValueError("Temperatura assente, non valida, troppo vecchia o con unità non riconosciuta: dati precedenti conservati.")
    result["observed_at"] = observed["temperatura_c"]
    result["field_observed_at"] = observed
    return result


def raccogli_dati_meteo():
    names = {"application_key": "ECOWITT_APPLICATION_KEY", "api_key": "ECOWITT_API_KEY", "mac": "ECOWITT_MAC"}
    missing = [env for env in names.values() if not os.environ.get(env, "").strip()]
    if missing:
        raise ValueError("Configura i segreti: " + ", ".join(missing))
    params = {key: os.environ[env].strip() for key, env in names.items()}
    params.update(call_back="all", temp_unitid=1, pressure_unitid=3, wind_speed_unitid=7)
    # Non stampare URL, eccezioni HTTP o payload: potrebbero contenere chiavi.
    for attempt in range(3):
        try:
            with urlopen(URL + "?" + urlencode(params), timeout=20) as response:
                payload = json.load(response)
            return parse_payload(payload)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise ValueError("Richiesta Ecowitt non riuscita (HTTP " + str(error.code) + ").") from None
        except (URLError, TimeoutError, OSError):
            if attempt == 2:
                raise ValueError("Ecowitt non raggiungibile dopo tre tentativi.") from None
        except json.JSONDecodeError:
            raise ValueError("Risposta Ecowitt non leggibile.") from None
        time.sleep(2 ** (attempt + 1))


def atomic_write(path, text):
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            tmp = Path(handle.name)
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if tmp and tmp.exists():
            tmp.unlink()


def save_record(record, base=BASE):
    history = base / "storico_albanello.jsonl"
    old = history.read_text(encoding="utf-8") if history.exists() else ""
    lines = [line for line in old.splitlines() if line.strip()]
    # Con una misura datata, non duplicare un campione già acquisito.
    if lines:
        last = json.loads(lines[-1])
        if record.get("observed_at") and record["observed_at"] == last.get("observed_at"):
            return False
    encoded = json.dumps(record, ensure_ascii=False, allow_nan=False)
    atomic_write(history, old.rstrip() + ("\n" if old.strip() else "") + encoded + "\n")
    atomic_write(base / "ultimo_stato.json", json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return True


def main():
    try:
        changed = save_record(raccogli_dati_meteo())
        print("Osservazione salvata." if changed else "Nessuna nuova misura: archivio invariato.")
        return 0
    except ValueError as error:
        print("ERRORE: " + str(error), file=sys.stderr)
        return 1
    except Exception:
        print("ERRORE: raccolta o salvataggio non riusciti. Controllare configurazione e file.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
