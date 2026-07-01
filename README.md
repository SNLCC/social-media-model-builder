# 自媒体内容模型构建器 · Social Media Model Builder

自媒体从来不是追逐热点、迎合潮流，自媒体的本质是构建一个属于自己的运营模型。跑通一个模型=起号成功！

基于第一性原理的自媒体内容模型构建工具。**不追热点、不采集爆款**，而是回归信息供需、人性论和平台分发原理，帮助你构建可复刻的自媒体账号模型。

```text
信息传递效率 = (信息价值 × 信息可接受度) / 信息获取成本
```

—— 所有方法论都从这个公式推导而来。

---

## 与其他工具的区别

| 常见做法 | 本工具的做法 |
|---------|------------|
| 采集爆款内容，模仿热门标题 | 从人性论和平台分发原理推导内容模型 |
| 追热点、追趋势 | 回归六种永恒信息需求（怎么做/选哪个/为什么/跟我一样/新东西/好看的） |
| 大量发帖试错，看哪个数据好 | 先用平台已有内容对照验证（零成本），通过后再精确发帖测试 |
| 依赖自动化采集工具，有风控风险 | 所有数据用户手动输入，不触碰平台反爬机制 |

## 核心工作流

```text
探索定位 → 模型构建 → 对照验证 → 发帖测试 → 信号分析 → 迭代
```

### 快速启动（3 步）

```bash
# Step 1: 定方向 — 5 个定性问题快速评估
python scripts/validate_content_model.py --quick

# Step 2: 建模型 — 构建 4+1 要素内容模型
# 阅读 references/model-building-methodology.md

# Step 3: 快验证 — 手动搜索关键词，输入数据验证
python scripts/validate_content_model.py
```

### 完整工作流

| 阶段 | 做什么 | 用到的资源 |
|------|--------|-----------|
| **1. 探索与定位** | 自我资源盘点、选择信息价值方向、定义目标人群 | `references/first-principles.md`<br>`references/xiaohongshu-platform.md` |
| **2. 模型构建** | 构建 4+1 要素内容模型：信息价值定位 → 目标人群 → 内容形式 → 获取策略 → 互动设计 | `references/model-building-methodology.md` |
| **3. 对照验证** | 不发帖，用平台已有内容验证模型假设 | `scripts/validate_content_model.py` |
| **4. 发帖测试** | 设计精确变量测试，预设信号灯 | `scripts/design_experiment.py` |
| **5. 信号决策** | 分析已发帖数据，止损/加注/观察 | `scripts/analyze_post_signals.py` |

## 4+1 要素模型

从第一性原理公式推导出的内容模型结构：

```text
核心四要素（从信息传递效率公式推导）：
  1. 信息价值定位     → 信息价值
  2. 目标人群画像     → 信息价值的受体
  3. 内容形式体系     → 信息可接受度
  4. 获取策略         → 信息获取成本（标题/封面/开头钩子）

从属要素（从互动概率公式推导）：
  5. 互动设计         → 互动收益 - 互动成本
```

## 项目结构

```text
social-media-model-builder/
├── LICENSE                     # MIT 开源许可
├── README.md
├── SKILL.md                    # 主文档（工作流 + 资源索引）
├── agents/
│   └── openai.yaml             # UI 元数据（可选）
├── scripts/
│   ├── validate_content_model.py   # 对照验证工具
│   ├── design_experiment.py        # 实验设计工具
│   └── analyze_post_signals.py     # 信号分析工具
└── references/
    ├── first-principles.md          # 第一性原理框架
    ├── xiaohongshu-platform.md      # 小红书平台分析
    ├── model-building-methodology.md # 内容模型构建方法论
    └── mvt-framework.md             # 最小可行性验证框架
```

## 使用方式

所有脚本都支持两种输入模式，且**不涉及任何自动化数据采集**：

```bash
# 交互模式：按照提示逐条输入
python scripts/validate_content_model.py

# CSV 模式：准备数据文件批量输入
python scripts/validate_content_model.py --file data.csv

# 快速定性评估模式
python scripts/validate_content_model.py --quick

# 指定输出目录（数据写入你的项目路径，而非 skill 目录）
python scripts/validate_content_model.py --output-dir ./my-records
```

## 平台适配

当前优先适配小红书。第一性原理跨平台通用，其他平台的分析可借助 AI 自身知识补充。

## 许可证

本项目采用 [MIT License](LICENSE)。

---

**商标声明**：小红书及 RED 是行吟信息科技（上海）有限公司的注册商标。本工具提供独立的分析方法论，与小红书及其母公司无任何关联、赞助或背书关系。
