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


def scarica(timeout: int = 25) -> dict:
    """{CLUB: {'giocatori': [...], 'clean_sheet': float|None}}"""
    r = requests.get(URL, headers=UA, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    squadre: dict[str, dict] = {}
    club = None
    stato_corrente = "titolare"

    for nodo in soup.find_all(["h2", "h3", "table", "ul", "p", "em", "i"]):
        testo = nodo.get_text(" ", strip=True)

        if nodo.name == "h2" and 2 < len(testo) < 30:
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
    return squadre


def cerca(dati: dict, cognome: str, club: str):
    """Trova un giocatore dentro la sezione del suo club. None se assente."""
    sez = dati.get(norm(club))
    if not sez:
        return None
    chiave = norm(cognome)
    cand = [g for g in sez["giocatori"] if g["nome"].startswith(chiave)]
    if not cand:
        cand = [g for g in sez["giocatori"] if chiave in g["nome"]]
    if not cand:
        return None
    ordine = {"indisponibile": 0, "titolare": 1, "panchina": 2}
    return sorted(cand, key=lambda g: ordine.get(g["stato"], 3))[0]


def formazione_ufficiale(dati: dict, club: str) -> bool:
    """True quando la fonte ha marcato la formazione ufficiale di quel club."""
    sez = dati.get(norm(club))
    if not sez:
        return False
    return any(g.get("ufficiale") for g in sez["giocatori"])


def clean_sheet(dati: dict, club: str):
    sez = dati.get(norm(club))
    return sez["clean_sheet"] if sez else None
