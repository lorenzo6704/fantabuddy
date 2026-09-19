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
import math
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
                     stato: str = "", mia: dict | None = None,
                     avv: dict | None = None):
    """Ritorna (media, dettagli). In dettagli c'e' anche `varianza`.

    `mia` e `avv` sono attacco e difesa dei due club (1.0 = media di lega).
    Contano molto: per un portiere l'avversario e' il fattore principale, e per
    un attaccante una difesa che concede vale piu' di qualunque forma.
    """
    ruolo, nome, club, rig, gol90, ass90 = g
    p_voto, quota_min = probabilita_voto(prob_tit, stato)
    mia = mia or {"attacco": 1.0, "difesa": 1.0}
    avv = avv or {"attacco": 1.0, "difesa": 1.0}
    # una difesa avversaria che concede il 20% in piu' della media vale un 20%
    # di occasioni in piu'; il fattore campo si somma a questo
    campo = (1.08 if casa else 0.93) * max(0.65, min(1.45, avv["difesa"]))
    voto = VOTO_BASE
    fonte = "stima iniziale"

    gialli_suoi = None
    if stat and stat["presenze"] >= 3:
        gialli_suoi = _fondi(GIALLI_90[ruolo], stat["ammonizioni"] / stat["presenze"],
                             stat["presenze"])
    if stat and stat["presenze"] > 0:
        n = stat["presenze"]
        voto = _fondi(VOTO_BASE, stat["media_voto"], n)
        gol90 = _fondi(gol90, stat["gol"] / n, n)
        ass90 = _fondi(ass90, stat["assist"] / n, n)
        fonte = (f"{stat['gol']} gol e {stat['assist']} assist in {n} presenze, "
                 f"media voto {stat['media_voto']:.2f}")

    if ruolo == "P":
        # gol attesi = quanto subisce la mia squadra x quanto segna l'avversaria
        subiti = (GOL_SUBITI_ATTESI * mia["difesa"] * avv["attacco"]
                  * (0.92 if casa else 1.08))
        subiti = max(0.35, min(3.2, subiti))
        if stat and stat["presenze"] > 0:
            # il dato personale conta, ma non sostituisce chi hai di fronte
            subiti = _fondi(subiti, stat["gol_subiti"] / stat["presenze"],
                            min(stat["presenze"], 4))
        # Probabilita' di porta inviolata: P(zero gol) con distribuzione di
        # Poisson, che e' la forma giusta per un conteggio di eventi rari.
        pi = math.exp(-subiti)
        bonus = rosa.GOL_SUBITO * subiti + rosa.PORTA_INVIOLATA * pi
        var_bonus = subiti * 1.0 + pi * (1 - pi) * rosa.PORTA_INVIOLATA ** 2
        quota_rig = 0.0
    else:
        quota_rig = QUOTA_RIGORISTA.get(rig, 0.0)
        # I rigori gia' calciati valgono piu' di quello che ho scritto in
        # rosa.py: se uno ne ha tirati due, il rigorista e' lui, punto.
        if stat:
            calciati = stat["rigori_segnati"] + stat["rigori_sbagliati"]
            if calciati >= 2:
                quota_rig = max(quota_rig, 0.85)
            elif calciati == 1:
                quota_rig = max(quota_rig, 0.50)
        rig_attesi = RIGORI_A_PARTITA * quota_rig
        lam_gol = gol90 * quota_min * campo + rig_attesi * REALIZZAZIONE_RIGORI
        lam_ass = ass90 * quota_min * campo
        # se il giocatore ha uno storico, usiamo il suo: ci sono difensori da
        # mezzo cartellino a partita e centrocampisti che non ne prendono mai
        base_giallo = gialli_suoi if gialli_suoi is not None else GIALLI_90[ruolo]
        p_giallo = min(0.9, base_giallo * quota_min)
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
        "avv_attacco": avv["attacco"], "avv_difesa": avv["difesa"], "club": club,
        "subiti_attesi": subiti if ruolo == "P" else None,
    }
