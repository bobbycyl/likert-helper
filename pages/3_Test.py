import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from openai import APIError, OpenAI

from likert import LikertConfig, compute_likert
from likert.model import dump_config
from stutils.stutils import LikertValueError, clean_cache, select_scale


@st.cache_resource
def get_openai_client():
    return OpenAI(
        api_key=st.secrets.openai.api_key,
        base_url=st.secrets.openai.base_url,
    )


if "test_form_submitted" not in st.session_state:
    st.session_state.test_form_submitted = False
if "test_scale" not in st.session_state:
    st.session_state.test_scale = None
if "test_scores" not in st.session_state:
    st.session_state.test_scores = {}
if "test_cur_iid" not in st.session_state:
    st.session_state.test_cur_iid = 1
if "test_scale_config" not in st.session_state:
    st.session_state.test_scale_config = None
if "test_item_content_list" not in st.session_state:
    st.session_state.test_item_content_list = []
if "test_version" not in st.session_state:
    st.session_state.test_version = 1


def start():
    clean_cache("test_answer_")
    st.session_state.test_scores = {}
    st.session_state.test_cur_iid = 1
    st.session_state.test_form_submitted = False
    st.session_state.test_version += 1


with st.form("test_starter"):
    try:
        scale_path = select_scale()
        scale_ext = os.path.splitext(scale_path)[1]
        st.session_state.test_scale_config = (
            LikertConfig.from_json(scale_path)
            if scale_ext == ".json"
            else LikertConfig.from_toml(scale_path)
        )
        with open(os.path.splitext(scale_path)[0] + ".txt", encoding="utf-8") as fi:
            st.session_state.test_item_content_list = [line.strip() for line in fi]
    except LikertValueError:
        st.error("please select a valid scale")

    st.form_submit_button("Start", on_click=start)

if not st.session_state.test_scale_config:
    st.stop()

if len(st.session_state.test_scale_config.item_map) != len(
    st.session_state.test_item_content_list,
):
    st.error("The number of items not match.")
    st.stop()

_fig_range_min = min(st.session_state.test_scale_config.levels_labels.keys())


def record_answer():
    st.session_state.test_scores[st.session_state.test_cur_iid] = st.session_state.get(
        "test_answer_%d_%d"
        % (st.session_state.test_version, st.session_state.test_cur_iid),
        _fig_range_min,
    )


def go_prev():
    record_answer()
    st.session_state.test_cur_iid -= 1


def go_next():
    record_answer()
    st.session_state.test_cur_iid += 1


def show_result():
    record_answer()

    st.session_state.test_form_submitted = True

    # 结果展示
    if len(st.session_state.test_scores) != len(
        st.session_state.test_item_content_list,
    ):
        st.warning("Please answer all questions.")
        return

    system_prompt = """你是一位专业的量表评估师。

解读要求：
- 基于量表原始得分和各维度得分，给出客观的描述、评价与建议
- 语言专业且易懂，避免过度解读
- 明确说明局限性：仅供参考，不构成诊断
"""

    df = (
        pd.DataFrame(dict(sorted(st.session_state.test_scores.items())), index=[0])
        .reset_index()
        .rename(columns={"index": "User"})
    )

    # 合并题干与原始得分到一张表里，方便展示
    df_readable = pd.DataFrame(
        {
            "Item": st.session_state.test_item_content_list,
            "Score": df.iloc[0, 1:].values,
        },
    )
    table_readable = df_readable.to_markdown(index=False)
    st.markdown(table_readable)

    res = compute_likert(df, st.session_state.test_scale_config).drop("User", axis=1)
    # show as markdown, one line per column
    res_str = ""
    col = res.columns
    for i in range(len(col)):
        res_str += "**%s**: %s\n\n" % (col[i], res.iat[0, i])
    st.markdown(res_str)

    user_prompt = f"""# 用户 {os.path.splitext(st.session_state.test_scale or "<未定义>")[0]} 量表测评结果

## 用户基本信息
- 年龄: {st.session_state.test_age}
- 性别: {st.session_state.test_gender}

## 量表题项与原始得分

{table_readable}

## 量表维度得分

{res_str}

## 量表配置信息

```json
{json.dumps(dump_config(st.session_state.test_scale_config), ensure_ascii=False)}
```

## 量表评估结果
"""

    # 绘制蛛网图
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=list(res.iloc[0].values) + [res.iat[0, 0]],
            theta=list(res.columns) + [res.columns[0]],
            fill="toself",
            line={"width": 2},
            marker={"size": 6},
        ),
    )

    # 如果有 sum 组，则无法绘制（sum * weight 会导致坐标轴严重膨胀，非标准 Likert 支持范畴）
    has_sum_group = False
    max_group_item_len = 1
    for grp in st.session_state.test_scale_config.groups:
        if grp.aggregate == "sum":
            has_sum_group = True
            if (group_item_len := len(grp.items)) > max_group_item_len:
                max_group_item_len = group_item_len

    _fig_range_max = max(st.session_state.test_scale_config.levels_labels.keys())

    if not has_sum_group:
        fig.update_layout(
            polar={
                "radialaxis": {
                    "visible": True,
                    "range": [_fig_range_min, _fig_range_max],  # 评分范围
                    "tickfont": {"size": 12},
                },
                "angularaxis": {"tickfont": {"size": 14, "color": "black"}},
            },
            title=os.path.splitext(st.session_state.test_scale or "unnamed")[0],
        )

        st.plotly_chart(fig, width="stretch")

    # check access code for AI service
    access_codes = st.secrets.openai.get("allowed", [])
    if st.session_state.test_access_code not in access_codes:
        return

    try:
        stream = get_openai_client().chat.completions.create(
            model=st.secrets.openai.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            stream=True,
        )
        with st.container(border=True):
            st.write_stream(stream)
            st.caption(
                "Notes: AI generated content is for reference only, not for diagnosis.",
            )
    except APIError as e:
        st.error("OpenAI API error.")
        print(e)
    except Exception as e:
        st.error("Unexpected Error: %s" % e)


# 基本信息填写
st.text_input(
    "Access Code", key="test_access_code", disabled=st.session_state.test_form_submitted
)
col_age, col_gender = st.columns(2)
with col_age:
    st.number_input(
        "Age",
        min_value=0,
        max_value=200,
        step=1,
        key="test_age",
        disabled=st.session_state.test_form_submitted,
        width="stretch",
    )
with col_gender:
    st.segmented_control(
        "Gender",
        ["Male", "Female"],
        key="test_gender",
        disabled=st.session_state.test_form_submitted,
        width="stretch",
    )

# 题目显示
with st.container(height=300, border=False):
    st.text(
        "Question %d\n%s"
        % (
            st.session_state.test_cur_iid,
            st.session_state.test_item_content_list[st.session_state.test_cur_iid - 1],
        ),
    )

# 答题区域，需还原已选择题项答案
st.select_slider(
    "Answer",
    list(st.session_state.test_scale_config.levels_labels.keys()),
    value=st.session_state.test_scores.get(
        st.session_state.test_cur_iid,
        _fig_range_min,
    ),
    key="test_answer_%d_%d"
    % (st.session_state.test_version, st.session_state.test_cur_iid),
    format_func=lambda x: st.session_state.test_scale_config.levels_labels[x],
    on_change=record_answer,
    disabled=st.session_state.test_form_submitted,
)

# 上一题、下一题按钮
col_prev, _col_blank, col_next = st.columns(3)
with col_prev:
    st.button(
        "Previous",
        disabled=st.session_state.test_form_submitted
        or (st.session_state.test_cur_iid <= 1),
        on_click=go_prev,
        width="stretch",
        icon=":material/arrow_left:",
    )
with col_next:
    st.button(
        "Next",
        disabled=st.session_state.test_form_submitted
        or (
            st.session_state.test_cur_iid
            >= len(st.session_state.test_item_content_list)
        ),
        on_click=go_next,
        width="stretch",
        icon=":material/arrow_right:",
        icon_position="right",
    )
    if st.session_state.test_cur_iid == len(st.session_state.test_item_content_list):
        st.button(
            "Submit",
            on_click=show_result,
            width="stretch",
            disabled=st.session_state.test_form_submitted,
        )

# 答题状态展示
with st.container(horizontal=True, gap="xxsmall"):
    for i in range(1, len(st.session_state.test_item_content_list) + 1):
        if i == st.session_state.test_cur_iid:
            st.badge("%d" % i, width=40)
        elif i in st.session_state.test_scores:
            st.badge("%d" % i, width=40, color="green")
        else:
            st.badge("%d" % i, width=40, color="orange")
