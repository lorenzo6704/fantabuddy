"""Modello di fantavoto atteso.

fantavoto_atteso = P(gioca) * (voto_base + bonus_attesi + malus_attesi)

I bonus vengono da xG e xA per 90 minuti, scalati per i minuti attesi e
corretti per la forza difensiva dell'avversario. I rigori sono trattati a
parte perche' sono la componente piu' prevedibile: dipendono dalla gerarchia
del club e dai rigori che quel club guadagna, non dalla forma del giocatore.

Chi non gioca vale 0 in questo modello, non 6: in una lega con sostituzioni
ordinate il non-voto viene rimpiazzato dalla panchina, quindi il valore di un
titolare incerto e' gia' scontato dalla probabilita'.
"""
from __future__ import annotations
import rosa, statistiche

VOTO_BASE = {"P": 6.0, "D": 6.0, "C": 6.0, "A": 6.0}
MINUTI_ATTESI = 78.0            # minuti medi di un titolare
RIGORI_LEGA_PER_SQUADRA_A_PARTITA = 0.16   # ~6 rigori a stagione per club
TASSO_REALIZZAZIONE_RIGORI = 0.78
QUOTA_RIGORISTA = {1: 0.85, 2: 0.12, 3: 0.03, 4: 0.0, 0: 0.0}
XG_MEDIO_SUBITO = 1.35          # riferimento di lega, per normalizzare


def _fattore_avversario(xg_subiti_avv: float | None) -> float:
    """1.0 = avversario medio. Sopra 1 = difesa che concede."""
    if not xg_subiti_avv:
        return 1.0
    return max(0.72, min(1.35, xg_subiti_avv / XG_MEDIO_SUBITO))


def fantavoto_atteso(g, stats, prob_tit, xg_subiti_avv, in_casa, p_clean_sheet=None):
    """g = tupla (ruolo, nome, club, understat, rig). Ritorna (valore, dettagli)."""
    ruolo, nome, club, uname, rig = g
    s = statistiche.trova(stats, uname, nome)
    d = {"stat": bool(s), "fonte_stat": "understat" if s else "assente"}

    quota_min = MINUTI_ATTESI / 90.0
    fatt = _fattore_avversario(xg_subiti_avv) * (1.06 if in_casa else 0.95)

    if s:
        xg = s["xg90"] * quota_min * fatt
        xa = s["xa90"] * quota_min * fatt
        gialli90 = (s["gialli"] / s["minuti"] * 90) if s["minuti"] else 0.12
    else:
        xg, xa, gialli90 = (0.10 if ruolo == "A" else 0.04), 0.05, 0.12

    # rigori: gerarchia del club x rigori attesi x tasso di realizzazione
    quota_rig = QUOTA_RIGORISTA.get(rig, 0.0)
    rig_attesi = RIGORI_LEGA_PER_SQUADRA_A_PARTITA * quota_rig
    gol_da_rigore = rig_attesi * TASSO_REALIZZAZIONE_RIGORI
    err_rigore = rig_attesi * (1 - TASSO_REALIZZAZIONE_RIGORI)

    bonus = ((xg + gol_da_rigore) * rosa.GOL[ruolo]
             + xa * rosa.ASSIST
             + err_rigore * rosa.RIGORE_SBAGLIATO
             + gialli90 * quota_min * rosa.AMMONIZIONE)

    if ruolo == "P":
        # per i portieri la quota di porta inviolata del mercato batte qualunque stima
        pi = p_clean_sheet if p_clean_sheet is not None else max(0.0, 0.42 - 0.22 * (xg_subiti_avv or XG_MEDIO_SUBITO))
        gol_att = (1 - pi) * 1.6
        bonus = rosa.GOL_SUBITO * gol_att + rosa.PORTA_INVIOLATA * pi

    valore = prob_tit * (VOTO_BASE[ruolo] + bonus)
    d.update(xg=xg, xa=xa, bonus=bonus, quota_rig=quota_rig,
             fattore_avversario=fatt, prob=prob_tit)
    return valore, d
