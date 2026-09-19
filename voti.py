"""Statistiche stagionali ufficiali da Fantacalcio.it.

Una richiesta sola, aggiornata dopo ogni giornata. Il formato di riga e':

    Dovbyk BOL 3 5,83 6,67 1 0 0 / 0 0 0 1 0
    nome  sq  pg  mv   fm  gf gs rp / r+ r- as am es

Da qui il bot ricava tre cose che prima doveva stimare a mano: la media voto
reale del giocatore, i gol e gli assist per partita. Niente archivio da
mantenere, niente limite di chiamate.
"""
from __future__ import annotations
import re, unicodedata
import requests
from bs4 import BeautifulSoup

URL = "https://www.fantacalcio.it/statistiche-serie-a"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept-Language": "it-IT,it;q=0.9"}

SIGLE = {"ATA": "Atalanta", "BOL": "Bologna", "CAG": "Cagliari", "COM": "Como",
         "FIO": "Fiorentina", "FRO": "Frosinone", "GEN": "Genoa", "INT": "Inter",
         "JUV": "Juventus", "LAZ": "Lazio", "LEC": "Lecce", "MIL": "Milan",
         "MON": "Monza", "NAP": "Napoli", "PAR": "Parma", "ROM": "Roma",
         "SAS": "Sassuolo", "TOR": "Torino", "UDI": "Udinese", "VEN": "Venezia"}

RIGA = re.compile(
    r"([A-Z\u00c0-\u00dc][A-Za-z\u00c0-\u00ff'\u2019\.\-]*(?:\s[A-Z][a-z\.]*)?)\s+"
    r"(" + "|".join(SIGLE) + r")\s+"
    r"(\d{1,2})\s+(-?\d{1,2},\d{1,2})\s+(-?\d{1,2},\d{1,2})\s+"
    r"(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s*/\s*"
    r"(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s).upper()


def _n(s: str) -> float:
    return float(s.replace(",", "."))


def analizza(testo: str) -> dict[str, dict]:
    out = {}
    for m in RIGA.finditer(testo):
        pg = int(m.group(3))
        if not 1 <= pg <= 38:
            continue
        nome = m.group(1).strip()
        out[norm(nome) + "|" + m.group(2)] = {
            "nome": nome, "club": SIGLE[m.group(2)], "presenze": pg,
            "media_voto": _n(m.group(4)), "fantamedia": _n(m.group(5)),
            "gol": int(m.group(6)), "gol_subiti": int(m.group(7)),
            "rigori_parati": int(m.group(8)), "rigori_segnati": int(m.group(9)),
            "rigori_sbagliati": int(m.group(10)), "assist": int(m.group(11)),
            "ammonizioni": int(m.group(12)), "espulsioni": int(m.group(13)),
        }
    return out


def scarica(timeout: int = 25) -> dict[str, dict]:
    r = requests.get(URL, headers=UA, timeout=timeout)
    r.raise_for_status()
    testo = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
    d = analizza(testo)
    if len(d) < 80:
        raise RuntimeError(f"statistiche illeggibili: solo {len(d)} righe riconosciute")
    return d


def cerca(dati: dict, cognome: str, club: str):
    """Prima dentro il club giusto, poi ovunque: evita di confondere omonimi."""
    chiave = norm(cognome)
    esatti = [v for k, v in dati.items()
              if v["club"].lower() == club.lower() and
              (norm(v["nome"]) == chiave or norm(v["nome"]).startswith(chiave))]
    if esatti:
        return max(esatti, key=lambda v: v["presenze"])
    larghi = [v for k, v in dati.items()
              if chiave in norm(v["nome"]) or norm(v["nome"]) in chiave]
    return max(larghi, key=lambda v: v["presenze"]) if larghi else None
