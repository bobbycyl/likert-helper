# Likert Helper

基于 Streamlit 的李克特（Likert）量表工具，提供三个功能：

- **量表配置生成器**：在界面上交互式地创建量表配置
- **批量计分计算器**：上传包含若干用户的单量表答题数据，按量表配置自动计算各维度得分
- **在线测评**：按量表逐题作答，在线查看雷达图与解读报告

## 快速开始

### 1. 安装依赖

需要 Python 3.12+。

```bash
pip install -r requirements.txt
```

### 2. 配置

在线测评页的解读功能需要 OpenAI 兼容接口的 API Key。参考 `.streamlit/secrets.example.toml`，创建 `.streamlit/secrets.toml`：

### 3. 运行

```bash
streamlit run app.py
```

## 使用说明

### 页面一：Generator（配置生成器）

逐行输入题项内容与维度分组名，设置分级数量后，可进行题项配置：

- **Reverse**：是否反向计分
- **Weight**：题项权重
- **Group**：该题所属的维度分组

点击 **Generate** 可预览并下载生成的 JSON 配置，下载后可放入 `scales/` 目录使用。

### 页面二：Calculator（量表计算器）

1. 在 `scales/` 目录中已放置量表配置文件，页面下拉框选择量表
2. 上传答题数据文件（页面仅支持 CSV，likert 包本身支持更多格式）
3. 查看计算后每个样本各维度的得分

数据文件约定：第 0 列为样本标识（如 User ID），其余列位置分别对应题号

### 页面三：Test（在线测评）

1. 选择一个量表（需要 `scales/` 下存在同名 `.txt` 文件，一行一题，作为题干展示）
2. 填写年龄、性别等基本信息，开始作答
3. 全部答完提交后，展示各维度得分、雷达图，若 Access Code 校验通过，生成解读报告

## 量表配置格式

配置文件放在 `scales/` 目录，支持 TOML 与 JSON 两种格式。以 TOML 为例：

```toml
[scale.levels_labels]
1 = "完全不符合"
2 = "基本不符合"
3 = "不确定"
4 = "基本符合"
5 = "完全符合"

[items]
reverse = [2, 6]              # 反向计分的题号列表

[items.weights]               # 可选：自定义权重，未列出的题项默认权重 1.0

[groups."专业知识"]
items = [1, 2, 3, 4, 5]
aggregate = "mean"            # 聚合方式：mean 或 sum
missing_threshold = 0.0       # 缺失比例上限，超过则该样本此维度记为缺失（默认 0.5）

[groups."核心技能"]
items = [6, 7, 8, 9]
aggregate = "mean"
missing_threshold = 0.0
```

可选配置 `score_bands`（分数等级划分），用于给维度得分附加等级标签，例如：

```toml
[[score_bands."专业知识"]]
min = 1.0
max = 2.0
label = "低"

[[score_bands."专业知识"]]
min = 2.0
max = 3.0
label = "较低"

[[score_bands."专业知识"]]
min = 3.0
max = 4.0
label = "较高"

[[score_bands."专业知识"]]
min = 4.0
max = 5.0
label = "高"
```

注意：`score_bands` 只影响 `compute_likert(..., apply_band=True)` 的输出（结果中会增加对应分组的 `<group>_band` 列），Calculator 与 Test 页面默认不使用。

## 开发者指南

### 核心内容

计算逻辑封装在 `likert` 包中，核心函数：

```python
from likert import LikertConfig, compute_likert

# 加载配置（支持 TOML / JSON 文件路径）
config = LikertConfig.from_toml("scales/CBF-PI-B.toml")

# 计算得分：file 支持文件路径、BytesIO 或 DataFrame
df = compute_likert("40_5_32_7.csv", config)
```

主要数据结构（`likert/model.py`）：

- `LikertConfig`：量表配置，包含分级标签 `levels_labels`、维度分组 `groups`、可选 `score_bands`
- `GroupConfig`：维度分组，包含题项 `items`、聚合方式 `aggregate`（mean/sum）、缺失阈值 `missing_threshold`
- `ItemConfig`：题项，包含题号 `id`、是否反向 `reverse`、权重 `weight`

### 新增量表

1. 在 `scales/` 下新建 `你的量表.toml`（或 `.json`）配置文件
2. 如需在线测评，再新建同名的 `你的量表.txt`，一行一题，顺序编写

## 已知限制

- Generator 页面暂不支持 `aggregate`、`missing_threshold`、`score_bands` 设置，生成的配置固定为均值聚合、缺失阈值 0
- Test 页面的雷达图仅适用于 `mean` 聚合的维度，含 `sum` 维度时不会绘制
