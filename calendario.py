"""Calendario di giornata, letto dalla pagina delle probabili di Fantacalcio.it.

La stessa pagina che da' le percentuali di titolarita' contiene anche numero di
giornata, data, ora e squadre di ogni partita. Una fonte sola per tutto: meno
pezzi, meno cose che possono rompersi.

football-data.org resta come rete di sicurezza e si attiva solo se la lettura
di Fantacalcio.it fallisce E il token e' configurato. Quando sarai sicuro che
la fonte principale regge, puoi cancellare il secret FOOTBALL_DATA_TOKEN.

Tutti gli orari sono in fuso di Roma.
"""
from __future__ import annotations
import datetime as dt
import os, re
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

ROMA = ZoneInfo("Europe/Rome")
URL_FC = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept-Language": "it-IT,it;q=0.9"}

MESI = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5,
        "giugno": 6, "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10,
        "novembre": 11, "dicembre": 12}
SQUADRE = ["Atalanta", "Bologna", "Cagliari", "Como", "Fiorentina", "Frosinone",
           "Genoa", "Inter", "Juventus", "Lazio", "Lecce", "Milan", "Monza",
           "Napoli", "Parma", "Roma", "Sassuolo", "Torino", "Udinese", "Venezia"]

DATA = re.compile(r"(?:luned\u00ec|marted\u00ec|mercoled\u00ec|gioved\u00ec|venerd\u00ec|sabato|domenica)"
                  r"\s+(\d{1,2})\s+(" + "|".join(MESI) + r")\s*,?\s*(\d{1,2})[:.](\d{2})",
                  re.I)
TEAM_MODULO = re.compile(r"\b(" + "|".join(SQUADRE) + r")\s+(\d-\d-\d(?:-\d)?)\b")
# Il numero va preso dal titolo della pagina: nelle notizie in cima compaiono
# altre giornate ("la top 3 della 4^ giornata") e la prima occorrenza sbaglia.
GIORNATA = re.compile(r"Probabili\s+Formazioni[^\n]{0,80}?(\d{1,2})\s*[\u00aa\u00b0a^]\s*Giornata",
                      re.I)


def ora_italiana(quando: dt.datetime) -> dt.datetime:
    return quando.astimezone(ROMA)


def _anno(mese: int, oggi: dt.date | None = None) -> int:
    """La stagione va da agosto a maggio: da gennaio in poi siamo nell'anno dopo."""
    oggi = oggi or dt.date.today()
    inizio_stagione = oggi.year if oggi.month >= 7 else oggi.year - 1
    return inizio_stagione if mese >= 7 else inizio_stagione + 1


def testo_probabili(timeout: int = 25) -> str:
    r = requests.get(URL_FC, headers=UA, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)


def analizza(testo: str, oggi: dt.date | None = None):
    """(giornata, [partite]) dalla pagina. Ogni data e' seguita dai due blocchi
    squadra+modulo delle due formazioni."""
    m = GIORNATA.search(testo)
    giornata = int(m.group(1)) if m else None

    tagli = [(x.start(), x.end(), x) for x in DATA.finditer(testo)]
    squadre = [(x.start(), x.group(1)) for x in TEAM_MODULO.finditer(testo)]
    partite = []
    for i, (inizio, fine, mm) in enumerate(tagli):
        limite = tagli[i + 1][0] if i + 1 < len(tagli) else len(testo)
        coinvolte = [nome for pos, nome in squadre if fine <= pos < limite]
        if len(coinvolte) < 2:
            continue
        giorno, mese, ora, minuti = (int(mm.group(1)), MESI[mm.group(2).lower()],
                                     int(mm.group(3)), int(mm.group(4)))
        quando = dt.datetime(_anno(mese, oggi), mese, giorno, ora, minuti, tzinfo=ROMA)
        partite.append({"inizio": quando, "casa": coinvolte[0], "ospite": coinvolte[1],
                        "stato": "TIMED", "giornata": giornata})
    partite.sort(key=lambda p: p["inizio"])
    return giornata, partite


# ------------------------------------------------- rete di sicurezza opzionale
API = "https://api.football-data.org/v4/competitions/SA/matches"


def _da_football_data():
    tok = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not tok:
        raise RuntimeError("nessuna fonte di calendario disponibile")
    oggi = dt.date.today()
    r = requests.get(API, headers={"X-Auth-Token": tok},
                     params={"dateFrom": (oggi - dt.timedelta(days=8)).isoformat(),
                             "dateTo": (oggi + dt.timedelta(days=21)).isoformat()},
                     timeout=20)
    r.raise_for_status()
    fuori = []
    for m in r.json().get("matches", []):
        fuori.append({
            "giornata": m.get("matchday"), "stato": m.get("status"),
            "inizio": dt.datetime.fromisoformat(
                m["utcDate"].replace("Z", "+00:00")).astimezone(ROMA),
            "casa": m["homeTeam"]["shortName"] or m["homeTeam"]["name"],
            "ospite": m["awayTeam"]["shortName"] or m["awayTeam"]["name"]})
    if not fuori:
        raise RuntimeError("football-data non ha restituito partite")
    g = min(p["giornata"] for p in fuori
            if p["giornata"] and p["stato"] in ("SCHEDULED", "TIMED"))
    return g, sorted([p for p in fuori if p["giornata"] == g],
                     key=lambda p: p["inizio"])


CODA_TURNO = dt.timedelta(hours=3)      # quanto dura l'ultima partita del turno


def turno(pagina: str | None = None, adesso: dt.datetime | None = None):
    """Il turno da giocare, letto dalla pagina delle probabili.

    `pagina` e' il testo gia' scaricato: passandolo si evita di scaricare due
    volte la stessa pagina. Ritorna un dizionario con giornata, partite,
    apertura e fine del turno, tutti in ora di Roma, oppure None se non si
    riesce a leggere nulla.
    """
    fonte = "Fantacalcio.it"
    try:
        testo = pagina if pagina is not None else testo_probabili()
        giornata, partite = analizza(testo)
        if not partite:
            raise RuntimeError("nessuna partita riconosciuta nella pagina")
    except Exception:
        try:
            giornata, partite = _da_football_data()
            fonte = "football-data"
        except Exception:
            return None
    if not partite:
        return None
    partite.sort(key=lambda p: p["inizio"])
    for p in partite:
        p.setdefault("fonte", fonte)
    return {"giornata": giornata, "partite": partite, "fonte": fonte,
            "apertura": partite[0]["inizio"],
            "fine": partite[-1]["inizio"] + CODA_TURNO}


def prossima_giornata(adesso: dt.datetime | None = None):
    """Vecchia forma, tenuta per compatibilita': (giornata, apertura, partite)."""
    t = turno(adesso=adesso)
    return None if t is None else (t["giornata"], t["apertura"], t["partite"])


def avversario(club: str, turno: list[dict]) -> tuple[str, bool] | None:
    for p in turno:
        if club.lower() in p["casa"].lower():
            return p["ospite"], True
        if club.lower() in p["ospite"].lower():
            return p["casa"], False
    return None


def radiografia(t: dict | None = None) -> str:
    t = t or turno()
    if t is None:
        return "pagina illeggibile: nessuna partita trovata"
    righe = [f"giornata {t['giornata']} da {t['fonte']}, {len(t['partite'])} partite, "
             f"apertura {ora_italiana(t['apertura']):%a %d/%m %H:%M}"]
    for p in t["partite"][:4]:
        righe.append(f"    {ora_italiana(p['inizio']):%a %d/%m %H:%M} "
                     f"{p['casa']}-{p['ospite']}")
    return "\n".join(righe)
