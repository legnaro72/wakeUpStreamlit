import os
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo


STREAMLIT_DEFAULT_URLS = [
    "https://farm-tornei-subbuteo-superba-all-db.streamlit.app/",
    "https://torneo-subbuteo-superba-ita-all-db.streamlit.app/",
    "https://torneo-subbuteo-ff-superba-ita-all-db.streamlit.app/",
    "https://torneo-subbuteo-superba-new-version-svizzero-alldb.streamlit.app/",
    "https://edit-superba-club-all-db-new.streamlit.app/",
    "https://farm-tornei-subbuteo-tigullio-all-db.streamlit.app/",
    "https://torneo-subbuteo-tigullio-ita-all-db.streamlit.app/",
    "https://torneo-subbuteo-ff-tigullio-ita-all-db.streamlit.app/",
    "https://torneo-subbuteo-tigullio-new-version-svizzero-alldb.streamlit.app/",
    "https://edit-tigullio-club-all-db-new.streamlit.app/",
    "https://farm-tornei-subbuteo-piercrew-all-db.streamlit.app/",
    "https://torneo-subbuteo-piercrew-ita-all-db.streamlit.app/",
    "https://torneo-subbuteo-ff-piercrew-ita-all-db.streamlit.app/",
    "https://torneo-subbuteo-piercrew-new-version-svizzero-alldb.streamlit.app/",
    "https://edit-piercrew-club-all-db-new.streamlit.app/",
    "https://dediche-musicali-ff.streamlit.app/",
    "https://ddgpilli.streamlit.app/",
]

RENDER_DEFAULT_URLS = ["https://therapy-reminder.onrender.com/"]
TIMEZONE = "Europe/Rome"
RENDER_WINDOWS = (
    (time(7, 0), time(10, 30)),
    (time(20, 0), time(23, 30)),
)
HTTP_TIMEOUT_SECONDS = 30


def parse_urls(raw_urls: str | None, default_urls: list[str]) -> list[str]:
    if not raw_urls:
        return default_urls

    urls = [url.strip() for url in raw_urls.split(",") if url.strip()]
    return urls or default_urls


def configured_streamlit_urls() -> list[str]:
    return parse_urls(os.getenv("STREAMLIT_URLS"), STREAMLIT_DEFAULT_URLS)


def configured_render_urls() -> list[str]:
    raw_urls = os.getenv("RENDER_URLS") or os.getenv("PING_URLS") or os.getenv("PING_URL")
    return parse_urls(raw_urls, RENDER_DEFAULT_URLS)


def configured_targets() -> set[str]:
    raw_targets = os.getenv("WAKE_TARGETS", "all")
    targets = {target.strip().lower() for target in raw_targets.split(",") if target.strip()}
    return targets or {"all"}


def is_inside_render_window(now: datetime) -> bool:
    current_time = now.time().replace(tzinfo=None)
    return any(start <= current_time <= end for start, end in RENDER_WINDOWS)


def log_http_result(now: datetime, url: str, status: int | str, result: str) -> None:
    print(now.strftime("%Y-%m-%d %H:%M:%S %Z"))
    print(f"URL: {url}")
    print(f"Status: {status}")
    print(f"Result: {result}")
    print("-" * 80)


def ping_render_url(url: str, now: datetime) -> bool:
    import requests

    try:
        response = requests.get(url, timeout=HTTP_TIMEOUT_SECONDS)
        success = 200 <= response.status_code < 400
        log_http_result(now, url, response.status_code, "SUCCESS" if success else "ERROR")
        return success
    except requests.RequestException as exc:
        log_http_result(now, url, "N/A", f"ERROR - {exc}")
        return False


def wake_render_apps(now: datetime) -> bool:
    force_ping = os.getenv("FORCE_PING", "").lower() in {"1", "true", "yes"}

    if not force_ping and not is_inside_render_window(now):
        print(now.strftime("%Y-%m-%d %H:%M:%S %Z"))
        print(f"Result: SKIPPED - outside Render wake-up windows for {TIMEZONE}")
        return True

    urls = configured_render_urls()
    return all(ping_render_url(url, now) for url in urls)


def wake_streamlit_apps(now: datetime) -> bool:
    from playwright.sync_api import sync_playwright

    urls = configured_streamlit_urls()
    all_ok = True

    print("=" * 80)
    print("STREAMLIT WAKEUP")
    print(now.strftime("%Y-%m-%d %H:%M:%S %Z"))
    print("=" * 80)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        for url in urls:
            print()
            print("-" * 80)
            print(f"APP: {url}")
            print("-" * 80)

            page = None

            try:
                page = browser.new_page()
                print("Apertura URL...")

                page.goto(url, timeout=180000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)

                try:
                    wake_button = page.get_by_text("Yes, get this app back up!")
                    wake_button.click(timeout=10000)
                    print("APP IN SLEEP - Bottone di wake-up cliccato")
                    page.wait_for_timeout(60000)
                except Exception:
                    print("APP gia' attiva oppure bottone wake-up non presente")

                try:
                    page.reload(timeout=180000)
                    page.wait_for_timeout(15000)
                except Exception as exc:
                    print(f"Reload non riuscito: {exc}")

                title = page.title()
                print(f"Titolo pagina: {title}")
                print("Result: SUCCESS")

            except Exception as exc:
                all_ok = False
                print(f"Result: ERROR - {exc}")

            finally:
                if page:
                    try:
                        page.close()
                    except Exception:
                        pass

        browser.close()

    print()
    print("=" * 80)
    print("FINE STREAMLIT WAKEUP")
    print("=" * 80)
    return all_ok


def main() -> int:
    now = datetime.now(ZoneInfo(TIMEZONE))
    targets = configured_targets()
    run_all = "all" in targets
    results = []

    if run_all or "streamlit" in targets:
        results.append(wake_streamlit_apps(now))

    if run_all or "render" in targets:
        results.append(wake_render_apps(now))

    if not results:
        print(f"Result: ERROR - no valid WAKE_TARGETS configured: {sorted(targets)}")
        return 1

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
