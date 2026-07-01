#!/usr/bin/env python3
"""
内容模型验证工具 -- validate_content_model.py

用途：在发布内容之前，用平台上已有的内容对照验证你的内容模型假设。
本工具不采集任何数据，所有数据由用户手动输入。

用法：
  python validate_content_model.py

输入模式：
  1. 交互模式：逐条输入观察数据
  2. CSV 模式：提供 CSV 文件路径（--file data.csv）

输出：
  - 模型假设的置信度评估
  - 支持/不支持的具体证据
  - 是否建议进入发帖测试阶段

数据格式（CSV）：
  keyword,search_count,high_interaction_count,avg_likes,avg_collects,avg_comments,note
  职场效率,5000,120,350,85,42,"教程类为主"
"""

import os
import csv
import sys
import json
import math
from dataclasses import dataclass, field, asdict
from typing import List, Optional


# ─── 数据结构 ───────────────────────────────────────────────────────────────

@dataclass
class Observation:
    """一次对照观察的数据"""
    keyword: str               # 搜索关键词
    search_count: int          # 搜索结果数量（粗略）
    high_interaction_count: int  # 高互动笔记数量（点赞>500的）
    avg_likes: float           # 该类笔记平均点赞数
    avg_collects: float        # 平均收藏数
    avg_comments: float        # 平均评论数
    notes: str = ""            # 观察备注


@dataclass
class ModelHypothesis:
    """内容模型假设"""
    value_proposition: str     # 信息价值定位
    target_audience: str       # 目标人群
    content_format: str        # 内容形式
    interaction_design: str    # 互动设计
    sustainability: str        # 可持续性

    def to_predictions(self) -> List[str]:
        """将模型假设转化为可验证预测"""
        # 这是一个简化的预测生成，实际使用时由用户定义具体预测
        return [
            f"'{self.value_proposition}' 方向有稳定的搜索需求",
            f"目标人群 '{self.target_audience}' 对此类内容有互动意愿",
            f"'{self.content_format}' 形式在该赛道中互动率表现良好",
        ]


@dataclass
class ValidationResult:
    """验证结果"""
    hypothesis: str
    confidence: float  # 0.0 ~ 1.0
    evidence_for: List[str] = field(default_factory=list)
    evidence_against: List[str] = field(default_factory=list)
    recommendation: str = ""


# ─── 核心分析逻辑 ───────────────────────────────────────────────────────────

def parse_csv(filepath: str) -> List[Observation]:
    """从 CSV 文件读取观察数据"""
    observations = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            obs = Observation(
                keyword=row['keyword'],
                search_count=int(row['search_count']),
                high_interaction_count=int(row['high_interaction_count']),
                avg_likes=float(row['avg_likes']),
                avg_collects=float(row['avg_collects']),
                avg_comments=float(row['avg_comments']),
                notes=row.get('notes', ''),
            )
            observations.append(obs)
    return observations


def interactive_input() -> List[Observation]:
    """交互模式输入观察数据"""
    print("\n" + "=" * 60)
    print("  内容模型验证工具 -- 交互模式")
    print("  请输入你在平台上观察到的数据")
    print("=" * 60)
    
    observations = []
    while True:
        print(f"\n--- 观察 #{len(observations) + 1} ---")
        keyword = input("搜索关键词: ").strip()
        if not keyword:
            if len(observations) == 0:
                continue
            break
        
        try:
            search_count = int(input("搜索结果数量（约）: ") or "0")
            high_count = int(input("高互动笔记数量（点赞>500）: ") or "0")
            avg_likes = float(input("平均点赞数: ") or "0")
            avg_collects = float(input("平均收藏数: ") or "0")
            avg_comments = float(input("平均评论数: ") or "0")
        except ValueError:
            print("  输入格式错误，请重新输入")
            continue
        
        notes = input("备注（可选）: ").strip()
        
        observations.append(Observation(
            keyword=keyword,
            search_count=search_count,
            high_interaction_count=high_count,
            avg_likes=avg_likes,
            avg_collects=avg_collects,
            avg_comments=avg_comments,
            notes=notes,
        ))
        
        more = input("\n继续添加观察？(y/n): ").strip().lower()
        if more != 'y':
            break
    
    return observations


def compute_platform_benchmarks(
    observations: List[Observation]
) -> dict:
    """计算平台同类内容的基准线"""
    if not observations:
        return {}
    
    total = len(observations)
    return {
        "avg_likes": sum(o.avg_likes for o in observations) / total,
        "avg_collects": sum(o.avg_collects for o in observations) / total,
        "avg_comments": sum(o.avg_comments for o in observations) / total,
        "avg_search_count": sum(o.search_count for o in observations) / total,
        "avg_interaction_rate": sum(
            (o.avg_likes + o.avg_collects * 3 + o.avg_comments * 2) / max(o.search_count, 1)
            for o in observations
        ) / total,
        "collect_to_like_ratio": sum(
            o.avg_collects / max(o.avg_likes, 1) for o in observations
        ) / total,
        "total_observations": total,
    }


def assess_demand_strength(
    observations: List[Observation],
    benchmarks: dict
) -> ValidationResult:
    """评估需求强度（含样本量惩罚）"""
    if not observations:
        return ValidationResult(
            hypothesis="该方向是否存在稳定需求",
            confidence=0.0,
            recommendation="没有数据，无法评估。建议先在小红书搜索相关关键词。"
        )
    
    n = len(observations)
    
    # 样本量惩罚因子：样本越少，置信度越不可靠
    # n >= 8 时惩罚因子 = 1.0（无惩罚）
    # n = 3 时惩罚因子 ≈ 0.6
    # n = 1 时惩罚因子 ≈ 0.3
    sample_penalty = min(n / 8, 1.0) if n > 0 else 0.0
    
    # 信号 1: 搜索结果数量（粗略需求规模）
    search_scores = []
    for o in observations:
        if o.search_count > 10000:
            search_scores.append(1.0)    # 大量内容 -> 需求确定存在
        elif o.search_count > 1000:
            search_scores.append(0.8)    # 中等 -> 需求存在
        elif o.search_count > 100:
            search_scores.append(0.5)    # 少量 -> 可能有需求
        else:
            search_scores.append(0.2)    # 极少 -> 需求不确定或不存在
    
    avg_search_score = sum(search_scores) / n
    
    # 信号 2: 高互动内容比例（用户是否愿意互动）
    total_search = sum(o.search_count for o in observations)
    interaction_ratio = sum(o.high_interaction_count for o in observations) / max(total_search, 1)
    interaction_score = min(interaction_ratio * 100, 1.0)  # 归一化
    
    # 信号 3: 收藏/点赞比（内容"有用"程度）
    cl_ratio = benchmarks.get("collect_to_like_ratio", 0)
    # 小红书优质内容的收藏/点赞比通常在 0.3~0.7+
    if cl_ratio > 0.5:
        cl_score = 1.0
    elif cl_ratio > 0.3:
        cl_score = 0.8
    elif cl_ratio > 0.15:
        cl_score = 0.5
    else:
        cl_score = 0.3
    
    # 原始综合置信度
    raw_confidence = avg_search_score * 0.4 + interaction_score * 0.35 + cl_score * 0.25
    
    # 应用样本量惩罚
    confidence = raw_confidence * sample_penalty
    confidence = round(min(max(confidence, 0.0), 1.0), 2)
    
    evidence = []
    
    if n < 5:
        evidence.append(f"样本量仅 {n} 条，置信度已打折（{sample_penalty:.0%}）。建议至少采集 5 条以上。")
    
    if avg_search_score >= 0.8:
        evidence.append(f"搜索量大（avg {benchmarks['avg_search_count']:.0f}），说明有稳定需求")
    elif avg_search_score >= 0.5:
        evidence.append(f"搜索量中等（avg {benchmarks['avg_search_count']:.0f}），需求存在但可能小众")
    else:
        evidence.append(f"搜索量较小（avg {benchmarks['avg_search_count']:.0f}），需确认需求是否存在")
    
    if interaction_score >= 0.6:
        evidence.append(f"高互动内容比例高（{interaction_ratio:.4f}），用户互动意愿强")
    else:
        evidence.append(f"高互动内容比例偏低（{interaction_ratio:.4f}），可能需要差异化")
    
    if cl_ratio >= 0.3:
        evidence.append(f"收藏/点赞比 {cl_ratio:.2f}，内容'有用性'受到认可")
    else:
        evidence.append(f"收藏/点赞比 {cl_ratio:.2f}，偏低，内容偏向「看完即走」类型")
    
    if confidence >= 0.6:
        recommendation = "[OK] 需求强度置信度较高，建议进入下一步详细分析。"
    elif confidence >= 0.35:
        recommendation = "[WARN] 需求存在但不确定强度，建议补充更多观察数据，或尝试差异化切入。"
    else:
        recommendation = "[FAIL] 当前数据不支持该方向有明确需求，建议调整模型假设。"
    
    return ValidationResult(
        hypothesis="该方向是否存在稳定需求",
        confidence=confidence,
        evidence_for=evidence,
        recommendation=recommendation,
    )


def assess_content_pattern(
    observations: List[Observation],
    user_format: str
) -> ValidationResult:
    """评估内容形式是否适合该赛道"""
    if not observations:
        return ValidationResult(
            hypothesis=f"内容形式 '{user_format}' 是否适合该赛道",
            confidence=0.0,
            recommendation="没有数据，无法评估。"
        )
    
    # 这是一个简化的评估：观察高互动内容中某种形式的占比
    # 实际使用时，用户需要更详细地分类观察
    format_keywords = {
        "清单体": ["清单", "TOP", "个", "步骤", "必备"],
        "故事体": ["分享", "经历", "我是怎么", "从...到"],
        "教程": ["教程", "教", "怎么", "攻略"],
        "测评": ["测评", "实测", "对比", "vs", "试"],
    }
    
    # 通过备注和关键词粗略判断
    # 这里简化处理，主要依赖用户输入的 notes
    format_hints = 0
    for o in observations:
        for fmt, keywords in format_keywords.items():
            if any(kw in o.notes for kw in keywords):
                format_hints += 1
                break
    
    # 如果没有明显的形式线索，给中等置信度
    if format_hints == 0:
        return ValidationResult(
            hypothesis=f"内容形式 '{user_format}' 是否适合该赛道",
            confidence=0.5,
            evidence_for=["未从观察数据中识别出明确的单一形式主导，你的形式选择有探索空间。"],
            recommendation="建议在备注中记录高互动内容的形式特征，或直接运行设计实验脚本设计测试。"
        )
    
    ratio = format_hints / len(observations)
    confidence = min(ratio, 1.0)
    
    return ValidationResult(
        hypothesis=f"内容形式 '{user_format}' 是否适合该赛道",
        confidence=round(confidence, 2),
        evidence_for=[f"在 {format_hints}/{len(observations)} 个观察中识别出该形式的痕迹"],
        recommendation=f"形式匹配度 {confidence:.0%}，建议通过 A/B 测试进一步验证。"
    )


def print_report(
    observations: List[Observation],
    benchmarks: dict,
    results: List[ValidationResult]
):
    """打印验证报告"""
    print("\n" + "=" * 60)
    print("  内容模型验证报告")
    print("=" * 60)
    
    # 基础统计
    print(f"\n[数据] 基准数据")
    print(f"  观察样本数: {len(observations)}")
    print(f"  同类内容平均互动:")
    print(f"    - 点赞: {benchmarks['avg_likes']:.0f}")
    print(f"    - 收藏: {benchmarks['avg_collects']:.0f}")
    print(f"    - 评论: {benchmarks['avg_comments']:.0f}")
    print(f"  收藏/点赞比: {benchmarks['collect_to_like_ratio']:.2f}")
    
    # 验证结果
    print(f"\n[结果] 模型假设验证结果")
    print("-" * 60)
    
    all_confident = True
    for r in results:
        icon = "[OK]" if r.confidence >= 0.6 else ("[WARN]" if r.confidence >= 0.35 else "[FAIL]")
        print(f"\n  {icon} {r.hypothesis}")
        print(f"     置信度: {r.confidence:.0%}")
        if r.evidence_for:
            for e in r.evidence_for:
                print(f"     📌 {e}")
        if r.evidence_against:
            for e in r.evidence_against:
                print(f"     [WARN]  {e}")
        print(f"     建议: {r.recommendation}")
        
        if r.confidence < 0.35:
            all_confident = False
    
    # 综合建议
    print("\n" + "=" * 60)
    print("  🏁 综合判断")
    print("=" * 60)
    
    if all_confident and all(r.confidence >= 0.6 for r in results):
        print("""
  [OK] 你的内容模型假设通过了对照验证。
  
  建议行动：
  1. 进入发帖测试阶段（使用 design_experiment.py 设计实验）
  2. 保持模型的核心定位不变
  3. 在发帖测试中精确测试变量
  
  注意：对照验证通过不代表内容一定能火，但它确认了
  你的方向上有需求基础，值得投入下一步验证。
""")
    elif any(r.confidence >= 0.6 for r in results):
        print("""
  [WARN] 部分假设得到支持，部分存在不确定性。
  
  建议行动：
  1. 重新审视置信度低的假设部分
  2. 补充更多观察数据或调整假设
  3. 确认差异化空间后再进入发帖测试
""")
    else:
        print("""
  [FAIL] 当前模型假设未得到充分支持。
  
  建议行动：
  1. 回到第一性原理，重新思考信息价值定位
  2. 换一个方向或人群重新建立假设
  3. 避免在未验证的假设上投入发帖资源
""")


# ─── 快速验证模式 ──────────────────────────────────────────────────────────

def run_quick_validation(output_dir: str = "."):
    """
    快速验证模式：通过 5 个定性问题评估方向可行性。
    不需要精确数字，适合快速筛选方向。
    """
    import json
    
    print("\n" + "=" * 60)
    print("  快速验证模式")
    print("  回答以下 5 个问题，快速评估方向可行性")
    print("=" * 60)
    
    questions = [
        {
            "q": "1. 在小红书搜索你的核心关键词，搜索结果多吗？",
            "opts": [
                ("很多（>1000条结果）", 1.0),
                ("有一些（100-1000条）", 0.7),
                ("很少（<100条）", 0.3),
                ("几乎没有", 0.0),
            ],
        },
        {
            "q": "2. 搜索结果中，有没有点赞 >500 的高互动笔记？",
            "opts": [
                ("很多（>50篇）", 1.0),
                ("有一些（10-50篇）", 0.7),
                ("偶尔有几篇", 0.4),
                ("几乎没有", 0.0),
            ],
        },
        {
            "q": "3. 这些高互动笔记的**收藏数**相对于点赞数如何？（收藏/点赞比高 = 内容有用性强）",
            "opts": [
                ("收藏很多（比点赞的1/3还多）", 1.0),
                ("收藏有一些（大约点赞的1/5）", 0.7),
                ("收藏很少（远少于点赞）", 0.3),
                ("基本没有收藏", 0.0),
            ],
        },
        {
            "q": "4. 你的内容方向和这些高互动笔记相比，有没有明显的差异化空间？",
            "opts": [
                ("有，我能做得更深入/更独特", 1.0),
                ("有一些不同角度", 0.7),
                ("差不多，没什么区别", 0.3),
                ("比别人的还差", 0.0),
            ],
        },
        {
            "q": "5. 你对这个方向的知识/经验储备如何？",
            "opts": [
                ("很丰富，有独特的经验", 1.0),
                ("有一些了解和实践", 0.7),
                ("基本了解，需要现学", 0.3),
                ("完全不懂", 0.0),
            ],
        },
    ]
    
    scores = []
    for q in questions:
        print(f"\n{q['q']}")
        for i, (opt, score) in enumerate(q["opts"], 1):
            print(f"  {i}. {opt}")
        while True:
            try:
                choice = int(input("请选择 (1-4): ").strip())
                if 1 <= choice <= 4:
                    scores.append(q["opts"][choice - 1][1])
                    break
                else:
                    print("请输入 1-4")
            except ValueError:
                print("请输入数字")
    
    # 计算得分（无样本量惩罚，因为定性问题已经包含了判断）
    raw_score = sum(scores) / len(scores)
    
    # 但问题 4（差异化）+ 问题 5（自身储备）的权重略高
    weighted_score = (scores[0] + scores[1] + scores[2] + scores[3] * 1.5 + scores[4] * 1.5) / 5.5
    confidence = round(min(max(weighted_score, 0.0), 1.0), 2)
    
    print("\n" + "=" * 60)
    print("  快速验证结果")
    print("=" * 60)
    print(f"\n  综合评分: {confidence:.0%}")
    print()
    
    if confidence >= 0.6:
        print("  [OK] 这个方向看起来有潜力！")
        print("  建议：进入阶段 2 构建完整内容模型，再进入详细对照验证。")
    elif confidence >= 0.35:
        print("  [WARN] 方向可行但有一定风险。")
        print("  建议：优化差异化定位后再次验证，或进入详细对照验证获取更精确的数据。")
    else:
        print("  [FAIL] 当前方向不太乐观。")
        print("  建议：换个方向或重新思考信息价值定位。")
    
    print()
    print("  [提示] 快速验证不能替代详细对照验证。确认方向后，")
    print("  建议再跑一次完整模式（不加 --quick）获取精确数据。")
    
    # 保存结果
    result = {
        "mode": "quick",
        "scores": {
            "search_volume": scores[0],
            "high_interaction": scores[1],
            "collect_ratio": scores[2],
            "differentiation": scores[3],
            "knowledge_reserve": scores[4],
        },
        "confidence": confidence,
    }
    output_path = os.path.join(output_dir, ".quick_validate.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[文件] 快速验证结果已保存至 {output_path}")


# ─── 主入口 ─────────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="内容模型验证工具 ---- 发帖前用平台已有内容验证你的模型假设"
    )
    parser.add_argument(
        "--file", "-f",
        help="CSV 数据文件路径（如果不提供则进入交互模式）"
    )
    parser.add_argument(
        "--format", "-fmt",
        default="",
        help="你的内容模型中的内容形式（如：清单体、故事体、教程）"
    )
    parser.add_argument(
        "--output-dir", "-d",
        default=".",
        help="输出目录（默认当前工作目录）。数据文件写入此目录而非 skill 目录，避免 skill 目录只读的问题。"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="快速验证模式：通过 5 个定性问题评估方向可行性，无需精确数据采集"
    )
    
    args = parser.parse_args()
    output_dir = args.output_dir
    
    if args.quick:
        run_quick_validation(output_dir)
        return
    
    # 1. 获取观察数据
    if args.file:
        try:
            observations = parse_csv(args.file)
            print(f"从 {args.file} 读取了 {len(observations)} 条观察数据")
        except Exception as e:
            print(f"读取文件失败: {e}")
            return
    else:
        # 先询问模型假设
        print("\n请先描述你的内容模型假设（可直接回车跳过，后续仍可分析）：")
        value_prop = input("信息价值定位: ").strip()
        audience = input("目标人群: ").strip()
        content_format = input("内容形式: ").strip() or args.format
        
        observations = interactive_input()
        
        if not observations:
            print("\n没有输入数据，退出。")
            return
    
    if len(observations) < 2:
        print("\n[WARN] 观察数据太少（<2条），结果可能不可靠。建议至少采集 5 条以上。")
    
    # 2. 计算基准线
    benchmarks = compute_platform_benchmarks(observations)
    
    # 3. 逐项验证
    results = []
    
    # 需求强度
    results.append(assess_demand_strength(observations, benchmarks))
    
    # 内容形式
    fmt = args.format or (content_format if 'content_format' in dir() else "")
    if fmt:
        results.append(assess_content_pattern(observations, fmt))
    
    # 4. 输出报告
    print_report(observations, benchmarks, results)
    
    # 5. JSON 输出
    output_path = os.path.join(output_dir, ".validate_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[文件] 原始报告已保存至 {output_path}")


if __name__ == "__main__":
    main()
