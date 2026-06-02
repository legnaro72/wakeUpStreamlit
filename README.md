# Wake Apps

Repository per risvegliare applicazioni Streamlit Cloud e gestire/diagnosticare il wake-up Render.

La soluzione e' un'integrazione:

- le app Streamlit continuano a usare Playwright e la logica del bottone `Yes, get this app back up!`
- l'app Render puo' essere chiamata manualmente o in backup tramite GitHub Actions
- per Render, lo scheduling primario consigliato e' uno scheduler HTTP esterno
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

## Scheduling Render esterno

Per Render la soluzione raccomandata non e' piu' affidarsi a GitHub Actions come scheduler primario.

La soluzione consigliata e':

```text
scheduler esterno ogni 12 minuti -> endpoint Render protetto -> Python decide se eseguire o saltare
```

Specifica operativa:

```text
docs/render-external-scheduler.md
```

GitHub Actions resta utile come backup, diagnostica e lancio manuale.

### Diagnostica schedule

File:

```text
.github/workflows/schedule-canary.yml
```

Esegue solo un comando `date` ogni 5 minuti. Serve a verificare se GitHub sta consegnando gli eventi `schedule` al repository. Se questo workflow non parte automaticamente, il problema non e' Render e non e' il codice Python: e' lo scheduling GitHub Actions del repository.

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
0 5,6,9,10,13,14,17,18,21,22 * * *
```

Il cron GitHub e' in UTC. Lo script filtra poi l'orario reale in `Europe/Rome` usando:

```text
STREAMLIT_RUN_HOURS=7,11,15,19,23
```

Quindi il wake-up Streamlit effettivo avviene alle:

```text
07:00, 11:00, 15:00, 19:00, 23:00 Europe/Rome
```

La doppia lista di ore UTC serve a coprire sia ora solare sia ora legale. Se GitHub avvia un run candidato che in Italia non corrisponde a una delle ore configurate, lo script stampa `SKIPPED` e non apre Chromium.

### Render

File schedulato automatico:

```text
.github/workflows/render-heartbeat.yml
```

File per ping manuale singolo:

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

Il workflow parte ogni 12 minuti tutto il giorno, ai minuti `07`, `19`, `31`, `43` e `55` di ogni ora. Lo script filtra poi l'orario reale in `Europe/Rome`, quindi ora legale e ora solare sono gestite automaticamente.

Questo evita ambiguita' tra UTC, ora solare e ora legale: GitHub Actions schedula in UTC, mentre la decisione se fare davvero il ping viene presa dal codice Python usando `Europe/Rome`. I minuti non partono da `00` per ridurre il rischio di ritardi o run saltati nei momenti di maggior carico GitHub.

Finestre Render:

- 07:00 - 10:30 Europe/Rome
- 20:00 - 23:30 Europe/Rome

Frequenza effettiva:

- 07:07, 07:19, 07:31, ..., 10:19
- 20:07, 20:19, 20:31, ..., 23:19

Fuori da queste finestre il workflow puo' comunque apparire nella lista GitHub Actions, ma lo script stampa `SKIPPED` e non chiama Render.

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

## Esecuzione locale

Per eseguire solo il wake Render in locale:

```powershell
python -m pip install -r requirements-wake.txt
$env:WAKE_TARGETS = "render"
python -u wake_streamlit.py
```

Per eseguire anche il wake Streamlit serve Playwright con Chromium:

```powershell
python -m pip install -r requirements-wake.txt
python -m pip install "playwright>=1.44,<2"
python -m playwright install chromium
$env:WAKE_TARGETS = "streamlit"
python -u wake_streamlit.py
```

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

Per gestire cold start lenti di Render, ogni chiamata usa timeout HTTP di 90 secondi e fino a 2 tentativi, con 15 secondi di pausa tra i tentativi. Questi valori sono configurabili con `HTTP_TIMEOUT_SECONDS`, `RENDER_ATTEMPTS` e `RENDER_RETRY_DELAY_SECONDS`.

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
- pulsanti per avviare i workflow GitHub Actions

Per deployarla su Streamlit Cloud, usa questo repository e `app.py` come entry point.

Dopo il deploy, aggiungi l'URL della dashboard in `streamlit_urls.txt`, cosi' anche questa app viene mantenuta sveglia.

Per avviare i workflow dalla dashboard, configura questi secrets o variabili d'ambiente:

```text
GITHUB_REPOSITORY=owner/nome-repository
GITHUB_TOKEN=token-github
GITHUB_REF_NAME=main
```

Il token deve poter avviare GitHub Actions sul repository. Per un fine-grained personal access token, abilita i permessi `Actions: Read and write` sul repository.

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
