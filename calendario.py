"""Calendario Serie A da football-data.org (piano gratuito, serve una API key).

Registrazione: https://www.football-data.org/client/register
La chiave va in FOOTBALL_DATA_TOKEN.
"""
from __future__ import annotations
import os, datetime as dt
import requests

API = "https://api.football-data.org/v4/competitions/SA/matches"


def _headers():
    tok = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not tok:
        raise RuntimeError("FOOTBALL_DATA_TOKEN mancante")
    return {"X-Auth-Token": tok}


def partite(timeout: int = 20) -> list[dict]:
    r = requests.get(API, headers=_headers(), timeout=timeout)
    r.raise_for_status()
    out = []
    for m in r.json().get("matches", []):
        out.append({
            "giornata": m.get("matchday"),
            "stato": m.get("status"),
            "inizio": dt.datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")),
            "casa": m["homeTeam"]["shortName"] or m["homeTeam"]["name"],
            "ospite": m["awayTeam"]["shortName"] or m["awayTeam"]["name"],
        })
    return out


def prossima_giornata(adesso: dt.datetime | None = None):
    """Ritorna (numero_giornata, primo_kickoff, [partite]) della prima giornata
    non ancora iniziata."""
    adesso = adesso or dt.datetime.now(dt.timezone.utc)
    future = [p for p in partite() if p["inizio"] > adesso and p["stato"] in
              ("SCHEDULED", "TIMED")]
    if not future:
        return None
    g = min(p["giornata"] for p in future)
    del_turno = sorted([p for p in future if p["giornata"] == g],
                       key=lambda p: p["inizio"])
    return g, del_turno[0]["inizio"], del_turno


def avversario(club: str, turno: list[dict]) -> tuple[str, bool] | None:
    """(avversario, in_casa) per un club in una giornata. None se riposa."""
    for p in turno:
        if club.lower() in p["casa"].lower():
            return p["ospite"], True
        if club.lower() in p["ospite"].lower():
            return p["casa"], False
    return None
