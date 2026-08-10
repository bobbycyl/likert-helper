import math
import os
from io import BytesIO

import numpy as np
import pandas as pd

from .model import Bands, LikertConfig


def _reverse_code(value: float, min_level: int, max_level: int) -> float:
    """反向编码"""
    if math.isnan(value):  # NaN
        return value
    return max_level - value + min_level


def _apply_band(score: float, bands: Bands) -> str:
    """根据分数返回等级标签"""
    if math.isnan(score):  # NaN
        return ""
    for lo, hi, label in bands:
        if lo <= score <= hi:  # 这里必须使用闭区间
            return label
    return ""


def _read_raw(path: str) -> pd.DataFrame:
    """读取原始结果文件"""
    # Excel / CSV
    ext = os.path.splitext(path)[1]
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(path, engine="calamine")
    if ext == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"不支持的文件格式: {ext}")


def compute_likert(
    file: str | BytesIO | pd.DataFrame,
    config: LikertConfig,
    apply_band: bool = False,
) -> pd.DataFrame:
    """计算李克特量表得分

    :param file: 原始结果，支持文件名、BytesIO 和 DataFrame，约定第 0 列为 User 标识符，题号 = 列位置
    :param config: 量表配置
    :param apply_band: 如果 config 定义了 band，是否在结果中增添对应 group 得分的 band 列（默认不使用）
    :return: 包含样本 ID 和每个 group 的得分，若 apply_band 为 True，则额外包含 group 得分对应的 band 列
    """
    if isinstance(file, str):
        df = _read_raw(file)
    elif isinstance(file, pd.DataFrame):
        df = file.copy()
    else:
        df = pd.read_csv(file)
    levels_labels = config.levels_labels
    _min_lvl = min(levels_labels.keys())
    _max_lvl = max(levels_labels.keys())

    # 第 0 列为样本 ID
    sample_id_col_name = df.columns[0]
    sample_id_series = df[sample_id_col_name]

    # 验证题项数量是否正确
    item_count = 0
    for grp in config.groups:
        for _it in grp.items:
            item_count += 1

    if len(df.columns) - 1 != item_count:
        raise ValueError("题项数量不匹配")

    # 开始计算
    result: dict[str, list[float] | list[str]] = {}

    for grp in config.groups:
        # 取出该组对应的题号（由于列 0 是样本 ID，所以题号与列号对应）
        item_cols = [it.id for it in grp.items]
        subset = df.iloc[:, item_cols].copy()

        # 反向编码
        for it in grp.items:
            if it.reverse:
                col_idx = item_cols.index(it.id)
                subset.iloc[:, col_idx] = subset.iloc[:, col_idx].apply(
                    lambda v, mi=_min_lvl, ma=_max_lvl: _reverse_code(v, mi, ma),
                )

        # 权重向量
        weights = np.array([it.weight for it in grp.items])

        # 逐行聚合
        scores: list[float] = []
        for idx in range(len(subset)):
            row = pd.Series(pd.to_numeric(subset.iloc[idx], errors="coerce")).values
            mask = ~np.isnan(row)
            n_valid = mask.sum()
            n_total = len(row)

            if n_total == 0 or (1 - n_valid / n_total) > grp.missing_threshold:
                # 缺失值过多，跳过该样本
                scores.append(np.nan)
                continue

            w = weights[mask]
            s = row[mask]
            if grp.aggregate == "mean":
                score = np.average(s, weights=w) if w.sum() > 0 else np.nan
            elif grp.aggregate == "sum":
                score = float(np.dot(s, w))
            else:
                raise ValueError(f"不支持的聚合方法: {grp.aggregate}")

            scores.append(score)

        # 添加到结果中
        result[grp.name] = scores

        # 标记等级
        if apply_band and config.score_bands and grp.name in config.score_bands:
            result[f"{grp.name}_band"] = [
                _apply_band(score, config.score_bands[grp.name]) for score in scores
            ]

    out_df = pd.DataFrame(result)
    out_df.insert(0, sample_id_col_name, sample_id_series)

    return out_df
