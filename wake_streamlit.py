from playwright.sync_api import sync_playwright
from datetime import datetime

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
    "https://dediche-musicali-ff.streamlit.app/",
    "https://ddgpilli.streamlit.app/"
]

print("=" * 80)
print("STREAMLIT WAKEUP")
print(datetime.now())
print("=" * 80)

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

    for url in APPS:

        print()
        print("-" * 80)
        print(f"APP: {url}")
        print("-" * 80)

        page = None

        try:

            page = browser.new_page()

            print("Apertura URL...")

            page.goto(
                url,
                timeout=180000,
                wait_until="domcontentloaded"
            )

            page.wait_for_timeout(5000)

            try:

                wake_button = page.get_by_text(
                    "Yes, get this app back up!"
                )

                wake_button.click(timeout=10000)

                print("APP IN SLEEP - Bottone di wake-up cliccato")

                page.wait_for_timeout(60000)

            except Exception:

                print("APP già attiva oppure bottone wake-up non presente")

            try:

                page.reload(timeout=180000)

                page.wait_for_timeout(15000)

            except Exception as e:

                print(f"Reload non riuscito: {e}")

            title = page.title()

            print(f"Titolo pagina: {title}")
            print("Completata")

        except Exception as e:

            print(f"ERRORE: {e}")

        finally:

            if page:
                try:
                    page.close()
                except:
                    pass

    browser.close()

print()
print("=" * 80)
print("FINE")
print("=" * 80)