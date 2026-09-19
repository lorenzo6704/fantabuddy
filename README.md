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

## 4. Carica i dieci file

**uploading an existing file**, trascinali tutti, **Commit changes**. Sono
tutti allo stesso livello, non ci sono sottocartelle.

## 5. Tre Secrets

**Settings** → **Secrets and variables** → **Actions** → **New repository
secret**, con questi nomi esatti:

| Name | Secret |
|---|---|
| `TELEGRAM_TOKEN` | il token di BotFather |
| `TELEGRAM_CHAT_ID` | il numero del punto 2 |

Sono due, non serve altro: il bot non usa nessuna API esterna con chiave.

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

Calendario, probabili e statistiche vengono tutti da Fantacalcio.it: una fonte
sola, e gli orari sono in fuso di Roma.

- **P(gioca)**: la percentuale che Fantacalcio.it assegna a ogni giocatore
  nelle probabili formazioni. Chi non compare ne' fra i titolari ne' in
  panchina viene trattato come non convocato, non stimato a caso.
- **Il calendario** viene dalla stessa pagina: contiene il numero di giornata,
  la data e l'ora di ogni partita e le squadre accoppiate. Gli orari italiani
  vengono convertiti in UTC. Nessuna API esterna, nessun token.
- **Bonus attesi**: gol e assist per novanta minuti, dalle stime scritte in
  `rosa.py`, scalate per i minuti attesi e per il fattore campo.
- **Rigori**: gerarchia dal dischetto per rigori attesi del club per tasso di
  realizzazione. E' la parte piu' prevedibile del fantacalcio.
- **Portieri**: gol subiti attesi e probabilita' di porta inviolata.

Poi prova tutti e sette i moduli e tiene quello col totale piu' alto.

# Le statistiche si aggiornano da sole

A ogni giro il bot legge la pagina delle statistiche di Fantacalcio.it, che
pubblica per ogni calciatore presenze, media voto, fantamedia, gol, assist,
rigori e cartellini. Da li' ricava tre cose che prima doveva stimare:

- la **media voto reale** al posto del 6.0 fisso;
- i **gol per partita**, al posto di `gol90` in rosa.py;
- gli **assist per partita**, al posto di `ass90`.

Finche' le presenze sono poche i valori di `rosa.py` pesano di piu'; dopo una
decina di partite conta quasi solo il campo. Nel messaggio lo vedi scritto:
*"1 gol e 2 assist in 3 presenze, media voto 6,50"*.

Quindi `rosa.py` non va ritoccato ogni settimana. Serve per i rigoristi, il
regolamento e i trasferimenti di gennaio.

# Manutenzione

- **`rig`** in `rosa.py`: posizione fra i rigoristi del club. Aggiornala quando
  cambia, e' il parametro che pesa di piu' e nessuna fonte lo espone.
- **`gol90` e `ass90`**: solo il punto di partenza, per i giocatori che non
  hanno ancora presenze.
- **Sezione regolamento**: di default il gol vale 3 per tutti i ruoli, come da
  Fantacalcio Classic. Se la tua lega differenzia (3 attaccante /
  3,5 centrocampista / 4 difensore) cambia il dizionario `GOL`.
  **Verificalo prima di fidarti del bot.**

# Limiti da conoscere

- Il bot prevede i bonus, non la prestazione: il voto base e' fisso a 6.0.
- Le ufficiali escono circa un'ora prima e il controllo gira ogni dieci
  minuti: se hai un giocatore nella partita di apertura, tieni comunque
  d'occhio il telefono.
- La lettura delle probabili dipende da come e' impaginato un sito. Se cambia,
  il bot non si blocca: te lo scrive nel messaggio e usa stime prudenziali.
