from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent
STREAMLIT_URLS_FILE = ROOT_DIR / "streamlit_urls.txt"
RENDER_URLS_FILE = ROOT_DIR / "render_urls.txt"


def read_urls(path: Path) -> list[str]:
    if not path.exists():
        return []

    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            urls.append(value)
    return urls


def app_rows(kind: str, urls: list[str]) -> list[dict[str, str | int]]:
    return [
        {
            "N": index,
            "Tipo": kind,
            "URL": url,
        }
        for index, url in enumerate(urls, start=1)
    ]


st.set_page_config(page_title="Wake Apps", layout="wide")

streamlit_urls = read_urls(STREAMLIT_URLS_FILE)
render_urls = read_urls(RENDER_URLS_FILE)

st.title("Wake Apps")

metric_cols = st.columns(3)
metric_cols[0].metric("Streamlit", len(streamlit_urls))
metric_cols[1].metric("Render", len(render_urls))
metric_cols[2].metric("Totale", len(streamlit_urls) + len(render_urls))

tab_streamlit, tab_render, tab_all, tab_workflows = st.tabs(
    ["Streamlit", "Render", "Tutte", "Workflow"]
)

with tab_streamlit:
    st.dataframe(
        app_rows("Streamlit", streamlit_urls),
        use_container_width=True,
        hide_index=True,
    )

with tab_render:
    st.dataframe(
        app_rows("Render", render_urls),
        use_container_width=True,
        hide_index=True,
    )

with tab_all:
    st.dataframe(
        app_rows("Streamlit", streamlit_urls) + app_rows("Render", render_urls),
        use_container_width=True,
        hide_index=True,
    )

with tab_workflows:
    st.dataframe(
        [
            {
                "Nome": "Wake Streamlit Apps Scheduled",
                "File": ".github/workflows/wake-streamlit.yml",
                "Target": "streamlit",
                "Frequenza": "06:00 e 18:00 UTC",
            },
            {
                "Nome": "Wake Render App Scheduled",
                "File": ".github/workflows/wake-render.yml",
                "Target": "render",
                "Frequenza": "Ogni 12 minuti nelle finestre Europe/Rome",
            },
            {
                "Nome": "Wake Apps Manual",
                "File": ".github/workflows/manual_main.yml",
                "Target": "streamlit, render, all",
                "Frequenza": "Manuale",
            },
        ],
        use_container_width=True,
        hide_index=True,
    )
