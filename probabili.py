"""Probabili formazioni: aggregato di quattro redazioni, zero input manuale.

Fonte: fantacalcio-online.com, che pubblica in tabella la percentuale di
schierabilita' che danno Fantacalcio.it, Gazzetta, SOS Fanta e Sky, piu' la
media pesata, l'elenco degli indisponibili e la quota di porta inviolata della
partita. Si aggiorna due volte al giorno fino al fischio d'inizio.

E' una fonte sola ma gia' in consenso: il disaccordo fra le redazioni diventa
un numero (lo spread), che il bot usa per dire quanto e' affidabile una riga
invece di far finta che sia certa.
"""
from __future__ import annotations
import re, unicodedata
import requests
from bs4 import BeautifulSoup

URL = ("https://www.fantacalcio-online.com/it/serie-a/2026-2027/"
       "probabili-formazioni/ultima-giornata")
UA = {"User-Agent": "Mozilla/5.0 (fantabot; uso personale)"}
COLONNE = ["Fc", "Gaz", "SOS", "Sky"]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s).upper()


def _pct(cella: str):
    m = re.search(r"(\d+)\s*%", cella or "")
    return int(m.group(1)) / 100 if m else None


# Righe tipo:  "P BIJLOWJ 90% 90% 95% – 91%"  oppure  "A DAVIS K 90% 90% 91%"
RIGA = re.compile(
    r"\b([PDCA])\s+([A-Z\u00c0-\u00dc][A-Za-z\u00c0-\u00ff'\u2019\-\. ]{1,28}?)\s+"
    r"((?:\d{1,3}\s*%|[\u2013\u2014-])\s+){1,4}(\d{1,3})\s*%")


def _da_testo(testo: str) -> list[dict]:
    """Lettore di riserva: cerca le righe direttamente nel testo della pagina,
    senza dipendere da come sono impaginate le tabelle."""
    fuori = []
    for m in RIGA.finditer(testo):
        nome = m.group(2)
        valori = [int(x) / 100 for x in re.findall(r"(\d{1,3})\s*%", m.group(0))]
        media = valori[-1]
        fonti = {c: v for c, v in zip(COLONNE, valori[:-1])}
        fuori.append({
            "nome": norm(nome), "grezzo": f"{m.group(1)} {nome.strip()}",
            "prob": media, "stato": "titolare" if media >= 0.6 else "panchina",
            "fonti": fonti,
            "spread": (max(valori[:-1]) - min(valori[:-1])) if len(valori) > 2 else 0.0,
            "nota": "", "ufficiale": False,
        })
    return fuori


def ispeziona(timeout: int = 25) -> dict:
    """Misure grezze della pagina: servono a capire se il contenuto c'e'
    davvero nell'HTML o se lo costruisce il browser con JavaScript."""
    r = requests.get(URL, headers=UA, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    testo = soup.get_text(" ", strip=True)
    return {"byte": len(r.text), "tabelle": len(soup.find_all("table")),
            "percentuali": len(re.findall(r"\d{1,3}\s*%", testo)),
            "righe_riconosciute": len(_da_testo(testo)),
            "assaggio": testo[:400]}


def scarica(timeout: int = 25) -> dict:
    """{CLUB: {'giocatori': [...], 'clean_sheet': float|None}}"""
    r = requests.get(URL, headers=UA, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    squadre: dict[str, dict] = {}
    club = None
    stato_corrente = "titolare"

    for nodo in soup.find_all(["h1", "h2", "h3", "h4", "table", "ul", "p", "em", "i",
                               "strong", "b", "div", "section"]):
        testo = nodo.get_text(" ", strip=True)

        if nodo.name in ("h1", "h2", "h3", "h4") and 2 < len(testo) < 40:
            club = norm(testo)
            squadre.setdefault(club, {"giocatori": [], "clean_sheet": None})
            continue

        m = re.search(r"Porta inviolata\s+([A-Za-z'\u00e0-\u00fc ]+?)\s+(\d+)\s*%", testo)
        if m:
            chi = norm(m.group(1))
            squadre.setdefault(chi, {"giocatori": [], "clean_sheet": None})
            squadre[chi]["clean_sheet"] = int(m.group(2)) / 100

        if club is None:
            continue

        if "Probabili titolari" in testo and len(testo) < 140:
            stato_corrente = "titolare"
        elif "Probabile panchina" in testo and len(testo) < 140:
            stato_corrente = "panchina"

        if nodo.name == "table":
            intest = " ".join(c.get_text(strip=True).lower() for c in nodo.find_all("th"))
            stato = "panchina" if "panchina" in intest else (
                "titolare" if "titolare" in intest else stato_corrente)
            for tr in nodo.find_all("tr"):
                celle = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
                if len(celle) < 3:
                    continue
                nome = re.sub(r"^[PDCA]\s+", "", celle[0])
                fonti, valori = {}, []
                for i, col in enumerate(COLONNE, start=1):
                    if i < len(celle):
                        v = _pct(celle[i])
                        if v is not None:
                            fonti[col] = v
                            valori.append(v)
                media = next((_pct(c) for c in reversed(celle) if _pct(c) is not None), None)
                if media is None:
                    continue
                # ultima colonna: segno di conferma quando esce la formazione ufficiale
                coda = " ".join(celle[len(fonti) + 2:]).lower()
                uff = any(t in coda for t in ("uff", "\u2713", "\u2714", "confermat", "\u2705"))
                squadre[club]["giocatori"].append({
                    "nome": norm(nome), "grezzo": nome, "prob": media,
                    "stato": stato, "fonti": fonti,
                    "spread": (max(valori) - min(valori)) if len(valori) > 1 else 0.0,
                    "nota": "", "ufficiale": uff,
                })

        if "Infortunat" in testo and len(testo) < 1200:
            for c1, c2 in re.findall(
                    r"([A-Z\u00c0-\u00da][A-Z\u00c0-\u00da'\u2019\- ]{2,})\s*(Infortunat\w*[^,\n]*)", testo):
                squadre[club]["giocatori"].append({
                    "nome": norm(c1), "grezzo": c1.strip(), "prob": 0.0,
                    "stato": "indisponibile", "fonti": {}, "spread": 0.0,
                    "nota": c2.strip(), "ufficiale": False,
                })

    # Se le tabelle non si sono lette (impaginazione diversa), ci riproviamo
    # sul testo, spezzato per squadra sulle intestazioni trovate.
    if sum(1 for s in squadre.values() for g in s["giocatori"]
           if g["stato"] != "indisponibile") < 40:
        testo = soup.get_text(" ", strip=True)
        titoli = [(m.start(), norm(m.group(1)))
                  for m in re.finditer(r"##\s*([A-Za-z\u00c0-\u00ff' ]{3,20})", testo)]
        righe = _da_testo(testo)
        if righe:
            for g in righe:
                pos = testo.find(g["grezzo"].split()[-1])
                club_g = None
                for start, nome_club in titoli:
                    if start <= pos:
                        club_g = nome_club
                squadre.setdefault(club_g or "SCONOSCIUTA",
                                   {"giocatori": [], "clean_sheet": None})
                squadre[club_g or "SCONOSCIUTA"]["giocatori"].append(g)
    return squadre


ORDINE = {"indisponibile": 0, "titolare": 1, "panchina": 2}


def _fra(righe, chiave):
    cand = [g for g in righe if g["nome"].startswith(chiave)]
    if not cand:
        cand = [g for g in righe if chiave in g["nome"] or g["nome"] in chiave]
    return sorted(cand, key=lambda g: ORDINE.get(g["stato"], 3))[0] if cand else None


def cerca(dati: dict, cognome: str, club: str):
    """Cerca prima dentro la sezione del club; se non la trova (impaginazione
    cambiata, nome della squadra scritto diversamente) ripiega su una ricerca
    globale. Cosi' un cognome raro si aggancia comunque."""
    chiave = norm(cognome)
    sez = dati.get(norm(club))
    if sez:
        g = _fra(sez["giocatori"], chiave)
        if g:
            return g
    tutte = [g for s in dati.values() for g in s["giocatori"]]
    return _fra(tutte, chiave)


def elenco(dati: dict) -> list[str]:
    """Serve alla diagnosi: mostra cosa ha letto davvero dalla pagina."""
    out = []
    for club, s in sorted(dati.items()):
        if s["giocatori"]:
            nomi = ", ".join(g["grezzo"] for g in s["giocatori"][:6])
            out.append(f"{club} ({len(s['giocatori'])}): {nomi}")
    return out


def formazione_ufficiale(dati: dict, club: str) -> bool:
    """True quando la fonte ha marcato la formazione ufficiale di quel club."""
    sez = dati.get(norm(club))
    if not sez:
        return False
    return any(g.get("ufficiale") for g in sez["giocatori"])


def clean_sheet(dati: dict, club: str):
    sez = dati.get(norm(club))
    return sez["clean_sheet"] if sez else None
