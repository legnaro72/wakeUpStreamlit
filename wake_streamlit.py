import os
import sys
import time as time_module
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT_DIR = Path(__file__).resolve().parent
STREAMLIT_URLS_FILE = ROOT_DIR / "streamlit_urls.txt"
RENDER_URLS_FILE = ROOT_DIR / "render_urls.txt"
TIMEZONE = "Europe/Rome"
RENDER_WINDOWS = (
    (time(7, 0), time(10, 30)),
    (time(20, 0), time(23, 30)),
)
HTTP_TIMEOUT_SECONDS = 30
DEFAULT_RENDER_DURATION_MINUTES = 0
DEFAULT_RENDER_INTERVAL_MINUTES = 12


def parse_urls(raw_urls: str | None) -> list[str]:
    if not raw_urls:
        return []

    return [url.strip() for url in raw_urls.split(",") if url.strip()]


def read_urls_file(path: Path) -> list[str]:
    if not path.exists():
        return []

    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            urls.append(value)
    return urls


def env_or_file_urls(env_value: str | None, path: Path) -> list[str]:
    env_urls = parse_urls(env_value)
    return env_urls or read_urls_file(path)


def configured_streamlit_urls() -> list[str]:
    return env_or_file_urls(os.getenv("STREAMLIT_URLS"), STREAMLIT_URLS_FILE)


def configured_render_urls() -> list[str]:
    raw_urls = os.getenv("RENDER_URLS") or os.getenv("PING_URLS") or os.getenv("PING_URL")
    return env_or_file_urls(raw_urls, RENDER_URLS_FILE)


def configured_targets() -> set[str]:
    raw_targets = os.getenv("WAKE_TARGETS", "all")
    targets = {target.strip().lower() for target in raw_targets.split(",") if target.strip()}
    return targets or {"all"}


def is_inside_render_window(now: datetime) -> bool:
    current_time = now.time().replace(tzinfo=None)
    return any(start <= current_time <= end for start, end in RENDER_WINDOWS)


def positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if not raw_value:
        return default

    try:
        return max(0, int(raw_value))
    except ValueError:
        print(f"Warning: invalid {name}={raw_value!r}; using {default}")
        return default


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


def ping_render_urls(now: datetime, urls: list[str]) -> bool:
    if not urls:
        print("Result: ERROR - no Render URLs configured")
        return False

    return all(ping_render_url(url, now) for url in urls)


def wake_render_apps(now: datetime) -> bool:
    force_ping = os.getenv("FORCE_PING", "").lower() in {"1", "true", "yes"}

    if not force_ping and not is_inside_render_window(now):
        print(now.strftime("%Y-%m-%d %H:%M:%S %Z"))
        print(f"Result: SKIPPED - outside Render wake-up windows for {TIMEZONE}")
        return True

    urls = configured_render_urls()
    duration_minutes = positive_int_from_env("RENDER_DURATION_MINUTES", DEFAULT_RENDER_DURATION_MINUTES)
    interval_minutes = positive_int_from_env("RENDER_INTERVAL_MINUTES", DEFAULT_RENDER_INTERVAL_MINUTES)

    if duration_minutes == 0:
        return ping_render_urls(now, urls)

    deadline = time_module.monotonic() + (duration_minutes * 60)
    interval_seconds = max(60, interval_minutes * 60)
    iteration = 1
    success_count = 0
    error_count = 0

    while True:
        current_now = datetime.now(ZoneInfo(TIMEZONE))
        print(f"Render burst iteration: {iteration}")
        if ping_render_urls(current_now, urls):
            success_count += 1
        else:
            error_count += 1

        if time_module.monotonic() >= deadline:
            break

        remaining_seconds = deadline - time_module.monotonic()
        sleep_seconds = min(interval_seconds, remaining_seconds)
        print(f"Next Render ping in {round(sleep_seconds / 60, 2)} minutes")
        time_module.sleep(sleep_seconds)
        iteration += 1

    print(f"Render burst summary: {success_count} success, {error_count} error")
    return success_count > 0


def wake_streamlit_apps(now: datetime) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        if exc.name != "playwright":
            raise

        print("=" * 80)
        print("STREAMLIT WAKEUP")
        print(now.strftime("%Y-%m-%d %H:%M:%S %Z"))
        print("=" * 80)
        print("Result: ERROR - Playwright non installato")
        print('Installa le dipendenze Streamlit wake con: python -m pip install "playwright>=1.44,<2"')
        print("Poi installa Chromium con: python -m playwright install chromium")
        return False

    urls = configured_streamlit_urls()
    all_ok = True

    if not urls:
        print("Result: ERROR - no Streamlit URLs configured")
        return False

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


def stop_if_running_in_streamlit() -> None:
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except Exception:
        return

    if get_script_run_ctx() is None:
        return

    st.error("Questo file e' uno script di automazione, non una dashboard Streamlit.")
    st.code("python -u wake_streamlit.py", language="powershell")
    st.info("Per aprire la dashboard usa invece: streamlit run app.py")
    st.stop()


if __name__ == "__main__":
    stop_if_running_in_streamlit()
    sys.exit(main())
