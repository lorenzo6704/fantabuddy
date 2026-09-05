"""Rosa LOLLOC4 2026/27 e parametri della lega.

`understat` e' il nome con cui il giocatore compare su understat.com: serve per
agganciare le statistiche. Se un nome non viene trovato il bot lo segnala nel
messaggio invece di ignorarlo in silenzio.

`rig` = posizione nella gerarchia dei rigoristi del club (1 = primo tiratore,
0 = non tira). Aggiornalo quando cambia: e' il parametro che pesa di piu'.
"""

GIOCATORI = [
    # ruolo, nome, club, understat, rig
    ("P", "De Gea",            "Fiorentina", "David de Gea",        0),
    ("P", "Palmisani",         "Frosinone",  "Michele Palmisani",   0),
    ("P", "Christensen",       "Fiorentina", "Oliver Christensen",  0),

    ("D", "Mancini",           "Roma",       "Gianluca Mancini",    0),
    ("D", "Rrahmani",          "Napoli",     "Amir Rrahmani",       0),
    ("D", "Bartesaghi",        "Milan",      "Davide Bartesaghi",   0),
    ("D", "Theate",            "Bologna",    "Arthur Theate",       0),
    ("D", "Dragusin",          "Fiorentina", "Radu Dragusin",       0),
    ("D", "Ghilardi",          "Roma",       "Daniele Ghilardi",    0),
    ("D", "Correia",           "Venezia",    "Tiago Correia",       0),
    ("D", "Estupinan",         "Milan",      "Pervis Estupinan",    0),

    ("C", "De Bruyne",         "Napoli",     "Kevin De Bruyne",     1),
    ("C", "Pulisic",           "Milan",      "Christian Pulisic",   0),
    ("C", "Zaniolo",           "Udinese",    "Nicolo Zaniolo",      0),
    ("C", "Goncalves",         "Fiorentina", "Pedro Goncalves",     0),
    ("C", "Piotrowski",        "Udinese",    "Jakub Piotrowski",    0),
    ("C", "Baldanzi",          "Genoa",      "Tommaso Baldanzi",    0),
    ("C", "Pessina",           "Monza",      "Matteo Pessina",      1),
    ("C", "Bakola",            "Sassuolo",   "Luis Bakola",         0),

    ("A", "Kean",              "Como",       "Moise Kean",          4),
    ("A", "Davis",             "Udinese",    "Keinan Davis",        1),
    ("A", "Dovbyk",            "Bologna",    "Artem Dovbyk",        1),
    ("A", "Colombo",           "Genoa",      "Lorenzo Colombo",     1),
    ("A", "Esposito Se.",      "Sassuolo",   "Sebastiano Esposito", 0),
    ("A", "Toure",             "Parma",      "El Bilal Toure",      1),
]

# ---------------------------------------------------------------- regolamento
# ATTENZIONE: verifica questi valori sul regolamento della TUA lega prima di
# fidarti del bot. Il regolamento ufficiale Fantacalcio Classic assegna +3 al
# gol indipendentemente dal ruolo; molte leghe casalinghe invece differenziano
# (3 attaccante / 3.5 centrocampista / 4 difensore). Cambiano le scelte.
GOL = {"P": 3.0, "D": 3.0, "C": 3.0, "A": 3.0}
ASSIST = 1.0
AMMONIZIONE = -0.5
ESPULSIONE = -1.0
RIGORE_SBAGLIATO = -3.0
PORTA_INVIOLATA = 1.0
GOL_SUBITO = -1.0

MODULI = {
    "3-4-3": (3, 4, 3), "3-5-2": (3, 5, 2), "4-3-3": (4, 3, 3),
    "4-4-2": (4, 4, 2), "4-5-1": (4, 5, 1), "5-3-2": (5, 3, 2),
    "5-4-1": (5, 4, 1),
}
PANCHINA_ORDINATA = True  # la lega usa le 5 sostituzioni in ordine di panchina
N_SOSTITUZIONI = 5
