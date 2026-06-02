import os
from pathlib import Path

import requests
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent
STREAMLIT_URLS_FILE = ROOT_DIR / "streamlit_urls.txt"
RENDER_URLS_FILE = ROOT_DIR / "render_urls.txt"
GITHUB_API_URL = "https://api.github.com"


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


def config_value(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value

    try:
        secret_value = st.secrets.get(name, default)
    except Exception:
        return default

    return str(secret_value) if secret_value else default


def github_token() -> str:
    return config_value("GITHUB_TOKEN") or config_value("GH_TOKEN")


def dispatch_workflow(
    repository: str,
    token: str,
    workflow_file: str,
    ref: str,
    inputs: dict[str, str] | None = None,
) -> tuple[bool, str]:
    url = f"{GITHUB_API_URL}/repos/{repository}/actions/workflows/{workflow_file}/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload: dict[str, str | dict[str, str]] = {"ref": ref}

    if inputs:
        payload["inputs"] = inputs

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        return False, f"Richiesta non riuscita: {exc}"

    if response.status_code == 204:
        return True, "Workflow avviato"

    return False, f"GitHub ha risposto {response.status_code}: {response.text}"


st.set_page_config(page_title="Wake Apps", layout="wide")

streamlit_urls = read_urls(STREAMLIT_URLS_FILE)
render_urls = read_urls(RENDER_URLS_FILE)
github_repository = config_value("GITHUB_REPOSITORY")
github_ref = config_value("GITHUB_REF_NAME", "main")
token = github_token()

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
        width="stretch",
        hide_index=True,
    )

with tab_render:
    st.dataframe(
        app_rows("Render", render_urls),
        width="stretch",
        hide_index=True,
    )

with tab_all:
    st.dataframe(
        app_rows("Streamlit", streamlit_urls) + app_rows("Render", render_urls),
        width="stretch",
        hide_index=True,
    )

with tab_workflows:
    workflows = [
        {
            "Nome": "Wake Streamlit Apps Scheduled",
            "File": "wake-streamlit.yml",
            "Target": "streamlit",
            "Frequenza": "06:00 e 18:00 UTC",
        },
        {
            "Nome": "Render Heartbeat Scheduled",
            "File": "render-heartbeat.yml",
            "Target": "render",
            "Frequenza": "Ogni 12 minuti nelle finestre Europe/Rome",
        },
        {
            "Nome": "Wake Render App Manual Ping",
            "File": "wake-render.yml",
            "Target": "render",
            "Frequenza": "Manuale singolo",
        },
        {
            "Nome": "Wake Apps Manual",
            "File": "manual_main.yml",
            "Target": "streamlit, render, all",
            "Frequenza": "Manuale",
        },
    ]

    st.dataframe(
        workflows,
        width="stretch",
        hide_index=True,
    )

    if not github_repository or not token:
        st.warning("Configura GITHUB_REPOSITORY e GITHUB_TOKEN per avviare i workflow dalla dashboard.")
    else:
        st.caption(f"Repository: {github_repository} - Ref: {github_ref}")

    disabled = not github_repository or not token
    action_cols = st.columns(3)

    if action_cols[0].button("Avvia Streamlit", disabled=disabled):
        success, message = dispatch_workflow(
            github_repository,
            token,
            "wake-streamlit.yml",
            github_ref,
        )
        st.success(message) if success else st.error(message)

    if action_cols[1].button("Avvia Render", disabled=disabled):
        success, message = dispatch_workflow(
            github_repository,
            token,
            "wake-render.yml",
            github_ref,
        )
        st.success(message) if success else st.error(message)

    manual_target = action_cols[2].selectbox("Manuale", ["render", "streamlit", "all"])
    render_duration_minutes = st.number_input(
        "Durata Render manuale",
        min_value=0,
        max_value=240,
        value=120,
        step=12,
    )

    if st.button("Avvia manuale", disabled=disabled):
        success, message = dispatch_workflow(
            github_repository,
            token,
            "manual_main.yml",
            github_ref,
            {
                "targets": manual_target,
                "render_urls": "",
                "streamlit_urls": "",
                "render_duration_minutes": str(render_duration_minutes),
                "render_interval_minutes": "12",
            },
        )
        st.success(message) if success else st.error(message)
