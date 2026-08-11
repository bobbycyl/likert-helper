import os

import streamlit as st

from likert import LikertConfig, compute_likert
from stutils.stutils import LikertValueError, select_scale

try:
    scale_path = select_scale()
    scale_ext = os.path.splitext(scale_path)[1]
    scale_config = (
        LikertConfig.from_json(scale_path)
        if scale_ext == ".json"
        else LikertConfig.from_toml(scale_path)
    )

    records = st.file_uploader("Upload your records", type="csv")

    if records is not None and not isinstance(records, list):
        try:
            df = compute_likert(records, scale_config)
            st.dataframe(df)
        except Exception as e:
            st.error(e)
except LikertValueError:
    st.error("please select a valid scale")
