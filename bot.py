#!/usr/bin/env python3
"""FantaBuddy: la formazione consigliata su Telegram.

Due messaggi per giornata:
  --pre         sei ore prima del primo match, formazione completa
  --ufficiali   quando esce la formazione ufficiale della partita di apertura,
                solo le correzioni

A turno iniziato tace: la formazione non e' piu' modificabile, quindi non c'e'
niente di utile da dire fino alla giornata successiva.

Per provarlo:  --prova (stampa)   --ora (manda subito)   --diagnosi
"""
from __future__ import annotations
import argparse, datetime as dt, os, sys
import requests

import rosa, modello, formazione, stato, calendario, probabili, rendimento

ORE_PRIMA = 6
FINESTRA = 0.75
ANTICIPO_UFFICIALI = 100     # minuti prima del via in cui cercare le ufficiali
CODA_TURNO = dt.timedelta(hours=3)   # quanto dura l'ultima partita


def invia(testo: str):
    tok, chat = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    for pezzo in _spezza(testo, 3800):
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          json={"chat_id": chat, "text": pezzo, "parse_mode": "HTML",
                                "disable_web_page_preview": True}, timeout=20)
        r.raise_for_status()


def _spezza(t: str, n: int):
    while len(t) > n:
        i = t.rfind("\n\n", 0, n)
        i = i if i > 0 else n
        yield t[:i]
        t = t[i:].lstrip()
    yield t


# ------------------------------------------------------------------- calcolo
def calcola(correzioni: dict | None = None):
    correzioni = correzioni or {}
    info = calendario.prossima_giornata()
    if info is None:
        return None
    g_num, _, turno = info
    apertura = min(p["inizio"] for p in turno)
    fine = max(p["inizio"] for p in turno) + CODA_TURNO

    guasti = []
    try:
        prob_dati = probabili.scarica()
    except Exception as e:
        prob_dati = {}
        guasti.append(f"probabili formazioni non raggiungibili ({type(e).__name__})")

    valutati, avvisi = [], []
    for g in rosa.GIOCATORI:
        ruolo, nome, club = g[0], g[1], g[2]
        sfida = calendario.avversario(club, turno)
        if sfida is None:
            continue
        avv, casa = sfida

        riga = probabili.cerca(prob_dati, nome, club)
        if nome.lower() in correzioni:
            p, st, nota = float(correzioni[nome.lower()]), "tua correzione", ""
        elif riga:
            p, st, nota = riga["prob"], riga["stato"], riga["nota"]
        else:
            p, st, nota = 0.5, "sconosciuto", ""
            avvisi.append(nome)

        val, det = modello.fantavoto_atteso(g, p, casa)
        det.update(stato=st, nota=nota)
        valutati.append({"g": g, "val": val, "det": det, "avv": avv, "casa": casa})

    return {"giornata": g_num, "apertura": apertura, "fine": fine, "turno": turno,
            "scelta": formazione.scegli(valutati), "avvisi": avvisi,
            "prob_dati": prob_dati, "guasti": guasti}


def undici_nomi(s) -> list[str]:
    return sorted([s["portiere"]["g"][1]] + [v["g"][1] for v in s["undici"]])


# ------------------------------------------------------------------ messaggi
def messaggio_completo(r) -> str:
    s = r["scelta"]
    out = [f"<b>Giornata {r['giornata']}</b> — primo match "
           f"{r['apertura'].astimezone():%d/%m alle %H:%M}",
           f"Modulo: <b>{s['modulo']}</b> · {s['totale']:.1f} punti attesi", "",
           "<b>FORMAZIONE</b>"]
    for v in [s["portiere"]] + s["undici"]:
        out += [f"<b>{v['g'][1]}</b> ({v['g'][0]}, {v['g'][2]}) — {v['val']:.2f}",
                f"  {formazione.motivazione(v)}"]
    out += ["", "<b>PANCHINA</b> (ordine di subentro)"]
    for v in s["panchina"][:rosa.N_SOSTITUZIONI + 2]:
        out += [f"<b>{v['g'][1]}</b> ({v['g'][0]}, {v['g'][2]}) — {v['val']:.2f}",
                f"  {formazione.motivazione(v)}",
                f"  {formazione.perche_fuori(v, s['undici'])}"]
    if r["guasti"]:
        out += ["", "🔧 " + "; ".join(r["guasti"]) + ". Calcolata lo stesso, "
                "ma con stime prudenziali: controllala."]
    if r["avvisi"]:
        out += ["", "⚠️ Non trovati nelle probabili: " + ", ".join(r["avvisi"])]
    out += ["", "<i>Percentuali da Fantacalcio.it. Ti riscrivo se esce la "
            "formazione ufficiale della partita di apertura.</i>"]
    return "\n".join(out)


def messaggio_correzione(r, prima: list[str], club: list[str]) -> str:
    s = r["scelta"]
    dopo = undici_nomi(s)
    entrati = [n for n in dopo if n not in prima]
    usciti = [n for n in prima if n not in dopo]
    testa = ("<b>Formazioni ufficiali</b> — " + ", ".join(club) +
             f"\nSi chiude alle {r['apertura'].astimezone():%H:%M}.")
    if not entrati and not usciti:
        return testa + "\n\nNessun cambio: la formazione che ti ho mandato regge."
    out = [testa, "", f"Modulo: <b>{s['modulo']}</b> · {s['totale']:.1f} punti attesi", ""]
    for n in entrati:
        v = next(v for v in [s["portiere"]] + s["undici"] if v["g"][1] == n)
        out += [f"🟢 <b>DENTRO {n}</b> ({v['g'][0]}, {v['g'][2]})",
                f"  {formazione.motivazione(v)}"]
    for n in usciti:
        v = next((v for v in s["panchina"] if v["g"][1] == n), None)
        if v:
            out += [f"🔴 <b>FUORI {n}</b> ({v['g'][0]}, {v['g'][2]})",
                    f"  {formazione.motivazione(v)}"]
    out += ["", "<b>Undici aggiornato:</b> " + ", ".join(dopo)]
    return "\n".join(out)


# -------------------------------------------------------------------- azioni
def turno_in_corso(r, adesso) -> bool:
    return r["apertura"] <= adesso <= r["fine"]


def modo_pre(st, forza=False):
    r = calcola(st["correzioni"])
    if r is None:
        return print("nessuna giornata in programma")
    st = stato.allinea_giornata(st, r["giornata"])
    adesso = dt.datetime.now(dt.timezone.utc)

    if turno_in_corso(r, adesso) and not forza:
        return print(f"giornata {r['giornata']} in corso: la formazione e' bloccata, "
                     f"riprendo dopo {r['fine']:%d/%m %H:%M} UTC")

    ore = (r["apertura"] - adesso).total_seconds() / 3600
    if forza or (ORE_PRIMA - FINESTRA <= ore <= ORE_PRIMA + FINESTRA
                 and r["giornata"] not in st["inviate"]):
        invia(messaggio_completo(r))
        st["inviate"] = sorted(set(st["inviate"] + [r["giornata"]]))
        st["ultimo_undici"] = undici_nomi(r["scelta"])
        st["chiuso"] = False
        stato.scrivi(st)
        print(f"inviata giornata {r['giornata']}")
    else:
        print(f"niente da fare: mancano {ore:.1f} ore al primo match")


def modo_ufficiali(st):
    r = calcola(st["correzioni"])
    if r is None or r["giornata"] not in st.get("inviate", []):
        return print("formazione non ancora inviata per questa giornata")
    st = stato.allinea_giornata(st, r["giornata"])
    if st.get("chiuso"):
        return print("giornata gia' chiusa")

    adesso = dt.datetime.now(dt.timezone.utc)
    if adesso >= r["apertura"]:
        st["chiuso"] = True
        stato.scrivi(st)
        return print("primo match iniziato: niente piu' correzioni")

    minuti = (r["apertura"] - adesso).total_seconds() / 60
    if minuti > ANTICIPO_UFFICIALI:
        return print(f"troppo presto: {minuti:.0f} minuti al primo match")

    club_apertura = {c for p in r["turno"] if p["inizio"] == r["apertura"]
                     for c in (p["casa"], p["ospite"])}
    miei = sorted({g[2] for g in rosa.GIOCATORI
                   if any(g[2].lower() in c.lower() or c.lower() in g[2].lower()
                          for c in club_apertura)})
    if not miei:
        st["chiuso"] = True
        stato.scrivi(st)
        return print("nessun tuo giocatore nella partita di apertura")

    pronti = [c for c in miei if probabili.formazione_ufficiale(r["prob_dati"], c)]
    if not pronti:
        return print("ufficiali non ancora uscite per: " + ", ".join(miei))
    invia(messaggio_correzione(r, st.get("ultimo_undici", []), pronti))
    st["ultimo_undici"] = undici_nomi(r["scelta"])
    st["chiuso"] = True
    stato.scrivi(st)
    print("correzione inviata per: " + ", ".join(pronti))


def modo_rendimento():
    """A turno concluso raccoglie gol e assist e li mette da parte."""
    esito = calendario.giornata_conclusa()
    if esito is None:
        return print("nessuna giornata conclusa da registrare")
    g, partite = esito
    d = rendimento.leggi()
    if g in d["giornate"]:
        return print(f"giornata {g} gia' registrata")
    d = rendimento.registra(g, partite)
    miei = {n: v for n, v in d["giocatori"].items() if v.get("gol") or v.get("assist")}
    print(f"registrata giornata {g}. Bonus in archivio: " +
          (", ".join(f"{n} {v['gol']}g {v['assist']}a" for n, v in sorted(miei.items()))
           or "nessuno"))


def diagnosi():
    esiti = []
    for v in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "FOOTBALL_DATA_TOKEN"):
        ok = bool(os.environ.get(v))
        esiti.append((v, "presente" if ok else "MANCANTE", not ok))
    try:
        tok = os.environ["TELEGRAM_TOKEN"]
        j = requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=15).json()
        esiti.append(("Telegram", f"bot @{j['result']['username']}" if j.get("ok")
                      else f"RIFIUTATO: {j.get('description')}", not j.get("ok")))
    except Exception as e:
        esiti.append(("Telegram", f"ERRORE {type(e).__name__}: {e}", True))
    try:
        g, _, turno = calendario.prossima_giornata()
        ap = min(p["inizio"] for p in turno)
        esiti.append(("Calendario", f"giornata {g}, apertura {ap:%d/%m %H:%M} UTC, "
                                    f"{len(turno)} partite", False))
    except Exception as e:
        esiti.append(("Calendario", f"ERRORE {type(e).__name__}: {e}", True))
    try:
        pr = probabili.scarica()
        n = sum(1 for g in rosa.GIOCATORI
                if (probabili.cerca(pr, g[1], g[2]) or {}).get("stato") not in
                (None, "non convocato"))
        squadre = sum(1 for s in pr.values() if s["giocatori"])
        esiti.append(("Probabili", f"{squadre} squadre, {n}/25 tuoi giocatori "
                                   f"nelle liste", n < 12))
    except Exception as e:
        esiti.append(("Probabili", f"ERRORE {type(e).__name__}: {e}", True))

    print("\n=== DIAGNOSI FANTABUDDY ===")
    for nome, msg, male in esiti:
        print(f"  [{'KO' if male else 'ok'}] {nome}: {msg}")
    rotti = [n for n, _, m in esiti if m]
    print("=== " + ("tutto a posto" if not rotti else "da sistemare: " +
                    ", ".join(rotti)) + " ===\n")
    return 0


def main():
    ap = argparse.ArgumentParser()
    for f in ("pre", "ufficiali", "prova", "ora", "diagnosi", "rendimento"):
        ap.add_argument("--" + f, action="store_true")
    a = ap.parse_args()
    if a.diagnosi:
        return diagnosi()
    if a.rendimento:
        return modo_rendimento()
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
        print(f"\nMANCA UN SECRET: {e}. Controlla Settings > Secrets and variables "
              f"> Actions: i nomi devono essere esatti.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERRORE: {type(e).__name__}: {e}")
        print("Lancia il passaggio diagnosi per vedere quale pezzo non risponde.")
        sys.exit(1)
