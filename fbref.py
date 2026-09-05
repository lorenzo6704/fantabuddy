"""Statistiche avanzate da FBref (dati Opta/StatsBomb): xG, xAG, tiri, minuti.

FBref serve tabelle HTML vere, senza JavaScript. Unica stranezza: molte tabelle
sono racchiuse dentro commenti HTML, quindi prima di leggerle vanno scoperti.

Espone la stessa forma di understat.scarica(), cosi' e' intercambiabile.
"""
from __future__ import annotations
import re, unicodedata
import requests
from bs4 import BeautifulSoup, Comment

STD = "https://fbref.com/en/comps/11/stats/Serie-A-Stats"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept-Language": "it-IT,it;q=0.9,en;q=0.8"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s).upper()


def _tabella(html: str, tid: str):
    soup = BeautifulSoup(html, "html.parser")
    t = soup.find("table", id=tid)
    if t:
        return t
    # FBref nasconde molte tabelle dentro commenti HTML
    for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
        if tid in c:
            t = BeautifulSoup(c, "html.parser").find("table", id=tid)
            if t:
                return t
    return None


def _num(riga, stat, default=0.0):
    c = riga.find(attrs={"data-stat": stat})
    if not c:
        return default
    txt = c.get_text(strip=True).replace(",", "")
    try:
        return float(txt)
    except ValueError:
        return default


def scarica(timeout: int = 25) -> dict[str, dict]:
    r = requests.get(STD, headers=UA, timeout=timeout)
    r.raise_for_status()
    t = _tabella(r.text, "stats_standard")
    if t is None:
        raise RuntimeError("tabella stats_standard non trovata su FBref")

    out = {}
    for tr in t.find_all("tr"):
        cella = tr.find(attrs={"data-stat": "player"})
        if not cella or tr.get("class") and "thead" in tr.get("class"):
            continue
        nome = cella.get_text(strip=True)
        if not nome or nome == "Player":
            continue
        minuti = _num(tr, "minutes")
        per90 = (lambda v: (v / minuti * 90) if minuti > 0 else 0.0)
        xg, xa = _num(tr, "xg"), _num(tr, "xg_assist")
        gare = _num(tr, "games", 1) or 1
        out[nome] = {
            "squadra": (tr.find(attrs={"data-stat": "team"}).get_text(strip=True)
                        if tr.find(attrs={"data-stat": "team"}) else ""),
            "minuti": minuti, "presenze": int(gare),
            "gol": int(_num(tr, "goals")), "assist": int(_num(tr, "assists")),
            "xg": xg, "xa": xa,
            "tiri": int(_num(tr, "shots")), "key_passes": int(_num(tr, "assisted_shots")),
            "gialli": int(_num(tr, "cards_yellow")), "rossi": int(_num(tr, "cards_red")),
            "xg90": per90(xg), "xa90": per90(xa), "tiri90": per90(_num(tr, "shots")),
            "min_per_presenza": minuti / gare,
        }
    if not out:
        raise RuntimeError("FBref: tabella trovata ma vuota")
    return out


def squadre(timeout: int = 25) -> dict[str, dict]:
    """xG fatti e subiti per partita, per misurare la forza dell'avversario."""
    r = requests.get(STD, headers=UA, timeout=timeout)
    r.raise_for_status()
    t = _tabella(r.text, "results2026-2027111_overall") or _tabella(r.text, "stats_squads_standard_for")
    out = {}
    if t is None:
        return out
    for tr in t.find_all("tr"):
        c = tr.find(attrs={"data-stat": "team"}) or tr.find(attrs={"data-stat": "squad"})
        if not c:
            continue
        nome = c.get_text(strip=True)
        gare = _num(tr, "games", 1) or 1
        if not nome or nome in ("Squad", "Team"):
            continue
        out[nome] = {"partite": int(gare),
                     "xg_fatti_pg": _num(tr, "xg") / gare,
                     "xg_subiti_pg": _num(tr, "xg_against") / gare or 1.35,
                     "clean_sheet": 0}
    return out
