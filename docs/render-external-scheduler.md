# Scheduling esterno Render

## Obiettivo

Usare uno scheduler HTTP esterno come meccanismo principale per chiamare l'app Render, senza dipendere dal trigger `schedule` di GitHub Actions.

GitHub Actions resta utile per:

- esecuzioni manuali;
- diagnostica;
- backup;
- dashboard Streamlit;
- eventuali test.

Non deve essere considerato lo scheduler primario per Render.

## Architettura raccomandata

```text
cron-job.org / servizio equivalente
        |
        | GET o POST ogni 12 minuti
        v
Endpoint Render protetto da token
        |
        | Python controlla Europe/Rome e idempotenza
        v
executed / skipped_outside_time_window / already_executed_recently / error
```

## Endpoint richiesto sull'app Render

L'app Render deve esporre un endpoint pubblico, per esempio:

```text
GET https://therapy-reminder.onrender.com/trigger?token=SECRET
```

Il token deve stare in variabile d'ambiente su Render:

```text
TRIGGER_TOKEN=valore-segreto-lungo
```

Non va hardcoded nel codice.

## Fasce orarie

La logica temporale deve stare nel codice Python dell'app Render, non nello scheduler esterno.

Timezone:

```text
Europe/Rome
```

Finestre:

```text
07:00 - 10:30
20:00 - 23:30
```

Frequenza trigger esterno:

```text
ogni 12 minuti
```

## Risposte HTTP consigliate

L'endpoint dovrebbe rispondere sempre in JSON:

```json
{"status": "executed", "now": "2026-06-02T20:07:00+02:00"}
```

```json
{"status": "skipped_outside_time_window", "now": "2026-06-02T14:07:00+02:00"}
```

```json
{"status": "already_executed_recently", "now": "2026-06-02T20:08:00+02:00"}
```

```json
{"status": "error", "message": "..."}
```

## Idempotenza

Per evitare doppie esecuzioni, l'app Render deve salvare l'ultima esecuzione riuscita.

Regola consigliata:

```text
Se l'ultima esecuzione valida e' avvenuta meno di 10 minuti fa, rispondere already_executed_recently.
```

Lo stato puo' essere salvato in:

- database gia' usato dall'app;
- file persistente se il servizio lo supporta;
- Redis o storage esterno;
- tabella dedicata `scheduler_runs`.

Su Render Free il filesystem puo' non essere affidabile tra restart, quindi e' preferibile usare uno storage esterno o il database dell'app.

## Esempio FastAPI

```python
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query

app = FastAPI()

TIMEZONE = "Europe/Rome"
WINDOWS = (
    (time(7, 0), time(10, 30)),
    (time(20, 0), time(23, 30)),
)
MIN_SECONDS_BETWEEN_RUNS = 10 * 60

last_executed_at: datetime | None = None


def inside_window(now: datetime) -> bool:
    current_time = now.time().replace(tzinfo=None)
    return any(start <= current_time <= end for start, end in WINDOWS)


def run_job() -> None:
    # Inserire qui la logica reale dell'app Render.
    pass


@app.get("/trigger")
def trigger(token: str = Query(default="")):
    expected_token = os.getenv("TRIGGER_TOKEN", "")
    if not expected_token or token != expected_token:
        raise HTTPException(status_code=401, detail="invalid token")

    now = datetime.now(ZoneInfo(TIMEZONE))

    if not inside_window(now):
        return {
            "status": "skipped_outside_time_window",
            "now": now.isoformat(),
            "timezone": TIMEZONE,
        }

    global last_executed_at
    if last_executed_at and now - last_executed_at < timedelta(seconds=MIN_SECONDS_BETWEEN_RUNS):
        return {
            "status": "already_executed_recently",
            "now": now.isoformat(),
            "last_executed_at": last_executed_at.isoformat(),
        }

    try:
        run_job()
    except Exception as exc:
        return {
            "status": "error",
            "now": now.isoformat(),
            "message": str(exc),
        }

    last_executed_at = now
    return {
        "status": "executed",
        "now": now.isoformat(),
        "timezone": TIMEZONE,
    }
```

Nota: l'esempio usa memoria di processo per `last_executed_at`. Va bene solo come scheletro. In produzione e' meglio salvare lo stato su database.

## Configurazione scheduler esterno

Configurazione consigliata per cron-job.org o equivalente:

```text
URL: https://therapy-reminder.onrender.com/trigger?token=SECRET
Metodo: GET
Frequenza: ogni 12 minuti
Timezone: Europe/Rome, se supportata
Timeout: 90 secondi o massimo disponibile
Retry: abilitato, se disponibile
```

Se lo scheduler non gestisce bene le fasce orarie, farlo chiamare ogni 12 minuti tutto il giorno. L'endpoint Render decidera' se eseguire o saltare.

## Criterio di accettazione

La soluzione e' accettata se per 3 giorni consecutivi:

- lo scheduler esterno registra chiamate regolari;
- Render registra trigger ricevuti;
- fuori fascia risponde `skipped_outside_time_window`;
- dentro fascia risponde `executed` oppure `already_executed_recently`;
- non ci sono doppie esecuzioni indesiderate;
- GitHub Actions puo' restare solo come backup/manuale.
