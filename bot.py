#!/usr/bin/env python3
"""FantaBuddy: manda su Telegram la formazione consigliata.

Due momenti:
  --pre         sei ore prima del primo match della giornata, messaggio completo
  --ufficiali   quando esce una formazione ufficiale, solo le correzioni

Per provarlo a mano:
  --prova       calcola e stampa a schermo, non manda niente
  --ora         calcola e manda subito
"""
from __future__ import annotations
import argparse, datetime as dt, os, sys
import requests

import rosa, modello, formazione, stato
import calendario, probabili, statistiche

ORE_PRIMA = 6
FINESTRA = 0.75          # il cron gira ogni 30 minuti
ANTICIPO_UFFICIALI = 100  # minuti prima del calcio d'inizio in cui guardare
# Dopo il fischio d'inizio della prima partita la formazione e' bloccata:
# l'unica finestra utile per una correzione e' quella che precede quel match.


# ------------------------------------------------------------------- Telegram
def invia(testo: str):
    tok, chat = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    for pezzo in _spezza(testo, 3800):
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          json={"chat_id": chat, "text": pezzo, "parse_mode": "HTML",
                                "disable_web_page_preview": True}, timeout=20)
        r.raise_for_status()


def _spezza(t: str, n: int):
    while len(t) > n:
        taglio = t.rfind("\n\n", 0, n)
        yield t[:taglio if taglio > 0 else n]
        t = t[(taglio if taglio > 0 else n):].lstrip()
    yield t


# ------------------------------------------------------------------- pipeline
def calcola(correzioni: dict | None = None):
    correzioni = correzioni or {}
    turno_info = calendario.prossima_giornata()
    if turno_info is None:
        return None
    g_num, kickoff, turno = turno_info

    stats, club_stats, fonte_stat, guasti = statistiche.scarica()
    if fonte_stat is None:
        guasti = ["nessuna fonte di statistiche raggiungibile (" +
                  "; ".join(g[:60] for g in guasti) + ")"]
    else:
        guasti = []
    try:
        prob_dati = probabili.scarica()
    except Exception as e:
        prob_dati = {}
        guasti.append(f"probabili formazioni non raggiungibili ({type(e).__name__})")

    valutati, avvisi = [], []
    for g in rosa.GIOCATORI:
        ruolo, nome, club, uname, rig = g
        sfida = calendario.avversario(club, turno)
        if sfida is None:
            continue
        avv, casa = sfida

        riga = probabili.cerca(prob_dati, nome, club)
        if nome.lower() in correzioni:
            p, fonte, spread, nota = float(correzioni[nome.lower()]), "tua correzione", 0.0, ""
        elif riga:
            p, fonte, spread, nota = riga["prob"], riga["stato"], riga["spread"], riga["nota"]
        else:
            p, fonte, spread, nota = 0.35, "non trovato", 0.0, ""
            avvisi.append(nome)

        xg_sub = None
        for k, v in club_stats.items():
            if avv.lower()[:5] in k.lower() or k.lower()[:5] in avv.lower():
                xg_sub = v["xg_subiti_pg"]
                break

        val, det = modello.fantavoto_atteso(g, stats, p, xg_sub, casa,
                                            probabili.clean_sheet(prob_dati, club))
        det.update(fonte_prob=fonte, spread=spread, nota=nota,
                   ufficiale=probabili.formazione_ufficiale(prob_dati, club))
        valutati.append({"g": g, "val": val, "det": det, "avv": avv, "casa": casa})

    return {"giornata": g_num, "kickoff": kickoff, "turno": turno,
            "scelta": formazione.scegli(valutati), "avvisi": avvisi,
            "prob_dati": prob_dati, "guasti": guasti}


def undici_nomi(scelta) -> list[str]:
    return sorted([scelta["portiere"]["g"][1]] + [v["g"][1] for v in scelta["undici"]])


# ------------------------------------------------------------------- messaggi
def messaggio_completo(r) -> str:
    ora = r["kickoff"].astimezone().strftime("%d/%m alle %H:%M")
    s = r["scelta"]
    out = [f"<b>Giornata {r['giornata']}</b> — primo match {ora}",
           f"Modulo: <b>{s['modulo']}</b> · {s['totale']:.1f} punti attesi", "",
           "<b>FORMAZIONE</b>"]
    for v in [s["portiere"]] + s["undici"]:
        out += [f"<b>{v['g'][1]}</b> ({v['g'][0]}, {v['g'][2]}) — {v['val']:.2f}",
                f"  {formazione.motivazione(v, True)}"]
    out += ["", "<b>PANCHINA</b> (ordine di subentro)"]
    for v in s["panchina"][:rosa.N_SOSTITUZIONI + 2]:
        out += [f"<b>{v['g'][1]}</b> ({v['g'][0]}, {v['g'][2]}) — {v['val']:.2f}",
                f"  {formazione.motivazione(v, False)}",
                f"  {formazione.perche_fuori(v, s['undici'])}"]
    if r["guasti"]:
        out += ["", "🔧 " + "; ".join(r["guasti"]) +
                ". La formazione qui sopra e' stata calcolata lo stesso, ma con "
                "stime prudenziali: controllala prima di schierarla."]
    if r["avvisi"]:
        out += ["", "⚠️ Non trovati nelle probabili, valutati in modo prudenziale: "
                + ", ".join(r["avvisi"])]
    out += ["", "<i>Percentuali dalla media di Fantacalcio.it, Gazzetta, SOS Fanta e Sky. "
            "Ti riscrivo appena escono le formazioni ufficiali. "
            "Se vedi un errore rispondi qui, per esempio: Kean non gioca.</i>"]
    return "\n".join(out)


def messaggio_correzione(r, prima: list[str], club_nuovi: list[str], scadenza=None) -> str:
    s = r["scelta"]
    dopo = undici_nomi(s)
    entrati = [n for n in dopo if n not in prima]
    usciti = [n for n in prima if n not in dopo]
    ora = scadenza.astimezone().strftime("%H:%M") if scadenza else "il primo fischio"
    testa = ("<b>Formazioni ufficiali</b> — " + ", ".join(club_nuovi) +
             f"\nUltima occasione per correggere: si chiude alle {ora}.")
    if not entrati and not usciti:
        return testa + "\n\nNessun cambio: la formazione che ti ho mandato regge."
    out = [testa, "", f"Modulo: <b>{s['modulo']}</b> · {s['totale']:.1f} punti attesi", ""]
    for n in entrati:
        v = next(v for v in [s["portiere"]] + s["undici"] if v["g"][1] == n)
        out += [f"🟢 <b>DENTRO {n}</b> ({v['g'][0]}, {v['g'][2]})",
                f"  {formazione.motivazione(v, True)}"]
    for n in usciti:
        v = next((v for v in s["panchina"] if v["g"][1] == n), None)
        if v:
            out += [f"🔴 <b>FUORI {n}</b> ({v['g'][0]}, {v['g'][2]})",
                    f"  {formazione.motivazione(v, False)}"]
    out += ["", "<b>Undici aggiornato:</b> " + ", ".join(dopo)]
    return "\n".join(out)


# ------------------------------------------------------------------- comandi
def modo_pre(st, forza=False):
    r = calcola(st["correzioni"])
    if r is None:
        return print("nessuna giornata in programma")
    st = stato.allinea_giornata(st, r["giornata"])
    ore = (r["kickoff"] - dt.datetime.now(dt.timezone.utc)).total_seconds() / 3600
    in_finestra = ORE_PRIMA - FINESTRA <= ore <= ORE_PRIMA + FINESTRA
    if forza or (in_finestra and r["giornata"] not in st["inviate"]):
        invia(messaggio_completo(r))
        st["inviate"] = sorted(set(st["inviate"] + [r["giornata"]]))
        st["ultimo_undici"] = undici_nomi(r["scelta"])
        st["chiuso"] = False
        stato.scrivi(st)
        print(f"inviata giornata {r['giornata']}")
    else:
        print(f"niente da fare: mancano {ore:.1f} ore al primo match")


def primo_match(turno):
    """Il match di apertura della giornata e i club coinvolti (anche se in
    contemporanea con altri)."""
    inizio = min(p["inizio"] for p in turno)
    club = set()
    for p in turno:
        if p["inizio"] == inizio:
            club.update({p["casa"], p["ospite"]})
    return inizio, club


def modo_ufficiali(st):
    r = calcola(st["correzioni"])
    if r is None or r["giornata"] not in st.get("inviate", []):
        return print("nessuna formazione gia' inviata per questa giornata")
    st = stato.allinea_giornata(st, r["giornata"])
    if st.get("chiuso"):
        return print("giornata gia' chiusa: la formazione non e' piu' modificabile")

    adesso = dt.datetime.now(dt.timezone.utc)
    inizio, club_apertura = primo_match(r["turno"])

    if adesso >= inizio:
        st["chiuso"] = True
        stato.scrivi(st)
        return print("primo match iniziato: niente piu' correzioni")

    minuti = (inizio - adesso).total_seconds() / 60
    if minuti > ANTICIPO_UFFICIALI:
        return print(f"troppo presto: mancano {minuti:.0f} minuti al primo match")

    # solo i miei giocatori che scendono in campo nella partita di apertura
    miei = sorted({club for _, _, club, _, _ in rosa.GIOCATORI
                   if any(club.lower() in c.lower() or c.lower() in club.lower()
                          for c in club_apertura)})
    if not miei:
        st["chiuso"] = True
        stato.scrivi(st)
        return print("nessun tuo giocatore nella partita di apertura: niente da correggere")

    pronti = [c for c in miei if probabili.formazione_ufficiale(r["prob_dati"], c)]
    if not pronti:
        return print("formazioni ufficiali non ancora pubblicate per:", ", ".join(miei))

    invia(messaggio_correzione(r, st.get("ultimo_undici", []), pronti,
                               scadenza=inizio))
    st["ultimo_undici"] = undici_nomi(r["scelta"])
    st["chiuso"] = True
    stato.scrivi(st)
    print("correzione inviata per:", ", ".join(pronti))


def diagnosi():
    """Controlla i pezzi uno per uno e stampa cosa funziona e cosa no."""
    esiti = []

    for v in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "FOOTBALL_DATA_TOKEN"):
        esiti.append((v, "presente" if os.environ.get(v) else "MANCANTE", not os.environ.get(v)))

    try:
        tok = os.environ["TELEGRAM_TOKEN"]
        j = requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=15).json()
        ok = j.get("ok")
        esiti.append(("Telegram", f"bot @{j['result']['username']}" if ok
                      else f"RIFIUTATO: {j.get('description')}", not ok))
    except Exception as e:
        esiti.append(("Telegram", f"ERRORE {type(e).__name__}: {e}", True))

    try:
        g, k, turno = calendario.prossima_giornata()
        esiti.append(("Calendario", f"giornata {g}, primo match {k:%d/%m %H:%M} UTC, "
                                    f"{len(turno)} partite", False))
    except Exception as e:
        esiti.append(("Calendario", f"ERRORE {type(e).__name__}: {e}", True))

    gioc, sq, fonte, guasti = statistiche.scarica()
    if fonte:
        agganciati = sum(1 for _, n, _, u, _ in rosa.GIOCATORI
                         if statistiche.trova(gioc, u, n))
        esiti.append(("Statistiche", f"fonte {fonte}: {len(gioc)} giocatori, "
                                     f"{agganciati}/25 tuoi agganciati, "
                                     f"{len(sq)} squadre", agganciati < 15))
    else:
        esiti.append(("Statistiche", "nessuna fonte risponde — " + " | ".join(guasti), True))

    try:
        pr = probabili.scarica()
        pieni = [k for k, v in pr.items() if v["giocatori"]]
        trovati = sum(1 for _, n, c, _, _ in rosa.GIOCATORI if probabili.cerca(pr, n, c))
        esiti.append(("Probabili", f"{len(pieni)} squadre, {trovati}/25 tuoi giocatori "
                                   f"agganciati", trovati < 15))
        if trovati < 25:
            try:
                i = probabili.ispeziona()
                print(f"\n--- com'e' fatta la pagina: {i['byte']} byte, "
                      f"{i['tabelle']} tabelle, {i['percentuali']} percentuali, "
                      f"{i['righe_riconosciute']} righe riconosciute a testo")
                print("    inizio pagina:", i["assaggio"][:200])
            except Exception as e:
                print("    ispezione fallita:", e)
            print("--- cosa ha letto dalla pagina delle probabili ---")
            for riga in probabili.elenco(pr)[:8]:
                print("   ", riga[:150])
            mancanti = [n for _, n, c, _, _ in rosa.GIOCATORI
                        if not probabili.cerca(pr, n, c)]
            print("    non agganciati:", ", ".join(mancanti) or "nessuno")
            print("--- fine ---")
    except Exception as e:
        esiti.append(("Probabili", f"ERRORE {type(e).__name__}: {e}", True))

    print("\n=== DIAGNOSI FANTABUDDY ===")
    for nome, msg, male in esiti:
        print(f"  [{'KO' if male else 'ok'}] {nome}: {msg}")
    rotti = [n for n, _, m in esiti if m]
    print("=== " + ("tutto a posto" if not rotti else "da sistemare: " + ", ".join(rotti)) + " ===\n")
    return 1 if any(m for _, _, m in esiti[:4]) else 0


def main():
    ap = argparse.ArgumentParser()
    for f in ("pre", "ufficiali", "prova", "ora", "diagnosi"):
        ap.add_argument("--" + f, action="store_true")
    a = ap.parse_args()
    if a.diagnosi:
        return diagnosi()
    st = stato.leggi()

    if a.prova:
        r = calcola(st["correzioni"])
        if r is None:
            return print("nessuna giornata in programma")
        t = messaggio_completo(r)
        for tag in ("<b>", "</b>", "<i>", "</i>"):
            t = t.replace(tag, "")
        return print(t)
    if a.ora:
        return modo_pre(st, forza=True)
    if a.ufficiali:
        return modo_ufficiali(st)
    return modo_pre(st)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyError as e:
        print(f"\nMANCA UN SECRET: {e}. Controlla Settings > Secrets and "
              f"variables > Actions, i nomi devono essere esatti.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERRORE: {type(e).__name__}: {e}")
        print("Lancia il passaggio 'diagnosi' per vedere quale pezzo non risponde.")
        sys.exit(1)
