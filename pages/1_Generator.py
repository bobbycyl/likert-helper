import json

import streamlit as st

from likert import GroupConfig, ItemConfig, LikertConfig
from likert.model import dump_config
from stutils.stutils import clean_cache


def item_settings(iid: int, content: str):
    with st.container(border=True, horizontal=True):
        st.text("%d: %s" % (iid, content))
        st.checkbox("Reverse", key="gen_it_%d_r" % iid)
        st.number_input("Weight", value=1.0, step=0.01, key="gen_it_%d_w" % iid)
        st.selectbox(
            "Group",
            st.session_state.gen_group_name_list,
            key="gen_it_%d_g" % iid,
        )


def generate_config():
    group_iid_mapping: dict[str, list[int]] = {}
    for iid in range(1, st.session_state.gen_item_length + 1):
        grp_name = st.session_state["gen_it_%d_g" % iid]
        if grp_name not in group_iid_mapping:
            group_iid_mapping[grp_name] = []
        group_iid_mapping[grp_name].append(iid)

    group_config_list: list[GroupConfig] = []
    for grp_name in st.session_state.gen_group_name_list:
        group_config_list.append(
            GroupConfig(
                name=grp_name,
                items=[
                    ItemConfig(
                        id=iid,
                        reverse=st.session_state["gen_it_%d_r" % iid],
                        weight=st.session_state["gen_it_%d_w" % iid],
                    )
                    for iid in group_iid_mapping.get(grp_name, [])
                ],
                # 以下两个参数不支持 GUI 设置，强制规范（不一定默认值）
                aggregate="mean",
                missing_threshold=0.0,
            ),
        )

    return LikertConfig(
        levels_labels={
            level: st.session_state[
                "gen_lvl_label_%d_%d" % (st.session_state.gen_version, level)
            ]
            for level in range(
                st.session_state.gen_min_level,
                st.session_state.gen_levels + st.session_state.gen_min_level,
            )
        },
        groups=group_config_list,
    )


st.info("`aggregate`, `missing_threshold` and `score_bands` not supported yet")
if "gen_item_length" not in st.session_state:
    st.session_state.gen_item_length = 0
if "gen_item_tuple_list" not in st.session_state:
    st.session_state.gen_item_tuple_list = []
if "gen_group_name_list" not in st.session_state:
    st.session_state.gen_group_name_list = []
if "gen_group_length" not in st.session_state:
    st.session_state.gen_group_length = 0
if "gen_levels" not in st.session_state:
    st.session_state.gen_levels = 5
if "gen_min_level" not in st.session_state:
    st.session_state.gen_min_level = 1
if "gen_version" not in st.session_state:
    st.session_state.gen_version = 1


def start():
    clean_cache("gen_lvl_")
    _item_content_list = (st.session_state.gen_items_input or "").split("\n")
    st.session_state.gen_item_length = len(_item_content_list)
    st.session_state.gen_item_tuple_list = [
        (iid, item_content)
        for iid, item_content in enumerate(_item_content_list, start=1)
    ]
    st.session_state.gen_group_name_list = (
        st.session_state.gen_groups_input or ""
    ).split("\n")
    st.session_state.gen_group_length = len(st.session_state.gen_group_name_list)
    st.session_state.gen_version += 1


with st.form("gen_starter"):
    st.text_area("Enter the items line by line.", key="gen_items_input")
    st.text_area("Enter the name of groups line by line.", key="gen_groups_input")
    st.number_input(
        "The number of levels", step=1, min_value=2, max_value=11, key="gen_levels"
    )
    st.number_input(
        "The minimum level", step=1, min_value=0, max_value=1, key="gen_min_level"
    )
    st.form_submit_button("Confirm", on_click=start)


with st.container(border=True):
    for level in range(
        st.session_state.gen_min_level,
        st.session_state.gen_levels + st.session_state.gen_min_level,
    ):
        st.text_input(
            "Level %d" % level,
            key="gen_lvl_label_%d_%d" % (st.session_state.gen_version, level),
        )

with st.container(border=True):
    for iid, item_content in st.session_state.gen_item_tuple_list:
        item_settings(iid, item_content)

if st.button("Generate", type="primary"):
    dumped_config = dump_config(generate_config())
    st.json(dumped_config)
    st.download_button(
        "Download config",
        data=json.dumps(dumped_config, ensure_ascii=False, indent=4),
        file_name="likert_config.json",
        mime="application/json",
    )
