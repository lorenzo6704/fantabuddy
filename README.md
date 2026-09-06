# FantaBuddy — la formazione consigliata su Telegram

Ti scrive due volte a giornata:

- **sei ore prima del primo match**, la formazione completa con la motivazione
  di ogni scelta;
- **se esce la formazione ufficiale della partita di apertura**, un secondo
  messaggio con le sole correzioni. Arriva una volta sola: dopo il primo
  fischio la formazione non e' piu' modificabile.

**A turno iniziato tace.** Da quando comincia la prima partita fino alla fine
dell'ultima non manda niente e non consuma niente: non c'e' piu' nulla che tu
possa cambiare. Riprende quando il calendario passa alla giornata dopo.

---

# Guida passo passo

## 1. Token del bot Telegram

Su Telegram, **@BotFather** → `/revoke` → scegli **FantaBuddy_bot** → copia il
token nuovo.

## 2. Chat id

Apri la chat con il bot e premi **Avvia**. Poi nel browser:

    https://api.telegram.org/botTOKEN/getUpdates

Cerca `"chat":{"id":123456789`. Quel numero e' il chat id.

## 3. Repository

Su github.com: **+** → **New repository**, nome `fantabuddy`, lascialo
**Public** (le password stanno nei Secrets, non nei file, e i repository
pubblici hanno le automazioni gratuite senza limiti).

## 4. Carica i dodici file

**uploading an existing file**, trascinali tutti, **Commit changes**. Sono
tutti allo stesso livello, non ci sono sottocartelle.

## 5. Tre Secrets

**Settings** → **Secrets and variables** → **Actions** → **New repository
secret**, con questi nomi esatti:

| Name | Secret |
|---|---|
| `TELEGRAM_TOKEN` | il token di BotFather |
| `TELEGRAM_CHAT_ID` | il numero del punto 2 |
| `FOOTBALL_DATA_TOKEN` | la chiave di football-data.org |

## 6. Il file dell'automazione

Va creato a mano: i browser non caricano le cartelle che iniziano col punto.

**Add file** → **Create new file**, come nome scrivi
`.github/workflows/fantabuddy.yml` (le barre creano le cartelle da sole),
incolla il contenuto di `fantabuddy.yml`, **Commit changes**.

## 7. Accendi

**Actions** → se serve **enable workflows** → **FantaBuddy** → **Run workflow**.
Il passaggio **diagnosi** ti dice se i pezzi rispondono.

---

# Come decide

    P(gioca) x (voto base + bonus attesi + malus attesi)

- **P(gioca)**: la percentuale che Fantacalcio.it assegna a ogni giocatore
  nelle probabili formazioni. Chi non compare ne' fra i titolari ne' in
  panchina viene trattato come non convocato, non stimato a caso.
- **Bonus attesi**: gol e assist per novanta minuti, dalle stime scritte in
  `rosa.py`, scalate per i minuti attesi e per il fattore campo.
- **Rigori**: gerarchia dal dischetto per rigori attesi del club per tasso di
  realizzazione. E' la parte piu' prevedibile del fantacalcio.
- **Portieri**: gol subiti attesi e probabilita' di porta inviolata.

Poi prova tutti e sette i moduli e tiene quello col totale piu' alto.

# Il rendimento si aggiorna da solo

A turno concluso il bot chiede a football-data.org il dettaglio di ogni
partita, estrae marcatori e assistman, e accumula i numeri in
`rendimento.json`, che il workflow ricommitta nel repository.

Le stime di `rosa.py` restano come punto di partenza, ma pesano sempre meno:
finche' le giornate sono poche domina la stima, dopo una decina di partite
conta quasi solo quello che il giocatore fa in campo. Nel messaggio lo vedi
scritto: *"2 gol e 1 assist in 3 giornate, pesati al 33%, quindi 0,56 gol e
0,17 assist attesi ogni 90'"*.

Quindi `rosa.py` non va piu' ritoccato ogni settimana. Serve solo per i
rigoristi, il regolamento e i trasferimenti.

**Cosa non si puo' avere: il fantavoto e la media voto.** Sono giudizi
redazionali di Gazzetta e Fantacalcio.it, non dati pubblici, e nessuna fonte
gratuita li espone. Il modello usa 6.0 come voto base e prevede i bonus, che
sono la parte che sposta la classifica.

# Manutenzione

- **`rig`** in `rosa.py`: posizione fra i rigoristi del club. Aggiornala
  quando cambia, e' il parametro che pesa di piu'.
- **`gol90` e `ass90`**: solo il punto di partenza. Dopo qualche giornata ci
  pensa `rendimento.json`.
- **Sezione regolamento**: di default il gol vale 3 per tutti i ruoli, come da
  Fantacalcio Classic. Se la tua lega differenzia (3 attaccante /
  3,5 centrocampista / 4 difensore) cambia il dizionario `GOL`.
  **Verificalo prima di fidarti del bot.**

Dopo un trasferimento di gennaio, aggiorna nome e club.

# Perche' non ci sono gli xG

Understat e FBref, le due fonti gratuite di expected goals, rifiutano le
richieste che arrivano dai datacenter, e i server di GitHub sono datacenter.
Abbiamo provato l'accesso diretto e quattro ponti pubblici: tutti bloccati.
Restavano solo servizi a pagamento o un account terzo con quota mensile, e
abbiamo scelto di non aggiungere quella fragilita'.

Quello che il bot ha in mano — chi gioca, con che percentuale, e chi tira i
rigori — sono comunque i due fattori che pesano di piu' sul risultato.

# Limiti da conoscere

- Il bot prevede i bonus, non la prestazione: il voto base e' fisso a 6.0.
- Le ufficiali escono circa un'ora prima e il controllo gira ogni dieci
  minuti: se hai un giocatore nella partita di apertura, tieni comunque
  d'occhio il telefono.
- La lettura delle probabili dipende da come e' impaginato un sito. Se cambia,
  il bot non si blocca: te lo scrive nel messaggio e usa stime prudenziali.
