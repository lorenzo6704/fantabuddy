# FantaBuddy — la formazione su Telegram

Ti scrive due volte a giornata:

- **sei ore prima del primo match**, la formazione completa con la motivazione
  di ogni scelta;
- **quando escono le formazioni ufficiali della partita di apertura**, un
  secondo messaggio con le sole correzioni: chi entra, chi esce e perché. Se
  non cambia niente te lo dice comunque, così sai che il controllo c'è stato.

  Quel messaggio arriva una volta sola. Dopo il fischio d'inizio della prima
  partita la formazione non è più modificabile, quindi le ufficiali delle
  partite successive non servono a niente e il bot smette di scriverti. Se
  nessuno dei tuoi giocatori scende in campo nel match di apertura, il secondo
  messaggio non parte proprio.

---

# Guida passo passo

Non serve saper programmare. Sono venti minuti in tutto, una volta sola.

## 1. Rifai il token del bot Telegram

Il token che avevi mandato in chat va considerato bruciato.

1. Apri Telegram, cerca **@BotFather**.
2. Scrivi `/revoke`.
3. Scegli **FantaBuddy_bot** dall'elenco.
4. BotFather ti risponde con un token nuovo, tipo
   `8578414663:AAF...`. Copialo e incollalo da qualche parte per i prossimi
   minuti (note del telefono va benissimo).

## 2. Trova il tuo chat id

1. Apri la chat con **@FantaBuddy_bot** e premi **Avvia**, oppure scrivigli
   "ciao". Deve comparire un messaggio *tuo* nella chat.
2. Nel browser apri questo indirizzo, sostituendo `TOKEN` con quello nuovo:

       https://api.telegram.org/botTOKEN/getUpdates

3. Se vedi `{"ok":true,"result":[]}` vuol dire che non hai ancora scritto al
   bot: torna al punto 1 e ricarica la pagina.
4. Quando funziona vedi un blocco lungo con dentro
   `"chat":{"id":123456789,...`. Quel numero è il tuo **chat id**. Copialo.

## 3. Prendi la chiave del calendario

Ce l'hai già: è il token che ti ha mandato Daniel di football-data.org.
Serve solo a sapere quando si gioca.

## 4. Crea il repository su GitHub

1. Vai su **github.com** e fai login (se non hai un account, registrati: è
   gratis).
2. In alto a destra, **+** → **New repository**.
3. Nome: `fantabuddy`. Lascialo **Public**.
   > Perché pubblico: le password non stanno mai nei file, stanno nei Secrets
   > del punto 6, che nessuno può leggere. E i repository pubblici hanno le
   > automazioni gratuite senza limite di minuti, quelli privati no. L'unica
   > cosa che diventa visibile è la tua rosa.
4. **Create repository**.

## 5. Carica i file

1. Nella pagina del repository appena creato, clicca
   **uploading an existing file**.
2. Trascina dentro **tutti** i file e le cartelle che ti ho dato, mantenendo la
   struttura: `bot.py`, `modello.py`, `formazione.py`, `rosa.py`, `stato.py`,
   `stato.json`, `requirements.txt`, `README.md`, la cartella `sources` e la
   cartella `.github`.
3. In fondo alla pagina, **Commit changes**.

> Se la cartella `.github` non si carica trascinandola (succede: il browser a
> volte nasconde le cartelle che iniziano con il punto), usa **Add file** →
> **Create new file**, scrivi come nome
> `.github/workflows/fantabuddy.yml` e incolla dentro il contenuto di quel
> file.

## 6. Metti le tre password nei Secrets

1. Nel repository, in alto: **Settings**.
2. Colonna di sinistra: **Secrets and variables** → **Actions**.
3. Bottone verde **New repository secret**. Ne crei tre, uno alla volta:

   | Name | Secret |
   |---|---|
   | `TELEGRAM_TOKEN` | il token nuovo di BotFather |
   | `TELEGRAM_CHAT_ID` | il numero trovato al punto 2 |
   | `FOOTBALL_DATA_TOKEN` | la chiave di football-data.org |

   Attenzione a scrivere i nomi **esattamente così**, maiuscole comprese.
4. Una volta salvati non sono più leggibili da nessuno, nemmeno da te.

## 7. Accendi le automazioni e prova

1. Scheda **Actions** in alto. Se compare un avviso, clicca
   **I understand my workflows, go ahead and enable them**.
2. A sinistra scegli **FantaBuddy**, poi a destra **Run workflow** →
   **Run workflow**.
3. Aspetta un minuto e ricarica. Se il pallino è verde, controlla Telegram.

Da questo momento gira da solo ogni mezz'ora e decide lui quando scriverti.

## Se qualcosa non va

Clicca sull'esecuzione fallita e leggi l'ultima riga rossa.

| Cosa c'è scritto | Cosa vuol dire |
|---|---|
| `KeyError: 'TELEGRAM_TOKEN'` | manca un secret, o il nome è scritto male |
| `401 Unauthorized` | il token Telegram è sbagliato o revocato |
| `403 Forbidden` (football-data) | chiave del calendario sbagliata |
| `chat not found` | chat id sbagliato, rifai il punto 2 |
| `variabile playersData non trovata` | Understat ha cambiato pagina |

---

# Come decide

Per ogni tuo giocatore calcola un **fantavoto atteso**:

    probabilità di giocare × (voto base + bonus attesi + malus attesi)

- **Probabilità di giocare**: media pesata di Fantacalcio.it, Gazzetta, SOS
  Fanta e Sky, presa dall'aggregato di fantacalcio-online.com. Il bot legge
  anche quanto le quattro redazioni sono in disaccordo fra loro, e te lo dice:
  un 70% su cui sono tutte d'accordo non è un 70% su cui litigano.
  Gli infortunati vengono riconosciuti e messi a zero.
- **Bonus attesi**: xG e xA per novanta minuti da Understat, aggiornati dopo
  ogni giornata, scalati per i minuti attesi e corretti per gli xG che concede
  l'avversario e per il fattore campo.
- **Rigori**: gerarchia dal dischetto × rigori attesi del club × tasso di
  realizzazione. È la componente più prevedibile del fantacalcio.
- **Portieri**: usa la quota di porta inviolata del mercato scommesse, che è
  una previsione migliore di qualunque media storica.

Poi prova tutti e sette i moduli e tiene quello col totale più alto.

# Manutenzione

- **`rosa.py`**, campo `rig`: la posizione nella gerarchia dei rigoristi.
  Aggiornala quando cambia, è il parametro che sposta di più.
- **`rosa.py`**, sezione regolamento: di default il gol vale 3 per tutti i
  ruoli, come da Fantacalcio Classic. Se la tua lega differenzia
  (3 attaccante / 3,5 centrocampista / 4 difensore) cambia il dizionario `GOL`.
  **Verificalo prima di fidarti del bot.**
- Dopo un trasferimento di gennaio, aggiorna nome e club in `rosa.py`.

# Limiti da conoscere

- Il bot prevede i bonus, non la prestazione: il voto base è fisso a 6.0.
- Le formazioni ufficiali escono circa un'ora prima della partita e il
  controllo gira ogni trenta minuti, quindi il secondo messaggio può arrivare
  con un ritardo di mezz'ora — e su GitHub gratuito i cron slittano di qualche
  minuto in più nei momenti di traffico. Su una finestra di sessanta minuti è
  poco margine: se hai un giocatore nella partita di apertura, tieni comunque
  d'occhio il telefono nell'ora prima del via.
- La lettura delle probabili dipende da come è impaginato un sito. Se cambia,
  il bot non si blocca: ripiega su stime prudenziali e te lo scrive nel
  messaggio.
