"""Statistiche di campionato da understat.com.

Understat pubblica i dati di Serie A dentro la pagina della lega, in una
variabile JS `playersData = JSON.parse('...')`. Si aggiorna dopo ogni giornata,
quindi il bot legge sempre numeri correnti.

Campi che usiamo: minuti, gol, assist, xG, xA, tiri, key passes, cartellini.
"""
from __future__ import annotations
import json, re, codecs, datetime as dt
import requests

BASE = "https://understat.com/league/Serie_A/{stagione}"
UA = {"User-Agent": "Mozilla/5.0 (fantabot; contatto: uso personale)"}


def _estrai(html: str, var: str) -> list[dict]:
    m = re.search(var + r"\s*=\s*JSON\.parse\('(.*?)'\)", html, re.S)
    if not m:
        raise RuntimeError(f"variabile {var} non trovata: understat ha cambiato pagina")
    return json.loads(codecs.decode(m.group(1), "unicode_escape"))


def stagione_corrente(oggi: dt.date | None = None) -> int:
    oggi = oggi or dt.date.today()
    return oggi.year if oggi.month >= 7 else oggi.year - 1


def scarica(stagione: int | None = None, timeout: int = 20) -> dict[str, dict]:
    """Ritorna {nome_understat: statistiche} con le medie per 90 minuti."""
    stagione = stagione or stagione_corrente()
    r = requests.get(BASE.format(stagione=stagione), headers=UA, timeout=timeout)
    r.raise_for_status()
    grezzi = _estrai(r.text, "playersData")

    out = {}
    for p in grezzi:
        minuti = float(p.get("time", 0) or 0)
        per90 = (lambda x: (float(x or 0) / minuti * 90) if minuti > 0 else 0.0)
        out[p["player_name"]] = {
            "squadra": p.get("team_title", ""),
            "minuti": minuti,
            "presenze": int(p.get("games", 0) or 0),
            "gol": int(p.get("goals", 0) or 0),
            "assist": int(p.get("assists", 0) or 0),
            "xg": float(p.get("xG", 0) or 0),
            "xa": float(p.get("xA", 0) or 0),
            "tiri": int(p.get("shots", 0) or 0),
            "key_passes": int(p.get("key_passes", 0) or 0),
            "gialli": int(p.get("yellow_cards", 0) or 0),
            "rossi": int(p.get("red_cards", 0) or 0),
            "xg90": per90(p.get("xG")),
            "xa90": per90(p.get("xA")),
            "tiri90": per90(p.get("shots")),
            "min_per_presenza": minuti / max(1, int(p.get("games", 1) or 1)),
        }
    return out


def squadre(stagione: int | None = None, timeout: int = 20) -> dict[str, dict]:
    """Dati aggregati per club: xG fatti e subiti per partita (forza avversario)."""
    stagione = stagione or stagione_corrente()
    r = requests.get(BASE.format(stagione=stagione), headers=UA, timeout=timeout)
    r.raise_for_status()
    grezzi = _estrai(r.text, "teamsData")
    out = {}
    for t in grezzi.values():
        gare = t["history"]
        n = max(1, len(gare))
        out[t["title"]] = {
            "partite": len(gare),
            "xg_fatti_pg": sum(g["xG"] for g in gare) / n,
            "xg_subiti_pg": sum(g["xGA"] for g in gare) / n,
            "clean_sheet": sum(1 for g in gare if g["missed"] == 0),
        }
    return out
