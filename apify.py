"""xG e xA da Understat, passando per Apify.

Understat e FBref rifiutano le richieste che arrivano dai datacenter, e i
server di GitHub sono datacenter: da li' non si raggiungono. Apify esegue lo
scraping dalla propria rete e ci restituisce JSON gia' pulito.

Serve un account gratuito su apify.com e un token, da mettere nel secret
APIFY_TOKEN. Senza quel secret questo provider si disattiva da solo e il bot
continua con le altre fonti.

Se Apify risponde che l'input non e' valido, l'errore elenca i campi che si
aspetta: puoi correggerli senza toccare il codice, mettendo il JSON giusto nel
secret APIFY_INPUT.
"""
from __future__ import annotations
import json, os
import requests

ATTORE = "mirthful_radish~understat-xg-football-scraper"
URL = f"https://api.apify.com/v2/acts/{ATTORE}/run-sync-get-dataset-items"
INPUT_DEFAULT = {"league": "Serie A", "season": "2026", "dataType": "league_players"}


def _input() -> dict:
    grezzo = os.environ.get("APIFY_INPUT")
    if grezzo:
        try:
            return json.loads(grezzo)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"APIFY_INPUT non e' JSON valido: {e}")
    return INPUT_DEFAULT


def _righe(timeout: int = 180) -> list[dict]:
    tok = os.environ.get("APIFY_TOKEN")
    if not tok:
        raise RuntimeError("APIFY_TOKEN non impostato")
    r = requests.post(URL, params={"token": tok}, json=_input(), timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"Apify {r.status_code}: {r.text[:300]}")
    dati = r.json()
    if not isinstance(dati, list) or not dati:
        raise RuntimeError("Apify ha risposto senza dati")
    return dati


def _f(d: dict, *chiavi, default=0.0):
    """I nomi dei campi cambiano fra scraper: proviamo le varianti note."""
    for k in chiavi:
        if k in d and d[k] not in (None, ""):
            try:
                return float(d[k])
            except (TypeError, ValueError):
                pass
    return default


def scarica(timeout: int = 180) -> dict[str, dict]:
    out = {}
    for p in _righe(timeout):
        nome = p.get("player_name") or p.get("playerName") or p.get("name")
        if not nome:
            continue
        minuti = _f(p, "time", "minutes", "minutesPlayed")
        per90 = (lambda v: (v / minuti * 90) if minuti > 0 else 0.0)
        xg, xa = _f(p, "xG", "xg", "expectedGoals"), _f(p, "xA", "xa", "expectedAssists")
        gare = _f(p, "games", "appearances", default=1) or 1
        out[nome] = {
            "squadra": p.get("team_title") or p.get("team") or "",
            "minuti": minuti, "presenze": int(gare),
            "gol": int(_f(p, "goals")), "assist": int(_f(p, "assists")),
            "xg": xg, "xa": xa,
            "tiri": int(_f(p, "shots")), "key_passes": int(_f(p, "key_passes", "keyPasses")),
            "gialli": int(_f(p, "yellow_cards", "yellowCards")),
            "rossi": int(_f(p, "red_cards", "redCards")),
            "xg90": per90(xg), "xa90": per90(xa),
            "tiri90": per90(_f(p, "shots")),
            "min_per_presenza": minuti / gare,
        }
    if not out:
        raise RuntimeError("Apify: nessun giocatore riconosciuto nella risposta")
    return out


def squadre(timeout: int = 180) -> dict[str, dict]:
    """Aggrega gli xG per club dai dati dei giocatori: basta a stimare la
    forza offensiva, non quella difensiva."""
    per_club: dict[str, dict] = {}
    for s in scarica(timeout).values():
        c = s["squadra"]
        if not c:
            continue
        d = per_club.setdefault(c, {"xg": 0.0, "minuti": 0.0})
        d["xg"] += s["xg"]
        d["minuti"] += s["minuti"]
    return {c: {"partite": max(1, round(d["minuti"] / 990)),
                "xg_fatti_pg": d["xg"] / max(1, round(d["minuti"] / 990)),
                "xg_subiti_pg": 1.35, "clean_sheet": 0}
            for c, d in per_club.items()}
