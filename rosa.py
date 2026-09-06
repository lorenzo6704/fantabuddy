"""Rosa LOLLOC4 2026/27, regolamento e stime di rendimento.

Senza una fonte di xG raggiungibile, il rendimento offensivo di ogni giocatore
sta qui: `gol90` e `ass90` sono i gol e gli assist attesi ogni novanta minuti.
Sono stime iniziali, da correggere quando la stagione dice qualcosa di diverso:
bastano dieci secondi e valgono piu' di qualunque automatismo.

`rig` = posizione nella gerarchia dei rigoristi del club (1 = primo tiratore,
0 = non tira). E' il parametro che sposta di piu' il risultato: tienilo
aggiornato.
"""

#          ruolo, nome,          club,         rig, gol90, ass90
GIOCATORI = [
    ("P", "De Gea",        "Fiorentina", 0, 0.00, 0.00),
    ("P", "Palmisani",     "Frosinone",  0, 0.00, 0.00),
    ("P", "Christensen",   "Fiorentina", 0, 0.00, 0.00),

    ("D", "Mancini",       "Roma",       0, 0.06, 0.03),
    ("D", "Rrahmani",      "Napoli",     0, 0.05, 0.02),
    ("D", "Bartesaghi",    "Milan",      0, 0.02, 0.10),
    ("D", "Theate",        "Bologna",    0, 0.05, 0.04),
    ("D", "Dragusin",      "Fiorentina", 0, 0.03, 0.02),
    ("D", "Ghilardi",      "Roma",       0, 0.03, 0.02),
    ("D", "Correia",       "Venezia",    0, 0.02, 0.06),
    ("D", "Estupinan",     "Milan",      0, 0.03, 0.10),

    ("C", "De Bruyne",     "Napoli",     1, 0.18, 0.35),
    ("C", "Pulisic",       "Milan",      0, 0.35, 0.20),
    ("C", "Zaniolo",       "Udinese",    0, 0.18, 0.10),
    ("C", "Goncalves",     "Fiorentina", 0, 0.20, 0.15),
    ("C", "Piotrowski",    "Udinese",    0, 0.10, 0.06),
    ("C", "Baldanzi",      "Genoa",      0, 0.12, 0.12),
    ("C", "Pessina",       "Monza",      1, 0.10, 0.08),
    ("C", "Bakola",        "Sassuolo",   0, 0.06, 0.06),

    ("A", "Kean",          "Como",       0, 0.45, 0.08),
    ("A", "Davis",         "Udinese",    1, 0.35, 0.10),
    ("A", "Dovbyk",        "Bologna",    1, 0.45, 0.06),
    ("A", "Colombo",       "Genoa",      1, 0.30, 0.08),
    ("A", "Esposito Se.",  "Sassuolo",   0, 0.28, 0.12),
    ("A", "Toure",         "Parma",      1, 0.30, 0.08),
]

# ---------------------------------------------------------------- regolamento
# VERIFICA questi valori sul regolamento della TUA lega. Il Fantacalcio Classic
# ufficiale da' +3 al gol per qualunque ruolo; molte leghe casalinghe invece
# differenziano (3 attaccante / 3,5 centrocampista / 4 difensore) e la scelta
# cambia le formazioni.
GOL = {"P": 3.0, "D": 3.0, "C": 3.0, "A": 3.0}
ASSIST = 1.0
AMMONIZIONE = -0.5
RIGORE_SBAGLIATO = -3.0
PORTA_INVIOLATA = 1.0
GOL_SUBITO = -1.0

MODULI = {
    "3-4-3": (3, 4, 3), "3-5-2": (3, 5, 2), "4-3-3": (4, 3, 3),
    "4-4-2": (4, 4, 2), "4-5-1": (4, 5, 1), "5-3-2": (5, 3, 2),
    "5-4-1": (5, 4, 1),
}
N_SOSTITUZIONI = 5
