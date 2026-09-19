"""Probabili formazioni da Fantacalcio.it, senza input manuale.

La pagina non usa tabelle: pubblica un testo continuo, un blocco per squadra,
fatto cosi'

    Juventus 4-2-3-1 Vicario 90% Kalulu 90% ... Panchina Contini 1% ...

Il lettore riconosce l'inizio di ogni blocco dal modulo (4-2-3-1, 3-5-2...),
poi legge le coppie "nome percentuale" fino al blocco successivo. La parola
"Panchina" fa passare dai titolari alle riserve.

Chi non compare ne' fra i titolari ne' in panchina non e' convocato: viene
segnalato come indisponibile invece che stimato, che e' l'informazione che
serve davvero per non schierarlo.
"""
from __future__ import annotations
import datetime as dt
import re, unicodedata
import requests
from bs4 import BeautifulSoup

URL = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept-Language": "it-IT,it;q=0.9"}

SQUADRE = ["Atalanta", "Bologna", "Cagliari", "Como", "Fiorentina", "Frosinone",
           "Genoa", "Inter", "Juventus", "Lazio", "Lecce", "Milan", "Monza",
           "Napoli", "Parma", "Roma", "Sassuolo", "Torino", "Udinese", "Venezia"]

MODULO = r"\d-\d-\d(?:-\d)?"
MESI = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5,
        "giugno": 6, "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10,
        "novembre": 11, "dicembre": 12}
GIORNI = "lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica"
DATA = re.compile(
    r"(?:" + GIORNI + r")[\s,]+(\d{1,2})\s+(" + "|".join(MESI) + r")[\s,]+"
    r"(\d{1,2})[:.](\d{2})", re.I)
TITOLO_GIORNATA = re.compile(r"(\d{1,2})\s*[\u00aa\u00b0a]?\s*Giornata", re.I)
STAGIONE = re.compile(r"(20\d{2})\s*/\s*(20\d{2})")
INTESTAZIONE = re.compile(r"\b(" + "|".join(SQUADRE) + r")\s+(" + MODULO + r")\b")
PERCENTUALE = re.compile(r"(\d{1,3})\s*%")
FINE = re.compile(r"Ultimo aggiornamento|Presentazione squadre", re.I)


def _senza_accenti(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s).upper()


def _coppie(blocco: str) -> list[tuple[str, float, str]]:
    """Da 'Vicario 90% Kalulu 90% Panchina Contini 1%' a [(nome, prob, stato)]."""
    fuori, cursore, stato = [], 0, "titolare"
    for m in PERCENTUALE.finditer(blocco):
        pezzo = blocco[cursore:m.start()]
        cursore = m.end()
        if re.search(r"\bpanchina\b", pezzo, re.I):
            stato = "panchina"
        # il nome e' l'ultima cosa scritta prima della percentuale
        pezzo = re.sub(r"^.*\bpanchina\b", "", pezzo, flags=re.I | re.S)
        pezzo = re.sub(r"^.*?" + MODULO, "", pezzo).strip(" -–—·|,")
        nome = " ".join(pezzo.split()[-3:]).strip()
        nome = re.sub(r"^(?:[A-Z]\s)?", "", nome).strip()
        if not nome or len(nome) > 30 or not re.search(r"[A-Za-z]{3}", nome):
            continue
        fuori.append((nome, int(m.group(1)) / 100, stato))
    return fuori


def testo_pagina(timeout: int = 25) -> str:
    r = requests.get(URL, headers=UA, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)


def scarica(timeout: int = 25) -> dict:
    return analizza(testo_pagina(timeout))


def analizza(testo: str) -> dict:
    """Separata da scarica() per poterla provare senza rete."""
    squadre: dict[str, dict] = {}
    tagli = [(m.start(), m.end(), m.group(1)) for m in INTESTAZIONE.finditer(testo)]
    for i, (inizio, dopo_intest, club) in enumerate(tagli):
        limite = tagli[i + 1][0] if i + 1 < len(tagli) else len(testo)
        blocco = testo[dopo_intest:limite]
        f = FINE.search(blocco)
        if f:
            blocco = blocco[:f.start()]
        chiave = norm(club)
        sez = squadre.setdefault(chiave, {"giocatori": [], "clean_sheet": None,
                                          "ufficiale": False})
        for nome, prob, stato in _coppie(blocco):
            sez["giocatori"].append({
                "nome": norm(nome), "grezzo": nome, "prob": prob, "stato": stato,
                "fonti": {"Fantacalcio.it": prob}, "spread": 0.0, "nota": "",
                "ufficiale": False,
            })
        if re.search(r"formazione\s+ufficiale", blocco, re.I):
            sez["ufficiale"] = True
    return squadre


def giornata(testo: str) -> int | None:
    m = TITOLO_GIORNATA.search(testo[:600])
    return int(m.group(1)) if m else None


def partite(testo: str, fuso: str = "Europe/Rome") -> list[dict]:
    """Ricava il turno dalla pagina: ogni data introduce una partita, e le due
    squadre che seguono sono, in ordine, quella di casa e quella ospite."""
    from zoneinfo import ZoneInfo
    piano = _senza_accenti(testo)
    m = STAGIONE.search(piano[:600])
    anno_inizio = int(m.group(1)) if m else dt.date.today().year

    eventi = []
    for d in DATA.finditer(piano):
        eventi.append(("data", d.start(), d.groups()))
    for t in INTESTAZIONE.finditer(piano):
        eventi.append(("club", t.start(), t.group(1)))
    eventi.sort(key=lambda e: e[1])

    out, in_corso = [], None
    for tipo, _, dato in eventi:
        if tipo == "data":
            giorno, mese_nome, ora, minuto = dato
            mese = MESI[mese_nome.lower()]
            anno = anno_inizio if mese >= 7 else anno_inizio + 1
            quando = dt.datetime(anno, mese, int(giorno), int(ora), int(minuto),
                                 tzinfo=ZoneInfo(fuso)).astimezone(dt.timezone.utc)
            in_corso = {"inizio": quando, "casa": None, "ospite": None}
            out.append(in_corso)
        elif in_corso is not None:
            if in_corso["casa"] is None:
                in_corso["casa"] = dato
            elif in_corso["ospite"] is None:
                in_corso["ospite"] = dato
    return [p for p in out if p["casa"] and p["ospite"]]


ORDINE = {"indisponibile": 0, "titolare": 1, "panchina": 2}


def _fra(righe, chiave):
    cand = [g for g in righe if g["nome"] == chiave] or \
           [g for g in righe if g["nome"].startswith(chiave)] or \
           [g for g in righe if chiave in g["nome"]]
    return sorted(cand, key=lambda g: ORDINE.get(g["stato"], 3))[0] if cand else None


def cerca(dati: dict, cognome: str, club: str):
    """Nella sezione del club; se il club non c'e', ricerca globale.
    None significa non convocato, non 'dato mancante'."""
    chiave = norm(cognome)
    sez = dati.get(norm(club))
    if sez:
        g = _fra(sez["giocatori"], chiave)
        if g:
            return g
        if sez["giocatori"]:
            return {"nome": chiave, "grezzo": cognome, "prob": 0.05,
                    "stato": "non convocato", "fonti": {}, "spread": 0.0,
                    "nota": "non compare fra titolari e panchina", "ufficiale": False}
    return _fra([g for s in dati.values() for g in s["giocatori"]], chiave)


def formazione_ufficiale(dati: dict, club: str) -> bool:
    sez = dati.get(norm(club))
    return bool(sez and sez.get("ufficiale"))


def clean_sheet(dati: dict, club: str):
    return None


def elenco(dati: dict) -> list[str]:
    out = []
    for club, s in sorted(dati.items()):
        if s["giocatori"]:
            out.append(f"{club} ({len(s['giocatori'])}): " +
                       ", ".join(g["grezzo"] + f" {int(g['prob']*100)}%"
                                 for g in s["giocatori"][:5]))
    return out


def ispeziona(timeout: int = 25) -> dict:
    r = requests.get(URL, headers=UA, timeout=timeout)
    r.raise_for_status()
    testo = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
    d = analizza(testo)
    return {"byte": len(r.text), "tabelle": 0,
            "percentuali": len(PERCENTUALE.findall(testo)),
            "righe_riconosciute": sum(len(s["giocatori"]) for s in d.values()),
            "assaggio": testo[:400]}
