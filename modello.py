"""Fantavoto atteso, con due distinzioni che contano.

**Voto e bonus non seguono la stessa regola.** Bastano quindici minuti per
prendere il voto pieno, quindi chi subentra a mezz'ora dalla fine porta a casa
il 6 intero. I bonus no: chi gioca venti minuti ha un quarto delle occasioni
di chi ne gioca novanta. Percio' il voto viene moltiplicato per la probabilita'
di scendere in campo, i bonus per i minuti attesi.

**La percentuale delle probabili misura la titolarita', non il voto.** Un
giocatore dato al 55% in ballottaggio quasi sempre il voto lo prende lo stesso:
o parte titolare, o entra nella ripresa. Sopra il 60% lo consideriamo in campo
quasi certamente.

Restituisce media e varianza: la varianza serve perche' la lega paga a soglie
di gol, e li' la volatilita' e' un fattore, non un dettaglio.
"""
from __future__ import annotations
import rosa

VOTO_BASE = 6.0
SD_VOTO = 0.55                    # quanto oscilla il voto di un giocatore
RIGORI_A_PARTITA = 0.16
REALIZZAZIONE_RIGORI = 0.78
QUOTA_RIGORISTA = {1: 0.85, 2: 0.12, 3: 0.03, 4: 0.0, 0: 0.0}
GIALLI_90 = {"P": 0.05, "D": 0.18, "C": 0.15, "A": 0.10}
GOL_SUBITI_ATTESI = 1.35
PESO_STIMA = 5.0


def probabilita_voto(p: float, stato: str = "") -> tuple[float, float]:
    """Da percentuale di titolarita' a (probabilita' di prendere voto, quota
    di minuti attesi). Le due cose sono diverse: vedi il commento in testa."""
    if stato == "non convocato" or p <= 0.02:
        return 0.0, 0.0
    if p >= rosa.SOGLIA_TITOLARE:            # titolare annunciato
        return 0.97, 0.80 + 0.15 * min(1.0, (p - 0.60) / 0.35)
    if p >= 0.35:                            # ballottaggio: uno dei due gioca,
        quota = (p - 0.35) / 0.25            # e chi perde spesso subentra
        return 0.78 + 0.19 * quota, 0.38 + 0.42 * quota
    if p >= 0.10:                            # panchina, subentro frequente
        return 0.45, 0.20
    return 0.15, 0.06


def _fondi(iniziale: float, osservato: float, presenze: int) -> float:
    peso = presenze / (presenze + PESO_STIMA)
    return iniziale * (1 - peso) + osservato * peso


def fantavoto_atteso(g, prob_tit: float, casa: bool, stat: dict | None = None,
                     stato: str = ""):
    """Ritorna (media, dettagli). In dettagli c'e' anche `varianza`."""
    ruolo, nome, club, rig, gol90, ass90 = g
    p_voto, quota_min = probabilita_voto(prob_tit, stato)
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
            subiti = _fondi(subiti, stat["gol_subiti"] / stat["presenze"], stat["presenze"])
        pi = max(0.0, 0.42 - 0.20 * subiti)
        bonus = rosa.GOL_SUBITO * subiti + rosa.PORTA_INVIOLATA * pi
        var_bonus = subiti * 1.0 + pi * (1 - pi) * rosa.PORTA_INVIOLATA ** 2
        quota_rig = 0.0
    else:
        quota_rig = QUOTA_RIGORISTA.get(rig, 0.0)
        rig_attesi = RIGORI_A_PARTITA * quota_rig
        lam_gol = gol90 * quota_min * campo + rig_attesi * REALIZZAZIONE_RIGORI
        lam_ass = ass90 * quota_min * campo
        p_giallo = GIALLI_90[ruolo] * quota_min
        bonus = (lam_gol * rosa.GOL[ruolo] + lam_ass * rosa.ASSIST
                 + rig_attesi * (1 - REALIZZAZIONE_RIGORI) * rosa.RIGORE_SBAGLIATO
                 + p_giallo * rosa.AMMONIZIONE)
        # gol e assist come conteggi rari: varianza pari alla media, scalata
        var_bonus = (lam_gol * rosa.GOL[ruolo] ** 2 + lam_ass * rosa.ASSIST ** 2
                     + p_giallo * (1 - p_giallo) * rosa.AMMONIZIONE ** 2)

    media = p_voto * (voto + bonus)
    # se non prende voto entra la panchina: la varianza di quel ramo e' minore,
    # quindi la teniamo conservativa sommando solo il ramo "gioca"
    varianza = p_voto * (SD_VOTO ** 2 + var_bonus) + p_voto * (1 - p_voto) * (voto + bonus) ** 2

    return media, {
        "prob": prob_tit, "p_voto": p_voto, "minuti": quota_min, "bonus": bonus,
        "quota_rig": quota_rig, "gol90": gol90, "ass90": ass90, "casa": casa,
        "voto": voto, "fonte_rend": fonte, "varianza": varianza, "stato": stato,
    }
