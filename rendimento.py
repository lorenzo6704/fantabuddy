"""Rendimento reale dei tuoi giocatori, aggiornato a fine giornata.

A turno concluso il bot chiede a football-data.org il dettaglio di ogni partita
e ne estrae marcatori e assistman. I numeri si accumulano in `rendimento.json`,
che il workflow ricommitta nel repository: cosi' la stagione si costruisce da
sola e `rosa.py` non va piu' toccato a mano.

Cosa NON si puo' avere: il fantavoto e la media voto. Sono giudizi redazionali
di Gazzetta e Fantacalcio.it, non dati pubblici, e nessuna fonte gratuita li
espone. Il modello continua quindi a usare 6.0 come voto base e prevede i
bonus, che sono la parte che sposta la classifica.

Le stime restano prudenti finche' il campione e' piccolo: all'inizio pesano di
piu' i valori scritti in rosa.py, e man mano che le giornate passano prende il
sopravvento quello che il giocatore fa davvero sul campo.
"""
from __future__ import annotations
import json, os, re, unicodedata
import requests

import rosa
from calendario import _headers

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendimento.json")
DETTAGLIO = "https://api.football-data.org/v4/matches/{id}"
PESO_STIMA = 6.0     # a quante giornate di dati equivale la stima iniziale


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s).upper()


COGNOMI = {norm(g[1]): g[1] for g in rosa.GIOCATORI}


def _mio(nome_api: str) -> str | None:
    """Aggancia un nome dell'API a un giocatore della rosa, per cognome."""
    n = norm(nome_api)
    for chiave, nome in COGNOMI.items():
        if n.endswith(chiave) or chiave in n:
            return nome
    return None


def leggi() -> dict:
    if not os.path.exists(FILE):
        return {"giornate": [], "giocatori": {}}
    try:
        return json.load(open(FILE, encoding="utf-8"))
    except Exception:
        return {"giornate": [], "giocatori": {}}


def scrivi(d: dict):
    json.dump(d, open(FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def registra(giornata: int, partite: list[dict], timeout: int = 20) -> dict:
    """Aggiunge i bonus di una giornata conclusa. Idempotente."""
    d = leggi()
    if giornata in d["giornate"]:
        return d

    for p in partite:
        if not p.get("id"):
            continue
        r = requests.get(DETTAGLIO.format(id=p["id"]), headers=_headers(), timeout=timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"football-data {r.status_code} sul match {p['id']}: "
                               f"{r.text[:160]}")
        m = r.json()
        for gol in (m.get("goals") or []):
            for chi, campo in ((gol.get("scorer"), "gol"), (gol.get("assist"), "assist")):
                nome = _mio((chi or {}).get("name", ""))
                if nome:
                    voce = d["giocatori"].setdefault(nome, {"gol": 0, "assist": 0})
                    voce[campo] += 1

    # una giornata giocata per tutti quelli il cui club era in campo
    club_in_campo = {c.lower() for p in partite for c in (p["casa"], p["ospite"])}
    for ruolo, nome, club, *_ in rosa.GIOCATORI:
        if any(club.lower() in c or c in club.lower() for c in club_in_campo):
            voce = d["giocatori"].setdefault(nome, {"gol": 0, "assist": 0})
            voce["giornate"] = voce.get("giornate", 0) + 1

    d["giornate"] = sorted(set(d["giornate"] + [giornata]))
    scrivi(d)
    return d


def stime(nome: str, gol90_iniziale: float, ass90_iniziale: float) -> tuple[float, float, str]:
    """Fonde la stima iniziale con il rendimento osservato.

    Ritorna (gol90, ass90, spiegazione). Finche' le giornate sono poche la
    stima iniziale domina; dopo una decina di partite conta quasi solo il campo.
    """
    d = leggi().get("giocatori", {}).get(nome)
    n = (d or {}).get("giornate", 0)
    if not d or n == 0:
        return gol90_iniziale, ass90_iniziale, "stima iniziale"

    # una presenza vale circa 78 minuti, quindi 0.87 di una partita intera
    partite_equivalenti = n * 0.87
    gol_oss = d["gol"] / max(0.5, partite_equivalenti)
    ass_oss = d["assist"] / max(0.5, partite_equivalenti)
    peso = n / (n + PESO_STIMA)
    g = gol90_iniziale * (1 - peso) + gol_oss * peso
    a = ass90_iniziale * (1 - peso) + ass_oss * peso
    return g, a, (f"{d['gol']} gol e {d['assist']} assist in {n} giornate, "
                  f"pesati al {int(peso*100)}%")
