"""Stato persistente del bot: offset Telegram, correzioni, giornate inviate.

Vive in un file JSON che il workflow di GitHub Actions ricommitta nel repo.
Le correzioni valgono per una sola giornata e si azzerano da sole quando il
numero di giornata cambia: non devi ricordarti di ripulire niente.
"""
from __future__ import annotations
import json, os

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stato.json")
VUOTO = {"offset": 0, "giornata": None, "correzioni": {},
         "inviate": [], "ultimo_undici": [], "chiuso": False}


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


def allinea_giornata(d: dict, giornata: int) -> dict:
    """Se siamo passati alla giornata successiva, le correzioni scadono."""
    if d.get("giornata") != giornata:
        d["giornata"] = giornata
        d["correzioni"] = {}
        d["chiuso"] = False
    return d
