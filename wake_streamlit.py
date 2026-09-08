import os
import re
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
DEFAULT_HTTP_TIMEOUT_SECONDS = 90
DEFAULT_RENDER_ATTEMPTS = 2
DEFAULT_RENDER_RETRY_DELAY_SECONDS = 15
DEFAULT_RENDER_DURATION_MINUTES = 0
DEFAULT_RENDER_INTERVAL_MINUTES = 12
DEFAULT_STREAMLIT_INITIAL_WAIT_SECONDS = 12
DEFAULT_STREAMLIT_WAKE_WAIT_SECONDS = 75
DEFAULT_STREAMLIT_RELOAD_WAIT_SECONDS = 30
STREAMLIT_READY_SELECTORS = (
    '[data-testid="stAppViewContainer"]',
    '[data-testid="stApp"]',
    '.stApp',
)
WAKE_BUTTON_PATTERN = re.compile(
    r"(?:yes,?\s*)?(?:get|wake)(?:\s+this)?\s+app(?:\s+back)?\s+up!?",
    re.IGNORECASE,
)
SLEEP_MESSAGE_PATTERN = re.compile(
    r"(?:this\s+)?app\s+(?:has\s+gone|is)\s+to\s+sleep|"
    r"(?:get|wake)(?:\s+this)?\s+app(?:\s+back)?\s+up",
    re.IGNORECASE,
)


def parse_urls(raw_urls: str | None) -> list[str]:
    if not raw_urls:
        return []

    return [url.strip() for url in raw_urls.split(",") if url.strip()]


def unique_urls(urls: list[str]) -> list[str]:
    return list(dict.fromkeys(urls))


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
    return unique_urls(env_urls or read_urls_file(path))


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

    attempts = max(1, positive_int_from_env("RENDER_ATTEMPTS", DEFAULT_RENDER_ATTEMPTS))
    retry_delay_seconds = positive_int_from_env(
        "RENDER_RETRY_DELAY_SECONDS",
        DEFAULT_RENDER_RETRY_DELAY_SECONDS,
    )
    timeout_seconds = max(1, positive_int_from_env("HTTP_TIMEOUT_SECONDS", DEFAULT_HTTP_TIMEOUT_SECONDS))

    for attempt in range(1, attempts + 1):
        attempt_now = now if attempt == 1 else datetime.now(ZoneInfo(TIMEZONE))

        if attempts > 1:
            print(f"Render ping attempt {attempt}/{attempts}")

        try:
            response = requests.get(url, timeout=timeout_seconds)
            success = 200 <= response.status_code < 400
            log_http_result(
                attempt_now,
                url,
                response.status_code,
                "SUCCESS" if success else "ERROR",
            )

            if success:
                return True
        except requests.RequestException as exc:
            log_http_result(attempt_now, url, "N/A", f"ERROR - {exc}")

        if attempt < attempts and retry_delay_seconds > 0:
            print(f"Retry Render ping in {retry_delay_seconds} seconds")
            time_module.sleep(retry_delay_seconds)

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


def visible_wake_button(page):
    candidates = (
        page.get_by_role("button", name=WAKE_BUTTON_PATTERN),
        page.get_by_text(WAKE_BUTTON_PATTERN, exact=False),
    )

    for candidate_group in candidates:
        try:
            for index in range(candidate_group.count()):
                candidate = candidate_group.nth(index)
                if candidate.is_visible(timeout=1000):
                    return candidate
        except Exception:
            continue

    return None


def streamlit_app_is_ready(page) -> bool:
    for selector in STREAMLIT_READY_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=1000):
                return True
        except Exception:
            continue

    return False


def page_contains_sleep_message(page) -> bool:
    try:
        body_text = page.locator("body").inner_text(timeout=3000)
    except Exception:
        return False

    return bool(SLEEP_MESSAGE_PATTERN.search(body_text))


def wait_for_initial_streamlit_state(page, timeout_seconds: int):
    deadline = time_module.monotonic() + timeout_seconds
    saw_sleep_message = False

    while time_module.monotonic() < deadline:
        wake_button = visible_wake_button(page)
        if wake_button is not None:
            return "sleeping", wake_button

        if streamlit_app_is_ready(page):
            return "active", None

        saw_sleep_message = saw_sleep_message or page_contains_sleep_message(page)
        page.wait_for_timeout(1000)

    return ("sleeping_without_button" if saw_sleep_message else "unknown"), None


def wait_for_streamlit_ready(page, timeout_seconds: int) -> bool:
    deadline = time_module.monotonic() + timeout_seconds

    while time_module.monotonic() < deadline:
        if streamlit_app_is_ready(page):
            return True
        page.wait_for_timeout(1000)

    return False


def wake_one_streamlit_app(browser, url: str) -> tuple[str, str]:
    initial_wait_seconds = max(
        1,
        positive_int_from_env(
            "STREAMLIT_INITIAL_WAIT_SECONDS",
            DEFAULT_STREAMLIT_INITIAL_WAIT_SECONDS,
        ),
    )
    wake_wait_seconds = max(
        1,
        positive_int_from_env(
            "STREAMLIT_WAKE_WAIT_SECONDS",
            DEFAULT_STREAMLIT_WAKE_WAIT_SECONDS,
        ),
    )
    reload_wait_seconds = max(
        1,
        positive_int_from_env(
            "STREAMLIT_RELOAD_WAIT_SECONDS",
            DEFAULT_STREAMLIT_RELOAD_WAIT_SECONDS,
        ),
    )

    page = browser.new_page()

    try:
        print("Apertura URL...")
        response = page.goto(url, timeout=180000, wait_until="domcontentloaded")
        if response is not None and response.status >= 400:
            return "error", f"HTTP {response.status}"

        state, wake_button = wait_for_initial_streamlit_state(page, initial_wait_seconds)

        if state == "active":
            return "active", page.title()

        if state == "sleeping_without_button":
            return "error", "pagina in sleep, ma pulsante di wake-up non trovato"

        if state == "unknown" or wake_button is None:
            return "error", "stato app non verificabile: player Streamlit e wake-up assenti"

        wake_button.click(timeout=10000)
        print("APP IN SLEEP - Bottone di wake-up cliccato")

        if not wait_for_streamlit_ready(page, wake_wait_seconds):
            print("App non ancora pronta: reload di verifica...")
            page.reload(timeout=180000, wait_until="domcontentloaded")
            if not wait_for_streamlit_ready(page, reload_wait_seconds):
                if page_contains_sleep_message(page):
                    return "error", "app ancora in sleep dopo il click"
                return "error", "app non pronta dopo click e reload"

        return "woken", page.title()
    finally:
        page.close()


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
    result_counts = {"active": 0, "woken": 0, "error": 0}

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

            try:
                result, detail = wake_one_streamlit_app(browser, url)
            except Exception as exc:
                result, detail = "error", str(exc)

            result_counts[result] += 1
            if result == "active":
                print(f"Titolo pagina: {detail}")
                print("Result: SUCCESS - APP ACTIVE")
            elif result == "woken":
                print(f"Titolo pagina: {detail}")
                print("Result: SUCCESS - APP WOKEN")
            else:
                print(f"Result: ERROR - {detail}")

        browser.close()

    print()
    print("=" * 80)
    print("FINE STREAMLIT WAKEUP")
    print(
        "Summary: "
        f"{result_counts['active']} active, "
        f"{result_counts['woken']} woken, "
        f"{result_counts['error']} error"
    )
    print("=" * 80)
    return result_counts["error"] == 0


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
