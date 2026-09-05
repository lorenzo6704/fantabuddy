# FantaBuddy — la formazione su Telegram

Ti scrive due volte a giornata:

- **sei ore prima del primo match**, la formazione completa con la motivazione
  di ogni scelta;
- **quando escono le formazioni ufficiali della partita di apertura**, un
  secondo messaggio con le sole correzioni: chi entra, chi esce e perche'.
  Arriva una volta sola, perche' dopo il primo fischio la formazione non e' piu'
  modificabile. Se non cambia niente te lo dice comunque.

---

# Guida passo passo

Non serve saper programmare. Venti minuti, una volta sola.

## 1. Rifai il token del bot Telegram

Il token che avevi mandato via chat va considerato bruciato.

1. Su Telegram cerca **@BotFather**.
2. Scrivi `/revoke` e scegli **FantaBuddy_bot**.
3. Copia il token nuovo che ti risponde.

## 2. Trova il tuo chat id

1. Apri la chat con **@FantaBuddy_bot** e premi **Avvia** (o scrivi "ciao").
2. Nel browser apri, mettendo il token nuovo al posto di `TOKEN`:

       https://api.telegram.org/botTOKEN/getUpdates

3. Se esce `{"ok":true,"result":[]}` non hai ancora scritto al bot: torna al
   punto 1 e ricarica.
4. Cerca `"chat":{"id":123456789`. Quel numero e' il tuo chat id.

## 3. Crea il repository

1. Su **github.com**: **+** in alto a destra → **New repository**.
2. Nome `fantabuddy`, lascialo **Public**.
   Le password non stanno nei file, stanno nei Secrets del punto 5, che nessuno
   puo' leggere. E i repository pubblici hanno le automazioni gratuite senza
   limiti. L'unica cosa visibile e' la tua rosa.
3. **Create repository**.

## 4. Carica gli undici file

Nella pagina del repository: **uploading an existing file**, trascina dentro
tutti e undici i file (sono tutti allo stesso livello, non ci sono cartelle),
poi **Commit changes**.

## 5. Metti le tre password nei Secrets

**Settings** → **Secrets and variables** → **Actions** → **New repository
secret**. Ne crei tre, con questi nomi esatti:

| Name | Secret |
|---|---|
| `TELEGRAM_TOKEN` | il token nuovo di BotFather |
| `TELEGRAM_CHAT_ID` | il numero del punto 2 |
| `FOOTBALL_DATA_TOKEN` | la chiave di football-data.org |

## 6. Crea il file dell'automazione

Questo va creato a mano, perche' i browser non caricano le cartelle che
iniziano con un punto.

1. Scheda **Code** → **Add file** → **Create new file**.
2. Come nome scrivi, barre comprese:

       .github/workflows/fantabuddy.yml

   Mentre digiti le barre, GitHub crea da solo le cartelle: le vedi comparire
   come etichette grigie prima della casella.
3. Incolla dentro il contenuto del file `fantabuddy.yml` che ti ho dato.
4. **Commit changes**.

## 7. Accendi e prova

**Actions** → se compare un avviso, **I understand my workflows, go ahead and
enable them** → a sinistra **FantaBuddy** → **Run workflow**.

Se il pallino diventa verde, guarda Telegram. Da qui in poi gira da solo.

## Se qualcosa non va

Clicca sull'esecuzione fallita e leggi l'ultima riga rossa.

| Errore | Significato |
|---|---|
| `KeyError: 'TELEGRAM_TOKEN'` | manca un secret o il nome e' scritto male |
| `401 Unauthorized` | token Telegram sbagliato o revocato |
| `403 Forbidden` | chiave football-data sbagliata |
| `chat not found` | chat id sbagliato, rifai il punto 2 |
| `ModuleNotFoundError` | manca un file: ricontrolla che siano tutti e undici |
| `variabile playersData non trovata` | Understat ha cambiato pagina |

---

# Come decide

Per ogni tuo giocatore calcola un **fantavoto atteso**:

    probabilita' di giocare x (voto base + bonus attesi + malus attesi)

- **Probabilita' di giocare**: media pesata di Fantacalcio.it, Gazzetta, SOS
  Fanta e Sky, dall'aggregato di fantacalcio-online.com. Il bot legge anche
  quanto le quattro redazioni sono in disaccordo, e te lo dice: un 70% su cui
  concordano tutte non e' un 70% su cui litigano. Gli infortunati vanno a zero.
- **Bonus attesi**: xG e xA per novanta minuti da Understat, aggiornati dopo
  ogni giornata, scalati per i minuti attesi e corretti per gli xG che concede
  l'avversario e per il fattore campo.
- **Rigori**: gerarchia dal dischetto x rigori attesi del club x tasso di
  realizzazione. E' la componente piu' prevedibile del fantacalcio.
- **Portieri**: usa la quota di porta inviolata del mercato scommesse.

Poi prova tutti e sette i moduli e tiene quello col totale piu' alto.

# Manutenzione

- **`rosa.py`**, campo `rig`: posizione nella gerarchia dei rigoristi.
  Aggiornala quando cambia, e' il parametro che sposta di piu'.
- **`rosa.py`**, sezione regolamento: di default il gol vale 3 per tutti i
  ruoli, come da Fantacalcio Classic. Se la tua lega differenzia
  (3 attaccante / 3,5 centrocampista / 4 difensore) cambia il dizionario `GOL`.
  **Verificalo prima di fidarti del bot.**
- Dopo un trasferimento di gennaio, aggiorna nome e club in `rosa.py`.

# Limiti da conoscere

- Il bot prevede i bonus, non la prestazione: il voto base e' fisso a 6.0.
- Le formazioni ufficiali escono circa un'ora prima e il controllo gira ogni
  dieci minuti, quindi il secondo messaggio puo' arrivare con dieci minuti di
  ritardo, e su GitHub gratuito i cron slittano di qualche minuto in piu'.
  Se hai un giocatore nella partita di apertura, tieni comunque d'occhio il
  telefono nell'ora prima del via.
- La lettura delle probabili dipende da come e' impaginato un sito. Se cambia,
  il bot non si blocca: ripiega su stime prudenziali e te lo scrive.
