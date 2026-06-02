# Wake Apps

Repository per risvegliare applicazioni Streamlit Cloud e Render tramite GitHub Actions.

La soluzione e' un'integrazione:

- le app Streamlit continuano a usare Playwright e la logica del bottone `Yes, get this app back up!`
- l'app Render usa una semplice richiesta HTTP con `requests`
- i workflow sono separati, cosi' Render non usa browser headless
- una dashboard Streamlit (`app.py`) mostra le app attualmente gestite

## Liste app

Le app gestite sono in due file:

```text
streamlit_urls.txt
render_urls.txt
```

Per aggiungere una nuova app in modo permanente, aggiungi una riga al file corretto, fai commit e push.

La dashboard Streamlit legge gli stessi file, quindi mostra sempre le app configurate nel repository.

## Workflow disponibili

### Streamlit

File:

```text
.github/workflows/wake-streamlit.yml
```

Esegue:

```text
WAKE_TARGETS=streamlit
```

Mantiene la logica storica:

- apre ogni URL Streamlit con Chromium headless
- cerca il bottone `Yes, get this app back up!`
- clicca il bottone se presente
- ricarica la pagina
- stampa il risultato nei log

Schedulazione attuale:

```cron
0 6,18 * * *
```

### Render

File:

```text
.github/workflows/wake-render.yml
```

Esegue:

```text
WAKE_TARGETS=render
```

Usa solo `requests`, senza Playwright e senza browser headless.

Gli URL sono letti da:

```text
render_urls.txt
```

Il workflow parte ogni 12 minuti nelle ore UTC che coprono le finestre richieste. Lo script filtra poi l'orario reale in `Europe/Rome`, quindi ora legale e ora solare sono gestite automaticamente.

Finestre Render:

- 07:00 - 10:30 Europe/Rome
- 20:00 - 23:30 Europe/Rome

Frequenza effettiva:

- 07:00, 07:12, 07:24, ..., 10:24
- 20:00, 20:12, 20:24, ..., 23:24

### Manuale

File:

```text
.github/workflows/manual_main.yml
```

Permette di lanciare manualmente:

- `streamlit`
- `render`
- `all`

Il manuale usa `FORCE_PING=true`, quindi il ping Render parte anche fuori dalle fasce orarie.

Di default il workflow manuale esegue Render per due ore:

```text
targets=render
render_duration_minutes=120
render_interval_minutes=12
```

In pratica:

- ping immediato
- attesa 12 minuti
- nuovo ping
- ripetizione fino al termine delle due ore

Per fare un solo ping manuale Render, imposta:

```text
render_duration_minutes=0
```

Per provare URL Render al volo senza modificare file, usa l'input `render_urls` con URL separati da virgola.

## Configurazione

### Streamlit

Gli URL Streamlit sono configurati in:

```text
streamlit_urls.txt
```

Per sovrascriverli senza modificare codice:

```text
STREAMLIT_URLS=https://app1.streamlit.app/,https://app2.streamlit.app/
```

### Render

Gli URL Render sono configurati in:

```text
render_urls.txt
```

Per configurare uno o piu' URL Render:

```text
RENDER_URLS=https://therapy-reminder.onrender.com/,https://altra-app.onrender.com/
```

Sono supportate anche le variabili `PING_URLS` e `PING_URL` come alias.

## Log Render

Ogni ping Render stampa almeno:

- data e ora
- URL chiamato
- status HTTP
- esito

Esempio:

```text
2026-04-09 07:00:01 CEST
URL: https://therapy-reminder.onrender.com/
Status: 200
Result: SUCCESS
```

## Deploy

1. Fai commit e push dei file nel repository GitHub.
2. Verifica che GitHub Actions sia abilitato.
3. Non serve configurare nulla su Render.
4. Non serve configurare variabili su GitHub se gli URL di default vanno bene.
5. Per aggiungere app Render o Streamlit in modo permanente, modifica i file `render_urls.txt` o `streamlit_urls.txt`.

## Dashboard Streamlit

File:

```text
app.py
```

Mostra:

- app Streamlit gestite
- app Render gestite
- totale app
- workflow GitHub Actions associati

Per deployarla su Streamlit Cloud, usa questo repository e `app.py` come entry point.

Dopo il deploy, aggiungi l'URL della dashboard in `streamlit_urls.txt`, cosi' anche questa app viene mantenuta sveglia.

## Endpoint `/healthz`

Non e' necessario creare `/healthz`.

Per Render e' sufficiente una normale richiesta HTTP alla homepage:

```text
https://therapy-reminder.onrender.com/
```

Un endpoint `/healthz` puo' essere utile in futuro se vuoi un controllo piu' leggero e stabile, ma deve essere aggiunto nel repository dell'app Render, non in questo repository di wake-up.

## Costi

La soluzione resta completamente gratuita:

- GitHub Actions schedulate
- nessun Render Cron Job
- nessun servizio esterno a pagamento
- nessun componente con costo ricorrente
- Render usa solo una richiesta HTTP con `requests`

## Limitazioni

- GitHub Actions scheduled puo' partire con qualche minuto di ritardo.
- Il manuale Render da due ore mantiene un job GitHub Actions attivo per circa due ore.
- Se GitHub Actions viene disabilitato, i ping non partono.
- Se il repository resta inattivo a lungo, GitHub puo' sospendere i workflow schedulati.
- Render potrebbe cambiare policy sui piani gratuiti o sulla gestione dello sleep.
- La logica Streamlit richiede Playwright perche' Streamlit Cloud puo' mostrare il bottone di wake-up.
