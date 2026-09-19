"""Fantavoto atteso.

    P(gioca) x (voto base + bonus attesi + malus attesi)

Le tre componenti vengono, quando disponibili, dalle statistiche ufficiali di
Fantacalcio.it: media voto reale al posto del 6.0 fisso, gol e assist per
partita al posto delle stime scritte in rosa.py.

Finche' le presenze sono poche i valori di rosa.py pesano di piu'; dopo una
decina di partite conta quasi solo quello che il giocatore fa in campo. E' il
modo giusto di trattare un campione piccolo: due gare a secco non fanno di
Dovbyk un giocatore da zero gol.
"""
from __future__ import annotations
import rosa

VOTO_BASE = 6.0
MINUTI_ATTESI = 78.0
RIGORI_A_PARTITA = 0.16
REALIZZAZIONE_RIGORI = 0.78
QUOTA_RIGORISTA = {1: 0.85, 2: 0.12, 3: 0.03, 4: 0.0, 0: 0.0}
GIALLI_90 = {"P": 0.05, "D": 0.18, "C": 0.15, "A": 0.10}
GOL_SUBITI_ATTESI = 1.35
PESO_STIMA = 5.0          # a quante presenze equivale la stima iniziale


def _fondi(iniziale: float, osservato: float, presenze: int) -> float:
    peso = presenze / (presenze + PESO_STIMA)
    return iniziale * (1 - peso) + osservato * peso


def fantavoto_atteso(g, prob_tit: float, casa: bool, stat: dict | None = None):
    """g = (ruolo, nome, club, rig, gol90, ass90). `stat` e' la riga di
    Fantacalcio.it per quel giocatore, se disponibile."""
    ruolo, nome, club, rig, gol90, ass90 = g
    quota_min = MINUTI_ATTESI / 90.0
    campo = 1.08 if casa else 0.93
    voto = VOTO_BASE
    fonte = "stima iniziale"

    if stat and stat["presenze"] > 0:
        n = stat["presenze"]
        voto = _fondi(VOTO_BASE, stat["media_voto"], n)
        gol90 = _fondi(gol90, stat["gol"] / n, n)
        ass90 = _fondi(ass90, stat["assist"] / n, n)
        fonte = (f"{stat['gol']} gol e {stat['assist']} assist in {n} presenze, "
                 f"media voto {stat['media_voto']:.2f}")

    if ruolo == "P":
        subiti = GOL_SUBITI_ATTESI * (0.92 if casa else 1.08)
        if stat and stat["presenze"] > 0:
            subiti = _fondi(subiti, stat["gol_subiti"] / stat["presenze"],
                            stat["presenze"])
        bonus = (rosa.GOL_SUBITO * subiti
                 + rosa.PORTA_INVIOLATA * max(0.0, 0.42 - 0.20 * subiti))
        quota_rig = 0.0
    else:
        quota_rig = QUOTA_RIGORISTA.get(rig, 0.0)
        rig_attesi = RIGORI_A_PARTITA * quota_rig
        gol = gol90 * quota_min * campo + rig_attesi * REALIZZAZIONE_RIGORI
        ass = ass90 * quota_min * campo
        bonus = (gol * rosa.GOL[ruolo] + ass * rosa.ASSIST
                 + rig_attesi * (1 - REALIZZAZIONE_RIGORI) * rosa.RIGORE_SBAGLIATO
                 + GIALLI_90[ruolo] * quota_min * rosa.AMMONIZIONE)

    return prob_tit * (voto + bonus), {
        "prob": prob_tit, "bonus": bonus, "quota_rig": quota_rig,
        "gol90": gol90, "ass90": ass90, "casa": casa, "voto": voto,
        "fonte_rend": fonte,
    }
