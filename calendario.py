"""Calendario Serie A da football-data.org.

Due accortezze che servono davvero:

1. Il piano gratuito concede dieci richieste al minuto. Il workflow lancia
   quattro comandi di fila e ognuno vorrebbe il calendario, quindi le risposte
   vengono messe in cache su disco per mezz'ora e le chiamate rallentate
   quando l'API segnala che il credito del minuto sta finendo.
2. La giornata prossima viene cercata in una finestra di tre settimane invece
   che su tutta la stagione: e' piu' leggero e non dipende da come l'API
   etichetta le partite lontane.
"""
from __future__ import annotations
import datetime as dt
import json, os, time
import requests

API = "https://api.football-data.org/v4/competitions/SA/matches"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache_calendario.json")
TTL = 1800          # mezz'ora
_memoria: dict[str, list] = {}


def _headers():
    tok = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not tok:
        raise RuntimeError("FOOTBALL_DATA_TOKEN mancante")
    return {"X-Auth-Token": tok}


def chiama(url: str, params: dict | None = None, timeout: int = 20, tentativi: int = 3):
    """GET con rispetto del limite: se l'API dice che il minuto e' esaurito,
    aspetta invece di schiantarsi."""
    for n in range(tentativi):
        r = requests.get(url, headers=_headers(), params=params, timeout=timeout)
        if r.status_code == 429:
            attesa = int(r.headers.get("X-RequestCounter-Reset", 0) or 0) + 2
            time.sleep(min(70, max(10, attesa)))
            continue
        r.raise_for_status()
        residue = r.headers.get("X-Requests-Available-Minute")
        if residue is not None and residue.isdigit() and int(residue) <= 1:
            time.sleep(8)      # lascia respirare il contatore
        return r.json()
    raise RuntimeError(f"football-data: limite di chiamate superato su {url}")


def _cache_leggi(chiave: str):
    if chiave in _memoria:
        return _memoria[chiave]
    if os.path.exists(CACHE):
        try:
            d = json.load(open(CACHE, encoding="utf-8"))
            if d.get("chiave") == chiave and time.time() - d.get("quando", 0) < TTL:
                return d["dati"]
        except Exception:
            pass
    return None


def _cache_scrivi(chiave: str, dati):
    _memoria[chiave] = dati
    try:
        json.dump({"chiave": chiave, "quando": time.time(), "dati": dati},
                  open(CACHE, "w", encoding="utf-8"))
    except Exception:
        pass


def partite(da: dt.date | None = None, a: dt.date | None = None) -> list[dict]:
    """Partite fra due date. Senza argomenti: da ieri a tre settimane avanti."""
    oggi = dt.date.today()
    da = da or oggi - dt.timedelta(days=8)
    a = a or oggi + dt.timedelta(days=21)
    chiave = f"{da}_{a}"

    grezzo = _cache_leggi(chiave)
    if grezzo is None:
        grezzo = chiama(API, {"dateFrom": da.isoformat(), "dateTo": a.isoformat()})
        _cache_scrivi(chiave, grezzo)

    out = []
    for m in grezzo.get("matches", []):
        out.append({
            "id": m.get("id"),
            "giornata": m.get("matchday"),
            "stato": m.get("status"),
            "inizio": dt.datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")),
            "casa": m["homeTeam"]["shortName"] or m["homeTeam"]["name"],
            "ospite": m["awayTeam"]["shortName"] or m["awayTeam"]["name"],
        })
    return out


def prossima_giornata(adesso: dt.datetime | None = None):
    """(giornata, kickoff_di_apertura, [tutte le partite del turno]).

    Il turno restituito comprende anche le partite gia' giocate: la formazione
    si blocca al primo fischio del turno, non al prossimo match rimasto.
    """
    adesso = adesso or dt.datetime.now(dt.timezone.utc)
    tutte = partite()
    future = [p for p in tutte if p["inizio"] > adesso
              and p["stato"] in ("SCHEDULED", "TIMED")]
    if not future:
        # finestra piu' larga: sosta lunga per le nazionali
        tutte = partite(a=dt.date.today() + dt.timedelta(days=60))
        future = [p for p in tutte if p["inizio"] > adesso
                  and p["stato"] in ("SCHEDULED", "TIMED")]
        if not future:
            return None
    g = min(p["giornata"] for p in future if p["giornata"] is not None)
    turno = sorted([p for p in tutte if p["giornata"] == g], key=lambda p: p["inizio"])
    return g, turno[0]["inizio"], turno


def giornata_conclusa(adesso: dt.datetime | None = None):
    """L'ultima giornata con tutte le partite finite, se e' completa."""
    tutte = partite()
    finite = [p for p in tutte if p["stato"] == "FINISHED" and p["giornata"]]
    if not finite:
        return None
    g = max(p["giornata"] for p in finite)
    del_turno = [p for p in tutte if p["giornata"] == g]
    if any(p["stato"] != "FINISHED" for p in del_turno):
        return None
    return g, del_turno


def avversario(club: str, turno: list[dict]) -> tuple[str, bool] | None:
    for p in turno:
        if club.lower() in p["casa"].lower():
            return p["ospite"], True
        if club.lower() in p["ospite"].lower():
            return p["casa"], False
    return None


def radiografia() -> str:
    """Per la diagnosi: che cosa restituisce davvero l'API."""
    tutte = partite()
    per_stato: dict[str, int] = {}
    for p in tutte:
        per_stato[p["stato"]] = per_stato.get(p["stato"], 0) + 1
    prossime = sorted([p for p in tutte if p["inizio"] > dt.datetime.now(dt.timezone.utc)],
                      key=lambda p: p["inizio"])[:4]
    righe = [f"{len(tutte)} partite in finestra, stati: {per_stato}"]
    for p in prossime:
        righe.append(f"    g{p['giornata']} {p['inizio']:%d/%m %H:%M} "
                     f"{p['casa']}-{p['ospite']} [{p['stato']}]")
    return "\n".join(righe)
