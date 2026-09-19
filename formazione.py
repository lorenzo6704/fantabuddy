"""Sceglie modulo, undici e panchina, e scrive la motivazione di ogni scelta."""
from __future__ import annotations
import rosa


def scegli(valutati: list[dict]) -> dict:
    per_ruolo = {r: sorted([v for v in valutati if v["g"][0] == r],
                           key=lambda v: -v["val"]) for r in "PDCA"}
    # Puo' capitare che nessuno dei tre portieri giochi (rinvii, soste
    # spezzate). Non e' un motivo per non dare il resto della formazione.
    portiere = per_ruolo["P"][0] if per_ruolo["P"] else None

    migliore = None
    for nome_mod, (nd, nc, na) in rosa.MODULI.items():
        if len(per_ruolo["D"]) < nd or len(per_ruolo["C"]) < nc or len(per_ruolo["A"]) < na:
            continue
        undici = per_ruolo["D"][:nd] + per_ruolo["C"][:nc] + per_ruolo["A"][:na]
        tot = (portiere["val"] if portiere else 0) + sum(v["val"] for v in undici)
        if migliore is None or tot > migliore["totale"]:
            migliore = {"modulo": nome_mod, "undici": undici,
                        "portiere": portiere, "totale": tot}
    if migliore is None:
        raise RuntimeError("troppi pochi giocatori per completare un modulo")

    dentro = {id(v) for v in migliore["undici"]}
    if portiere:
        dentro.add(id(portiere))
    migliore["panchina"] = sorted([v for v in valutati if id(v) not in dentro],
                                  key=lambda v: -v["val"])
    return migliore


def motivazione(v: dict) -> str:
    g, d = v["g"], v["det"]
    ruolo, nome, club, rig = g[0], g[1], g[2], g[3]
    p, stato = d["prob"], d.get("stato", "")
    pezzi = []

    if stato == "non convocato":
        pezzi.append("non compare fra titolari e panchina: non convocato")
    elif p >= 0.85:
        pezzi.append(f"titolare al {int(p*100)}% nelle probabili")
    elif p >= 0.6:
        pezzi.append(f"probabile titolare ({int(p*100)}%)")
    elif p >= 0.35:
        pezzi.append(f"in ballottaggio ({int(p*100)}%)")
    else:
        pezzi.append(f"dato in panchina ({int(p*100)}%)")

    if ruolo != "P":
        if rig == 1:
            pezzi.append("primo rigorista del club")
        elif rig in (2, 3):
            pezzi.append(f"{'secondo' if rig == 2 else 'terzo'} dal dischetto")
        fonte = d.get("fonte_rend", "stima iniziale")
        if fonte == "stima iniziale":
            pezzi.append(f"nessuna presenza ancora, stima di partenza "
                         f"{d['gol90']:.2f} gol e {d['ass90']:.2f} assist")
        else:
            pezzi.append(fonte)
    dove = "in casa" if d["casa"] else "in trasferta"
    pezzi.append(f"{dove} contro {v['avv']}")
    t = "; ".join(pezzi)
    return t[0].upper() + t[1:] + "."


def perche_fuori(v: dict, undici: list[dict]) -> str:
    ruolo = v["g"][0]
    pari = [u for u in undici if u["g"][0] == ruolo]
    if not pari:
        return "Il modulo scelto non schiera nessuno del suo ruolo."
    ultimo = min(pari, key=lambda u: u["val"])
    return (f"Fuori per {ultimo['val'] - v['val']:.2f} punti attesi rispetto a "
            f"{ultimo['g'][1]}, l'ultimo del reparto a entrare.")
