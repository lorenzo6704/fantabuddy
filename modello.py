"""Fantavoto atteso.

    P(gioca) x (voto base + bonus attesi + malus attesi)

I bonus vengono dalle stime di gol e assist per novanta minuti scritte in
rosa.py, scalate per i minuti attesi. I rigori sono trattati a parte perche'
sono la componente piu' prevedibile: dipendono dalla gerarchia del club, non
dalla forma del giocatore.

Chi non gioca vale zero, non sei: con le sostituzioni ordinate il non-voto
viene rimpiazzato dalla panchina, quindi l'incertezza sulla titolarita' e' gia'
scontata dalla probabilita'.
"""
from __future__ import annotations
import rosa, rendimento

VOTO_BASE = 6.0
MINUTI_ATTESI = 78.0
RIGORI_A_PARTITA = 0.16          # ~6 rigori a stagione per club
REALIZZAZIONE_RIGORI = 0.78
QUOTA_RIGORISTA = {1: 0.85, 2: 0.12, 3: 0.03, 4: 0.0, 0: 0.0}
GIALLI_90 = {"P": 0.05, "D": 0.18, "C": 0.15, "A": 0.10}
GOL_SUBITI_ATTESI = 1.35         # media di lega, usata per i portieri


def fantavoto_atteso(g, prob_tit: float, casa: bool):
    """g = (ruolo, nome, club, rig, gol90, ass90). Ritorna (valore, dettagli)."""
    ruolo, nome, club, rig, gol90_iniz, ass90_iniz = g
    gol90, ass90, fonte_rend = rendimento.stime(nome, gol90_iniz, ass90_iniz)
    quota_min = MINUTI_ATTESI / 90.0
    campo = 1.08 if casa else 0.93

    if ruolo == "P":
        subiti = GOL_SUBITI_ATTESI * (0.92 if casa else 1.08)
        bonus = rosa.GOL_SUBITO * subiti + rosa.PORTA_INVIOLATA * max(0.0, 0.42 - 0.20 * subiti)
        quota_rig = 0.0
    else:
        quota_rig = QUOTA_RIGORISTA.get(rig, 0.0)
        rig_attesi = RIGORI_A_PARTITA * quota_rig
        gol = gol90 * quota_min * campo + rig_attesi * REALIZZAZIONE_RIGORI
        ass = ass90 * quota_min * campo
        bonus = (gol * rosa.GOL[ruolo] + ass * rosa.ASSIST
                 + rig_attesi * (1 - REALIZZAZIONE_RIGORI) * rosa.RIGORE_SBAGLIATO
                 + GIALLI_90[ruolo] * quota_min * rosa.AMMONIZIONE)

    valore = prob_tit * (VOTO_BASE + bonus)
    return valore, {"prob": prob_tit, "bonus": bonus, "quota_rig": quota_rig,
                    "gol90": gol90, "ass90": ass90, "casa": casa,
                    "fonte_rend": fonte_rend}
