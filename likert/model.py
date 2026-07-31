import json
from dataclasses import dataclass, field
from typing import Literal, Optional

import tomllib

ITEM_DEFAULT_REVERSE = False
ITEM_DEFAULT_WEIGHT = 1.0
GROUP_DEFAULT_AGGREGATE = "mean"
GROUP_DEFAULT_MISSING_THRESHOLD = 0.5


@dataclass
class ItemConfig:
    """题项配置"""

    id: int  # 题目编号
    reverse: bool = ITEM_DEFAULT_REVERSE  # 是否反向编码（默认否）
    weight: float = ITEM_DEFAULT_WEIGHT  # 权重（默认等权）


@dataclass
class GroupConfig:
    """特征分组配置"""

    name: str  # 特征分组名
    items: list[ItemConfig]  # 特征分组题项列表
    aggregate: Literal["mean", "sum"] = GROUP_DEFAULT_AGGREGATE  # 聚合方式（默认 mean）
    missing_threshold: float = GROUP_DEFAULT_MISSING_THRESHOLD  # 允许的缺失比例上限，超过则记为 NaN（默认 0.5，如需严格模式，请设置为 0）


type Bands = list[tuple[float, float, str]]  # [(low, high, label), ...]


class LikertValueError(ValueError):
    pass


@dataclass
class LikertConfig:
    """李克特量表配置"""

    levels_labels: dict[int, str]  # 分级对应表达
    groups: list[GroupConfig]
    item_map: dict[int, ItemConfig] = field(default_factory=dict)
    score_bands: Optional[dict[str, Bands]] = None

    def __post_init__(self):
        self.item_map = {it.id: it for grp in self.groups for it in grp.items}

    @classmethod
    def from_toml(cls, path: str):
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        return parse_config(raw)

    @classmethod
    def from_json(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return parse_config(raw)

    def to_json(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            toml_dict = dump_config(self)
            json.dump(toml_dict, f, ensure_ascii=False, indent=4)


def parse_config(toml_dict: dict) -> LikertConfig:
    """从 TOML 字典解析李克特量表配置"""
    # 基本量表设置
    scale_section = toml_dict["scale"]
    levels_labels: dict[int, str] = {
        int(k): v for k, v in scale_section["levels_labels"].items()
    }

    # 题项全局设置
    items_section = toml_dict["items"]
    global_reverse_set = set(int(x) for x in items_section.get("reverse", []))
    global_weights = {
        int(k): float(v) for k, v in items_section.get("weights", {}).items()
    }

    # 特征分组设置
    groups: list[GroupConfig] = []
    groups_section = toml_dict["groups"]
    for grp_name, grp_dict in groups_section.items():
        item_ids = [int(x) for x in grp_dict["items"]]
        aggregate = grp_dict.get(
            "aggregate", GROUP_DEFAULT_AGGREGATE
        )  # 与 GroupConfig 默认值保持一致
        missing_threshold = grp_dict.get(
            "missing_threshold", GROUP_DEFAULT_MISSING_THRESHOLD
        )  # 与 GroupConfig 默认值保持一致

        grp_items = []
        for iid in item_ids:
            grp_items.append(
                ItemConfig(
                    id=iid,
                    reverse=iid in global_reverse_set,
                    weight=global_weights.get(
                        iid, ITEM_DEFAULT_WEIGHT
                    ),  # 与 ItemConfig 默认值保持一致
                )
            )

        groups.append(
            GroupConfig(
                name=grp_name,
                items=grp_items,
                aggregate=aggregate,
                missing_threshold=missing_threshold,
            )
        )

    # Optional: 分数等级划分
    score_bands: Optional[dict[str, Bands]] = None
    bands_section = toml_dict.get("score_bands", None)  # 这是一个 TOML 表数组
    if bands_section is not None:
        score_bands = {}
        for grp_name, band_list in bands_section.items():
            # min, max, label
            parsed_bands: Bands = []
            for band in band_list:
                parsed_bands.append(
                    (float(band["min"]), float(band["max"]), str(band["label"]))
                )
            score_bands[grp_name] = sorted(parsed_bands, key=lambda x: x[0])

    return LikertConfig(
        levels_labels=levels_labels,
        groups=groups,
        score_bands=score_bands,
    )


def dump_config(config: LikertConfig) -> dict:
    toml_dict = {
        "scale": {
            "levels_labels": {str(k): v for k, v in config.levels_labels.items()},
        },
        "items": {
            "reverse": sorted(
                [it.id for grp in config.groups for it in grp.items if it.reverse]
            ),
            "weights": {
                str(it.id): it.weight
                for grp in config.groups
                for it in grp.items
                if it.weight != ITEM_DEFAULT_WEIGHT
            },
        },
        "groups": {
            grp.name: {
                "items": [it.id for it in grp.items],
                "aggregate": grp.aggregate,
                "missing_threshold": grp.missing_threshold,
            }
            for grp in config.groups
        },
    }

    if config.score_bands:
        bands_section = {}
        for grp_name, bands in config.score_bands.items():
            band_list = []
            for band in bands:
                band_list.append({"min": band[0], "max": band[1], "label": band[2]})
            bands_section[grp_name] = band_list
        toml_dict["score_bands"] = bands_section

    return toml_dict
