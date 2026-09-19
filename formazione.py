"""Sceglie modulo, undici e panchina, e scrive la motivazione di ogni scelta."""
from __future__ import annotations
import math
import rosa, punteggio


CORRELAZIONE_STESSO_CLUB = 0.25


def _varianza_squadra(in_campo: list[dict]) -> float:
    """Somma delle varianze, piu' la correlazione fra compagni di squadra.

    Due giocatori dello stesso club vanno su e giu' insieme: se la loro
    squadra prende tre gol, ne risentono entrambi. Ignorarlo fa sembrare la
    formazione piu' stabile di quanto sia, e con le soglie a gol la stabilita'
    e' proprio la cosa da stimare bene.
    """
    var = sum(v["det"].get("varianza", 1.0) for v in in_campo)
    per_club: dict[str, list[float]] = {}
    for v in in_campo:
        per_club.setdefault(v["g"][2], []).append(
            math.sqrt(max(0.0, v["det"].get("varianza", 1.0))))
    for sd in per_club.values():
        for i in range(len(sd)):
            for j in range(i + 1, len(sd)):
                var += 2 * CORRELAZIONE_STESSO_CLUB * sd[i] * sd[j]
    return var


def scegli(valutati: list[dict]) -> dict:
    per_ruolo = {r: sorted([v for v in valutati if v["g"][0] == r],
                           key=lambda v: -v["val"]) for r in "PDCA"}
    # Puo' capitare che nessuno dei tre portieri giochi (rinvii, soste
    # spezzate). Non e' un motivo per non dare il resto della formazione.
    portiere = per_ruolo["P"][0] if per_ruolo["P"] else None

    migliore = None
    for nome_mod, (nd, nc, na) in rosa.MODULI.items():
        completo = (len(per_ruolo["D"]) >= nd and len(per_ruolo["C"]) >= nc
                    and len(per_ruolo["A"]) >= na)
        undici = per_ruolo["D"][:nd] + per_ruolo["C"][:nc] + per_ruolo["A"][:na]
        # Se un modulo non si riempie (rinvii, turni spezzati) non lo scartiamo:
        # meglio dare la formazione migliore possibile e dire che e' incompleta.
        in_campo = ([portiere] if portiere else []) + undici
        tot = sum(v["val"] for v in in_campo)
        var = _varianza_squadra(in_campo)
        sd = math.sqrt(var)
        # La lega paga a soglie di gol, non a punti: scegliamo il modulo che
        # massimizza i GOL attesi, che tiene conto anche della volatilita'.
        gol = punteggio.gol_attesi(tot, sd)
        voto = (gol, completo, len(undici))
        if migliore is None or voto > migliore["_voto"]:
            migliore = {"modulo": nome_mod, "undici": undici, "portiere": portiere,
                        "totale": tot, "scarto": sd, "gol_attesi": gol,
                        "completo": completo, "_voto": voto,
                        "mancano": max(0, (nd + nc + na) - len(undici))}
    if migliore is None or not migliore["undici"]:
        raise RuntimeError("nessun tuo giocatore scende in campo in questo turno")
    migliore.pop("_voto")

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

    pv, minuti = d.get("p_voto", 0), d.get("minuti", 0)
    if stato == "non convocato":
        pezzi.append("non compare fra titolari e panchina: non convocato")
    elif p >= 0.85:
        pezzi.append(f"titolare al {int(p*100)}%")
    elif p >= rosa.SOGLIA_TITOLARE:
        pezzi.append(f"titolare ({int(p*100)}%)")
    elif p >= 0.35:
        pezzi.append(f"ballottaggio al {int(p*100)}%, ma il voto lo prende "
                     f"nel {int(pv*100)}% dei casi")
    else:
        pezzi.append(f"panchina ({int(p*100)}%), voto probabile al {int(pv*100)}%")
    if 0 < minuti < 0.75:
        pezzi.append(f"circa {int(minuti*90)}' attesi, quindi meno occasioni da bonus")

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
    att, dif = d.get("avv_attacco", 1.0), d.get("avv_difesa", 1.0)
    if ruolo == "P":
        forza = ("che segna molto" if att >= 1.20 else
                 "che segna poco" if att <= 0.80 else "di rendimento medio")
        sub = d.get("subiti_attesi")
        pezzi.append(f"{dove} contro {v['avv']} {forza}" +
                     (f", {sub:.2f} gol attesi da subire" if sub else ""))
    else:
        forza = ("difesa che concede molto" if dif >= 1.20 else
                 "difesa solida" if dif <= 0.80 else "difesa nella media")
        pezzi.append(f"{dove} contro {v['avv']}, {forza}")
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
