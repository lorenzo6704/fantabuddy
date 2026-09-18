"""Statistiche stagionali dei giocatori da Fantacalcio.it.

La pagina delle statistiche pubblica, per ogni calciatore, presenze, media
voto, fantamedia, gol, assist, ammonizioni, espulsioni e rigori: e' tutto
quello che serve, gia' cumulato, in una richiesta sola. Niente archivio da
mantenere e niente limite di chiamate da rispettare.

Se la pagina non e' leggibile (contenuto costruito dal browser), `scarica()`
solleva un errore e il bot continua con le stime scritte in rosa.py.
"""
from __future__ import annotations
import re, unicodedata
import requests
from bs4 import BeautifulSoup

URL = "https://www.fantacalcio.it/statistiche-serie-a"
URL_VOTI = "https://www.fantacalcio.it/voti-fantacalcio-serie-a/2026-27/{g}"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept-Language": "it-IT,it;q=0.9"}

# "Nome Cognome 4 6,25 7,50 2 1 1 0" -> presenze, mv, fm, gf, ass, amm, esp
RIGA = re.compile(
    r"([A-Z\u00c0-\u00dc][A-Za-z\u00c0-\u00ff'\u2019\.\- ]{2,28}?)\s+"
    r"(\d{1,2})\s+(\d{1,2}[,.]\d{1,2})\s+(-?\d{1,2}[,.]\d{1,2})\s+"
    r"(\d{1,2})\s+(\d{1,2})")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s).upper()


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def _testo(url: str, timeout: int = 25) -> str:
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)


def analizza(testo: str) -> dict[str, dict]:
    out = {}
    for m in RIGA.finditer(testo):
        nome = m.group(1).strip()
        if len(nome) < 3 or not re.search(r"[A-Za-z]{3}", nome):
            continue
        presenze = int(m.group(2))
        if presenze == 0 or presenze > 38:
            continue
        out[norm(nome)] = {
            "nome": nome, "presenze": presenze,
            "media_voto": _num(m.group(3)), "fantamedia": _num(m.group(4)),
            "gol": int(m.group(5)), "assist": int(m.group(6)),
        }
    return out


def scarica(timeout: int = 25) -> dict[str, dict]:
    d = analizza(_testo(URL, timeout))
    if len(d) < 80:
        raise RuntimeError(f"statistiche illeggibili: solo {len(d)} righe riconosciute")
    return d


def cerca(dati: dict, cognome: str):
    chiave = norm(cognome)
    for k, v in dati.items():
        if k.endswith(chiave) or chiave in k:
            return v
    return None


def ispeziona(timeout: int = 25) -> str:
    """Per la diagnosi: dice se la pagina e' leggibile e come sono scritte
    davvero le righe."""
    righe = []
    for etichetta, url in (("statistiche", URL), ("voti 4a", URL_VOTI.format(g=4))):
        try:
            t = _testo(url, timeout)
        except Exception as e:
            righe.append(f"  {etichetta}: ERRORE {type(e).__name__}: {str(e)[:60]}")
            continue
        virgole = len(re.findall(r"\d{1,2},\d{1,2}", t))
        d = analizza(t)
        righe.append(f"  {etichetta}: {len(t)//1024} KB · {virgole} numeri con virgola "
                     f"· {len(d)} righe riconosciute")
        for campione in ("Dovbyk", "Davis", "De Bruyne"):
            i = t.lower().find(campione.lower())
            if i > 0:
                righe.append(f"    [{campione}] ...{t[max(0, i-60):i+180]}...")
                break
    return "\n".join(righe)
