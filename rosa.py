"""Rosa LOLLOC4 2026/27, regolamento e stime di rendimento.

`gol90` e `ass90` sono i gol e gli assist attesi ogni novanta minuti. Servono
solo come punto di partenza: appena il giocatore accumula presenze, il bot li
sostituisce con i numeri veri presi dalle statistiche di Fantacalcio.it.

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
# Valori della TUA lega, presi dal pannello punteggi.
GOL = {"P": 3.0, "D": 3.0, "C": 3.0, "A": 3.0}   # il gol vale 3 per tutti i ruoli
RIGORE_SEGNATO = 3.0
RIGORE_SBAGLIATO = -3.0
RIGORE_PARATO = 3.0
ASSIST = 1.0
AUTOGOL = -2.0
AMMONIZIONE = -0.5
ESPULSIONE = -1.0
PORTA_INVIOLATA = 1.0
GOL_SUBITO = -1.0
GOL_VITTORIA = 0.0
GOL_PAREGGIO = 0.0
PLAYER_OF_THE_MATCH = 0.0

# Soglie gol: con almeno N punti di squadra si segnano M gol.
SOGLIE = [66, 71, 76, 80, 84, 88]
PASSO_OLTRE = 4          # poi un gol ogni 4 punti

# Con 15 minuti giocati il voto si prende comunque: la probabilita' delle
# probabili formazioni misura la titolarita', non il voto. La conversione sta
# in modello.probabilita_voto().
SOGLIA_TITOLARE = 0.60

MODULI = {
    "3-4-3": (3, 4, 3), "3-5-2": (3, 5, 2), "4-3-3": (4, 3, 3),
    "4-4-2": (4, 4, 2), "4-5-1": (4, 5, 1), "5-3-2": (5, 3, 2),
    "5-4-1": (5, 4, 1),
}
N_SOSTITUZIONI = 5
