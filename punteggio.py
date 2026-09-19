"""Dal punteggio di squadra ai gol, secondo le soglie della lega.

Il fantacalcio non premia i punti: premia i gol, e i gol arrivano a scalini
(66 punti il primo, poi 71, 76, 80, 84, 88, e uno ogni quattro punti dopo).
Questo cambia il modo giusto di scegliere la formazione.

Massimizzare i punti attesi e' solo un'approssimazione. Se la squadra vale 64
punti di media, sei sotto la prima soglia e ti conviene rischiare: un undici
piu' volatile ha piu' probabilita' di superare quota 66. Se ne vale 90, la
volatilita' ti fa solo perdere gol. Qui calcoliamo direttamente i GOL attesi,
che tengono conto di entrambe le cose.

Il totale di squadra viene trattato come una normale: e' un'approssimazione
ragionevole, perche' e' la somma di undici contributi quasi indipendenti.
"""
from __future__ import annotations
import math
import rosa

MAX_GOL = 14


def soglie(fino_a: int = MAX_GOL) -> list[int]:
    s = list(rosa.SOGLIE)
    while len(s) < fino_a:
        s.append(s[-1] + rosa.PASSO_OLTRE)
    return s[:fino_a]


def _p_almeno(media: float, scarto: float, soglia: float) -> float:
    """P(totale >= soglia) con approssimazione normale."""
    if scarto <= 0.01:
        return 1.0 if media >= soglia else 0.0
    z = (soglia - media) / scarto
    return 0.5 * math.erfc(z / math.sqrt(2))


def gol_attesi(media: float, scarto: float) -> float:
    return sum(_p_almeno(media, scarto, s) for s in soglie())


def dettaglio(media: float, scarto: float) -> str:
    """Riga leggibile: gol attesi e quanto manca alla soglia successiva."""
    g = gol_attesi(media, scarto)
    prossima = next((s for s in soglie() if s > media), None)
    testo = f"{media:.1f} punti attesi (\u00b1{scarto:.1f}) \u2192 {g:.2f} gol attesi"
    if prossima:
        p = _p_almeno(media, scarto, prossima)
        testo += (f"; soglia successiva a {prossima} punti, "
                  f"probabilita' {p*100:.0f}%")
    return testo
