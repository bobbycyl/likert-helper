import os

import streamlit as st


class LikertValueError(ValueError):
    pass


def _is_subdirectory(path: str, parent: str) -> bool:
    path = os.path.abspath(path)
    parent = os.path.abspath(parent)
    common = os.path.commonpath([path, parent])

    return common == parent


def clean_cache(prefix: str):
    for key in list(st.session_state.keys()):
        if str(key).startswith(prefix):
            del st.session_state[key]


def select_scale() -> str:
    scales_dir = os.path.join(str(os.path.dirname(__file__)), "..", "scales")
    local_scale_files = [
        x
        for x in os.listdir(scales_dir)
        if os.path.splitext(x)[1] in [".toml", ".json"]
    ]
    scale = st.selectbox(
        "Select a scale",
        local_scale_files,
        index=None,
        key="test_scale",
        format_func=lambda x: str(os.path.splitext(x)[0]),
    )
    if scale:
        scale_path = os.path.join(scales_dir, scale)
        if not _is_subdirectory(scale_path, scales_dir):
            raise LikertValueError("invalid scale file")
        return scale_path
    raise LikertValueError("no scale selected")
