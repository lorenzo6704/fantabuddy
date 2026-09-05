"""Sceglie modulo, undici e panchina, e scrive la motivazione di ogni scelta."""
from __future__ import annotations
from itertools import combinations
import rosa


def scegli(valutati: list[dict]) -> dict:
    """valutati = [{'g':tupla, 'val':float, 'det':dict, 'avv':str, 'casa':bool}, ...]
    Prova tutti i moduli ammessi e tiene quello con il punteggio atteso piu' alto."""
    per_ruolo = {r: sorted([v for v in valutati if v["g"][0] == r],
                           key=lambda v: -v["val"]) for r in "PDCA"}
    if not per_ruolo["P"]:
        raise RuntimeError("nessun portiere in rosa")

    portiere = per_ruolo["P"][0]
    migliore = None
    for nome_mod, (nd, nc, na) in rosa.MODULI.items():
        if len(per_ruolo["D"]) < nd or len(per_ruolo["C"]) < nc or len(per_ruolo["A"]) < na:
            continue
        undici = (per_ruolo["D"][:nd] + per_ruolo["C"][:nc] + per_ruolo["A"][:na])
        tot = portiere["val"] + sum(v["val"] for v in undici)
        if migliore is None or tot > migliore["totale"]:
            migliore = {"modulo": nome_mod, "undici": undici,
                        "portiere": portiere, "totale": tot}

    titolari_id = {id(v) for v in migliore["undici"]} | {id(portiere)}
    panchina = sorted([v for v in valutati if id(v) not in titolari_id],
                      key=lambda v: -v["val"])
    migliore["panchina"] = panchina
    return migliore


# ------------------------------------------------------------------ motivazioni
def motivazione(v: dict, titolare: bool) -> str:
    g, d = v["g"], v["det"]
    ruolo, nome, club = g[0], g[1], g[2]
    pezzi = []

    p = d["prob"]
    if p >= 0.85:
        pezzi.append("titolare nelle probabili")
    elif p >= 0.6:
        pezzi.append(f"titolare probabile ({int(p*100)}%)")
    elif p >= 0.35:
        pezzi.append(f"in ballottaggio ({int(p*100)}%)")
    else:
        pezzi.append(f"difficilmente in campo ({int(p*100)}%)")
    if d.get("fonte_prob") == "minuti":
        pezzi[-1] += ", stima dai minuti giocati"
    elif d.get("fonte_prob") == "manuale":
        pezzi[-1] += " (impostato da te)"

    if ruolo != "P":
        if d["quota_rig"] >= 0.5:
            pezzi.append("primo rigorista")
        elif d["quota_rig"] > 0:
            pezzi.append("nelle gerarchie dal dischetto")
        if d["stat"]:
            pezzi.append(f"{d['xg']:.2f} xG e {d['xa']:.2f} xA attesi")
        else:
            pezzi.append("nessuna statistica disponibile, stima prudenziale")

    fa = d["fattore_avversario"]
    dove = "in casa" if v["casa"] else "in trasferta"
    if fa >= 1.12:
        pezzi.append(f"{dove} contro {v['avv']}, che concede molto")
    elif fa <= 0.88:
        pezzi.append(f"{dove} contro {v['avv']}, difesa solida")
    else:
        pezzi.append(f"{dove} contro {v['avv']}")

    testo = "; ".join(pezzi)
    return testo[0].upper() + testo[1:] + "."


def perche_fuori(v: dict, undici: list[dict]) -> str:
    """Spiega la panchina per confronto diretto con chi gioca nel suo ruolo."""
    ruolo = v["g"][0]
    pari = [u for u in undici if u["g"][0] == ruolo]
    if not pari:
        return "Il modulo scelto non prevede altri giocatori del suo ruolo."
    ultimo = min(pari, key=lambda u: u["val"])
    delta = ultimo["val"] - v["val"]
    return (f"Fuori per {delta:.2f} punti attesi rispetto a {ultimo['g'][1]}, "
            f"l'ultimo del suo reparto a entrare.")
