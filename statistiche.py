"""Sceglie da sola la fonte di statistiche che funziona.

Prova i provider in ordine e tiene il primo che risponde con dati veri.
Aggiungerne uno domani vuol dire aggiungere una riga a PROVIDER.
"""
from __future__ import annotations
import re, unicodedata
import understat, fbref, apifootball

# In ordine di preferenza. Understat e FBref sono migliori (xG veri) ma
# bloccano gli indirizzi dei datacenter: restano in lista perche' funzionano
# se un giorno fai girare il bot da casa tua.
PROVIDER = [("Understat", understat), ("FBref", fbref), ("API-Football", apifootball)]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s).upper()


def scarica():
    """Ritorna (statistiche_giocatori, statistiche_squadre, nome_fonte, guasti)."""
    guasti = []
    for nome, mod in PROVIDER:
        try:
            gioc = mod.scarica()
            if len(gioc) < 50:
                raise RuntimeError(f"solo {len(gioc)} giocatori, sembra vuota")
            try:
                sq = mod.squadre()
            except Exception:
                sq = {}
            return gioc, sq, nome, guasti
        except Exception as e:
            guasti.append(f"{nome}: {type(e).__name__} {e}")
    return {}, {}, None, guasti


def trova(stats: dict, nome_completo: str, cognome: str):
    """Aggancia un giocatore per nome completo, altrimenti per cognome."""
    if nome_completo in stats:
        return stats[nome_completo]
    chiave = norm(cognome)
    for k, v in stats.items():
        if norm(k).endswith(chiave) or chiave in norm(k):
            return v
    return None
