"""Stato persistente del bot: offset Telegram, correzioni, giornate inviate.

Vive in un file JSON che il workflow di GitHub Actions ricommitta nel repo.
Le correzioni valgono per una sola giornata e si azzerano da sole quando il
numero di giornata cambia: non devi ricordarti di ripulire niente.
"""
from __future__ import annotations
import json, os

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stato.json")
VUOTO = {"offset": 0, "giornata": None, "correzioni": {}, "inviate": [],
         "ultimo_undici": [], "chiuso": False,
         # Numero della giornata: il bot lo incrementa a ogni turno nuovo.
         # Va seminato una volta sola, scrivendo qui il numero giusto e la
         # data della partita di apertura di quel turno.
         "numero_giornata": None, "numero_riferito_a": None}


def leggi() -> dict:
    if not os.path.exists(FILE):
        return dict(VUOTO)
    try:
        d = json.load(open(FILE, encoding="utf-8"))
    except Exception:
        return dict(VUOTO)
    for k, v in VUOTO.items():
        d.setdefault(k, v)
    return d


def scrivi(d: dict):
    json.dump(d, open(FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def numero_giornata(d: dict, chiave: str) -> int | None:
    """Tiene il conto delle giornate senza dipendere da fonti esterne.
    La prima volta va seminato a mano in stato.json; poi si aggiorna da solo
    ogni volta che cambia la data di apertura del turno."""
    n, riferito = d.get("numero_giornata"), d.get("numero_riferito_a")
    if n is None:
        return None
    if riferito == chiave:
        return n
    if riferito is None or chiave > riferito:
        d["numero_giornata"] = n + (1 if riferito else 0)
        d["numero_riferito_a"] = chiave
        return d["numero_giornata"]
    return n


def allinea_giornata(d: dict, chiave) -> dict:
    """La chiave e' la data di apertura del turno. Quando cambia turno, le
    correzioni scadono da sole."""
    if d.get("giornata") != chiave:
        d["giornata"] = chiave
        d["correzioni"] = {}
        d["chiuso"] = False
    return d
