import os

import streamlit as st

from likert import LikertConfig, compute_likert

scales_dir = os.path.join(os.path.dirname(__file__), "..", "scales")
local_scale_files = [
    x for x in os.listdir(scales_dir) if os.path.splitext(x)[1] in [".toml", ".json"]
]
scale = st.selectbox("Select a scale", local_scale_files)
scale_ext = os.path.splitext(scale)[1]
scale_path = os.path.join(scales_dir, scale)
scale_config = (
    LikertConfig.from_json(scale_path)
    if scale_ext == ".json"
    else LikertConfig.from_toml(scale_path)
)

records = st.file_uploader("Upload your records", type="csv")

if records is not None:
    try:
        df = compute_likert(records, scale_config)
    except Exception as e:
        st.error(e)
        st.stop()
    st.dataframe(df)
