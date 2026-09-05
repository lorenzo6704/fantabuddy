#!/usr/bin/env python3
"""Prova piu' fonti di probabili formazioni e dice quale funziona davvero.

Serve perche' molti siti costruiscono la pagina con JavaScript: scaricandola
si ottiene un guscio vuoto. Questo script scarica ogni candidata, misura cosa
contiene e conta quanti dei TUOI giocatori riesce a classificare.

    python sonda.py

Poi si tiene la fonte con il punteggio piu' alto.
"""
from __future__ import annotations
import re, sys
import requests
from bs4 import BeautifulSoup

import rosa
from probabili import norm

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept-Language": "it-IT,it;q=0.9"}

FONTI = {
    "fantacalcio.it":      "https://www.fantacalcio.it/probabili-formazioni-serie-a",
    "sosfanta":            "https://www.sosfanta.com/lista-formazioni/probabili-formazioni-serie-a/",
    "fanta.soccer":        "https://www.fanta.soccer/it/probabiliformazioni/",
    "fco racconto":        "https://www.fantacalcio-online.com/it/consigli-fantacalcio/"
                           "probabili-formazioni-prossima-giornata-serie-a",
    "goal.com":            "https://www.goal.com/it/liste/fantacalcio-formazioni-titolari-"
                           "serie-a-2026-2027-tutte-le-squadre-tipo/blt5527c89487e5b7d3",
}

# parole che segnalano in che blocco della pagina siamo
MARCATORI = [
    ("indisponibile", ("indisponibil", "squalificat", "infortunat", "non convocat")),
    ("panchina",      ("panchina", "subentr", "in dubbio")),
    ("titolare",      ("titolar", "probabile formazione", "probabili formazioni", "undici")),
]


def stato_vicino(testo_norm: str, pos: int) -> str | None:
    """Guarda all'indietro dal nome e prende il marcatore piu' vicino."""
    finestra = testo_norm[max(0, pos - 1500):pos]
    migliore, distanza = None, 10 ** 9
    for stato, parole in MARCATORI:
        for w in parole:
            i = finestra.rfind(w)
            if i >= 0 and (len(finestra) - i) < distanza:
                migliore, distanza = stato, len(finestra) - i
    return migliore


def prova(nome: str, url: str) -> dict:
    try:
        r = requests.get(url, headers=UA, timeout=25)
        r.raise_for_status()
    except Exception as e:
        return {"fonte": nome, "errore": f"{type(e).__name__}: {e}"}

    soup = BeautifulSoup(r.text, "html.parser")
    testo = soup.get_text(" ", strip=True)
    basso = testo.lower()

    trovati, classificati, dettaglio = 0, 0, []
    for ruolo, cognome, club, _, _ in rosa.GIOCATORI:
        chiave = cognome.lower().split()[0]
        pos = basso.find(chiave)
        if pos < 0:
            continue
        trovati += 1
        st = stato_vicino(basso, pos)
        if st:
            classificati += 1
        if len(dettaglio) < 6:
            dettaglio.append(f"{cognome}={st or 'boh'}")

    return {"fonte": nome, "byte": len(r.text), "tabelle": len(soup.find_all("table")),
            "percentuali": len(re.findall(r"\d{1,3}\s*%", testo)),
            "trovati": trovati, "classificati": classificati, "esempi": dettaglio}


STAT_FONTI = {
    "understat 2026": "https://understat.com/league/Serie_A/2026",
    "understat 2025": "https://understat.com/league/Serie_A/2025",
    "fbref standard": "https://fbref.com/en/comps/11/stats/Serie-A-Stats",
    "fbref shooting": "https://fbref.com/en/comps/11/shooting/Serie-A-Stats",
}


def prova_stat():
    print("\n=== SONDA FONTI STATISTICHE (xG) ===")
    for nome, url in STAT_FONTI.items():
        try:
            r = requests.get(url, headers=UA, timeout=25)
            r.raise_for_status()
        except Exception as e:
            print(f"  [KO] {nome:<16} {type(e).__name__}: {str(e)[:60]}")
            continue
        h = r.text
        soup = BeautifulSoup(h, "html.parser")
        n_tab = len(soup.find_all("table"))
        commenti = h.count("<!--")
        ha_json = bool(re.search(r"playersData\s*=", h))
        ha_xg = "xg" in h.lower()
        print(f"  [{'ok' if (ha_json or n_tab or commenti) and ha_xg else '--'}] "
              f"{nome:<16} {len(h)//1024:>4} KB · {n_tab:>2} tabelle · "
              f"{commenti:>3} commenti · playersData={ha_json} · contiene 'xg'={ha_xg}")
    print("=== fine statistiche ===\n")


def main():
    prova_stat()
    righe = [prova(n, u) for n, u in FONTI.items()]
    righe.sort(key=lambda d: -(d.get("classificati", -1)))
    print("\n=== SONDA FONTI PROBABILI ===")
    for d in righe:
        if "errore" in d:
            print(f"  [KO] {d['fonte']:<16} {d['errore'][:70]}")
            continue
        print(f"  [{'ok' if d['classificati'] >= 15 else '--'}] {d['fonte']:<16} "
              f"{d['byte']//1024:>4} KB · {d['tabelle']:>2} tabelle · "
              f"{d['percentuali']:>3} % · tuoi giocatori: {d['trovati']}/25 trovati, "
              f"{d['classificati']}/25 classificati")
        if d["esempi"]:
            print(f"       esempi: {', '.join(d['esempi'])}")
    vincitrice = righe[0]
    print("=== migliore: " + (vincitrice["fonte"] if vincitrice.get("classificati", 0)
                              else "nessuna, servono altre candidate") + " ===\n")


if __name__ == "__main__":
    sys.exit(main())
