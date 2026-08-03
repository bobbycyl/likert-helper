import streamlit as st


def clean_cache(prefix: str):
    for key in list(st.session_state.keys()):
        if str(key).startswith(prefix):
            del st.session_state[key]
