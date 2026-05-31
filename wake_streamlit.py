from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

APPS = [
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
	"https://ddgpilli.streamlit.app/",
]

now_rome = datetime.now(ZoneInfo("Europe/Rome"))

if now_rome.hour not in [7, 19]:
    print(f"Ora italiana: {now_rome}. Non è ora di svegliare le app.")
    raise SystemExit(0)

print(f"Ora italiana: {now_rome}. Sveglio le app Streamlit...")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    for url in APPS:
        try:
            print(f"Apro: {url}")
            page.goto(url, wait_until="networkidle", timeout=120_000)
            page.wait_for_timeout(15_000)
            print(f"OK: {url}")
        except Exception as e:
            print(f"ERRORE su {url}: {e}")

    browser.close()