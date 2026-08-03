# Likert Helper

基于 Streamlit 的李克特（Likert）量表工具，提供三个功能：

- **量表配置生成器**：在界面上交互式地创建量表配置
- **批量计分计算器**：上传包含若干用户的单量表答题数据，按量表配置自动计算各维度得分
- **在线测评**：按量表逐题作答，在线查看各维度得分与蛛网图，生成 AI 结果解读

## 快速开始

### 1. 安装依赖

需要 Python 3.12+。

```bash
pip install -r requirements.txt
```

### 2. 配置

在线测评页的 AI 解读功能需要 OpenAI 兼容接口的 API Key。参考 `.streamlit/secrets.example.toml`，创建 `.streamlit/secrets.toml`：

### 3. 运行

```bash
streamlit run app.py
```

## 使用说明

### 页面一：Generator（配置生成器）

逐行输入题目内容与维度分组名，设置分级数量后，可对每道题配置：

- **Reverse**：是否反向计分（勾选后该题得分会反转）
- **Weight**：题目权重
- **Group**：该题所属的维度分组

点击 **Generate** 可预览并下载生成的 JSON 配置，下载后可放入 `scales/` 目录使用。

> 注意：该页面目前固定使用均值聚合，且暂不支持缺失值阈值与分数等级（score_bands）设置，如需这些特性请直接编辑配置文件。

### 页面二：Calculator（计算器）

1. 在 `scales/` 目录中已放置配置（TOML 或 JSON），页面下拉框选择量表
2. 上传答题数据文件（页面仅支持 CSV）
3. 页面自动计算并展示每个样本各维度的得分

数据文件约定：第 0 列为样本标识（如 User ID），其余列位置分别对应题号

### 页面三：Test（在线测评）

1. 选择一个量表（需要 `scales/` 下存在同名 `.txt` 文件，每行一道题，作为题干展示）
2. 填写年龄、性别等基本信息，点击 **Start** 逐题作答
3. 全部答完提交后，展示各维度得分、蛛网图，并生成 AI 结果解读

## 量表配置格式

配置文件放在 `scales/` 目录，支持 TOML 与 JSON 两种格式。以 TOML 为例：

```toml
[scale.levels_labels]
1 = "完全不符合"
2 = "不符合"
3 = "不确定"
4 = "符合"
5 = "完全符合"

[items]
reverse = [2, 6]              # 反向计分的题号列表

[items.weights]               # 可选：自定义权重，未列出的题默认权重 1.0

[groups."专业知识"]
items = [1, 2, 3, 4, 5, 6]
aggregate = "mean"            # 聚合方式：mean 或 sum
missing_threshold = 0.0       # 缺失比例上限，超过则该样本此维度记为缺失（默认 0.5）

[groups."核心技能"]
items = [7, 8, 9]
aggregate = "mean"
missing_threshold = 0.0
```

可选配置 `score_bands`（分数等级划分），用于给维度得分附加等级标签：

```toml
[[score_bands."专业知识"]]
min = 1.0
max = 2.5
label = "较低"

[[score_bands."专业知识"]]
min = 2.5
max = 5.0
label = "较高"
```

注意：`score_bands` 只影响 `compute_likert(..., apply_band=True)` 的输出（结果中会增加 `维度名_band` 列），Calculator 与 Test 页面默认不使用。

## 开发者指南

### 核心内容

计算逻辑封装在 `likert` 包中，核心函数：

```python
from likert import LikertConfig, compute_likert

# 加载配置（支持 TOML / JSON 文件路径）
config = LikertConfig.from_toml("scales/CBF-PI-B.toml")

# 计算得分：file 支持文件路径、BytesIO 或 DataFrame
df = compute_likert("raw_data.csv", config)

# 如需附加分数等级列
df = compute_likert("raw_data.csv", config, apply_band=True)
```

主要数据结构（`likert/model.py`）：

- `LikertConfig`：量表配置，包含分级标签 `levels_labels`、维度分组 `groups`、可选 `score_bands`
- `GroupConfig`：维度分组，包含题项 `items`、聚合方式 `aggregate`（mean/sum）、缺失阈值 `missing_threshold`
- `ItemConfig`：题项，包含题号 `id`、是否反向 `reverse`、权重 `weight`

### 新增一个量表

1. 在 `scales/` 下新建 `你的量表.toml`（或 `.json`）配置文件
2. 如需在线测评，再新建同名的 `你的量表.txt`，每行写一道题
3. 重启应用后，Calculator 与 Test 页面即可选择该量表

## 已知限制

- Generator 页面暂不支持 `aggregate`、`missing_threshold`、`score_bands` 设置，生成的配置固定为均值聚合、缺失阈值 0
- Test 页面的蛛网图仅适用于 `mean` 聚合的维度，含 `sum` 维度时不会绘制蛛网图
- AI 解读仅对 OpenAI 兼容接口生效，需在 `.streamlit/secrets.toml` 中配置
