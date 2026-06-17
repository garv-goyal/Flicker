"""Flicker — app router. Defines the pages and renders the shared chrome.

Uses st.navigation with position="hidden" so Streamlit never draws its own
sidebar nav (our custom top bar handles navigation). Each view file under
views/ renders only its page body.
"""
import streamlit as st

from utils import ui
from utils.chatbot import render_chat

st.set_page_config(page_title="Flicker — Film Intelligence", page_icon=ui.favicon(),
                   layout="wide", initial_sidebar_state="collapsed")

pages = [
    st.Page("views/overview.py", title="Pulse", default=True),
    st.Page("views/critical.py", title="Critics", url_path="critical"),
    st.Page("views/hype.py", title="Hype", url_path="hype"),
    st.Page("views/genres.py", title="Genres", url_path="genres"),
    st.Page("views/operations.py", title="Pipeline", url_path="operations"),
    st.Page("views/subscribe.py", title="Weekly", url_path="subscribe"),
]

current = st.navigation(pages, position="hidden")

ui.inject_css()
ui.header(active=current.url_path or "overview")
current.run()
ui.footer()
render_chat()
