import os
from io import BytesIO

import numpy as np
import pandas as pd

from .model import Bands, LikertConfig


def _reverse_code(value: int | float, min_level: int, max_level: int) -> float:
    """反向编码"""
    if value != value:  # NaN
        return value
    return max_level - value + min_level


def _apply_band(score: float, bands: Bands) -> str:
    """根据分数返回等级标签"""
    if score != score:  # NaN
        return ""
    for lo, hi, label in bands:
        if lo <= score <= hi:  # 这里必须使用闭区间
            return label
    else:
        return ""


def _read_raw(path: str) -> pd.DataFrame:
    """读取原始结果文件"""
    # Excel / CSV
    ext = os.path.splitext(path)[1]
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(path, engine="calamine")
    elif ext == ".csv":
        return pd.read_csv(path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def compute_likert(
    file: str | BytesIO | pd.DataFrame,
    config: LikertConfig,
) -> pd.DataFrame:
    """计算李克特量表得分"""
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
    result = {}

    for grp in config.groups:
        # 取出该组对应的题号（由于列 0 是样本 ID，所以题号与列号对应）
        item_cols = [it.id for it in grp.items]
        subset = df.iloc[:, item_cols].copy()

        # 反向编码
        for it in grp.items:
            if it.reverse:
                col_idx = item_cols.index(it.id)
                subset.iloc[:, col_idx] = subset.iloc[:, col_idx].apply(
                    lambda v, mi=_min_lvl, ma=_max_lvl: _reverse_code(v, mi, ma)
                )

        # 权重向量
        weights = np.array([it.weight for it in grp.items])

        # 逐行聚合
        scores = []
        for idx in range(len(subset)):
            row = pd.to_numeric(subset.iloc[idx], errors="coerce").values
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
        if config.score_bands and grp.name in config.score_bands:
            result[f"{grp.name}_band"] = [
                _apply_band(score, config.score_bands[grp.name]) for score in scores
            ]

    out_df = pd.DataFrame(result)
    out_df.insert(0, sample_id_col_name, sample_id_series)

    return out_df
