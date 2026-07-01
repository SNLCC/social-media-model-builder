#!/usr/bin/env python3
"""
实验设计工具 -- design_experiment.py

用途：设计精确的发帖测试实验，设定变量、信号灯和测试计划。
本工具不执行发帖操作，只提供实验设计方案。

用法：
  python design_experiment.py
  python design_experiment.py --template  # 生成空白实验模板 CSV

输出：
  - 实验设计方案（Markdown 格式）
  - 信号灯定义
  - 测试计划时间线
"""

import sys
import io

# 强制 UTF-8 输出，兼容 Windows PowerShell 等非 UTF-8 终端
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
elif hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import csv
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime, timedelta


# ─── 数据结构 ───────────────────────────────────────────────────────────────

@dataclass
class TestVariable:
    """测试变量"""
    name: str                 # 变量名称（如"标题公式"）
    control: str              # 控制组条件
    treatment: str            # 测试组条件
    notes: str = ""           # 补充说明


@dataclass
class SignalLight:
    """信号灯"""
    type: str                 # "green" / "yellow" / "red"
    metric: str               # 指标（如"点击率"）
    condition: str            # 触发条件（如"连续5篇 > 15%"）
    action: str               # 触发后的行动


@dataclass
class Experiment:
    """实验设计"""
    name: str                 # 实验名称
    hypothesis: str           # 实验假设
    model_assumption: str     # 验证的模型假设
    variables: List[TestVariable] = field(default_factory=list)
    sample_size: int = 5      # 每组最少样本量
    test_duration_days: int = 14  # 测试周期（天）
    signals: List[SignalLight] = field(default_factory=list)
    notes: str = ""


# ─── 信号灯预设 ────────────────────────────────────────────────────────────

DEFAULT_SIGNALS = [
    SignalLight(
        type="green",
        metric="互动率持续上升",
        condition="连续 5 篇互动率递增，且最后一篇高于第一篇 30% 以上",
        action="增加发布频率（从 1 篇/周 -> 2 篇/周），深化该方向"
    ),
    SignalLight(
        type="green",
        metric="收藏率超预期",
        condition="单篇收藏率 > 平台同类 top 25%",
        action="该方向投入更多资源，制作系列内容"
    ),
    SignalLight(
        type="yellow",
        metric="数据波动大",
        condition="单篇数据起伏不定（CV > 50%）",
        action="增加样本量至 10 篇再判断，检查内容一致性"
    ),
    SignalLight(
        type="yellow",
        metric="互动分散",
        condition="没有稳定的互动模式，各篇数据无明显规律",
        action="检查内容模型的一致性，是否每篇都在验证同一个变量"
    ),
    SignalLight(
        type="red",
        metric="点击率低于预期",
        condition="连续 5 篇点击率 < 平台同类中位数",
        action="停止该方向，回到对照验证阶段，重新评估"
    ),
    SignalLight(
        type="red",
        metric="互动率持续走低",
        condition="连续 5 篇互动率递减",
        action="暂停发帖，回阶段一重新验证模型"
    ),
    SignalLight(
        type="red",
        metric="收藏率归零",
        condition="连续 3 篇收藏数为 0",
        action="重新评估信息价值定位，内容可能缺乏'有用性'"
    ),
]


# ─── 交互式实验设计 ────────────────────────────────────────────────────────

def interactive_design() -> Experiment:
    """交互式设计实验"""
    print("\n" + "=" * 60)
    print("  实验设计工具")
    print("=" * 60)
    
    name = input("\n实验名称: ").strip()
    if not name:
        name = f"实验_{datetime.now().strftime('%m%d')}"
    
    hypothesis = input("实验假设（你预期什么会变好）: ").strip()
    model_assumption = input("验证哪个模型假设: ").strip()
    
    exp = Experiment(
        name=name,
        hypothesis=hypothesis,
        model_assumption=model_assumption,
    )
    
    # 设计变量
    print("\n现在设计测试变量（每次只测一个变量）")
    while True:
        print(f"\n--- 变量 #{len(exp.variables) + 1} ---")
        var_name = input("变量名称（如：标题公式）: ").strip()
        if not var_name and len(exp.variables) == 0:
            print("至少需要一个变量")
            continue
        elif not var_name:
            break
            
        control = input("控制组条件: ").strip()
        treatment = input("测试组条件: ").strip()
        notes = input("补充说明（可选）: ").strip()
        
        exp.variables.append(TestVariable(
            name=var_name,
            control=control,
            treatment=treatment,
            notes=notes,
        ))
        
        more = input("\n添加另一个变量？(y/n): ").strip().lower()
        if more != 'y':
            break
    
    # 样本量
    try:
        sample = int(input(f"\n每组最少样本量（默认 {exp.sample_size}）: ").strip() or exp.sample_size)
        exp.sample_size = sample
    except ValueError:
        pass
    
    try:
        days = int(input(f"测试周期天数（默认 {exp.test_duration_days}）: ").strip() or exp.test_duration_days)
        exp.test_duration_days = days
    except ValueError:
        pass
    
    # 信号灯
    print("\n信号灯设定（回车使用默认信号灯）")
    
    return exp


def generate_template_csv(filepath: str):
    """生成空白实验设计模板 CSV"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["变量名称", "控制组", "测试组", "补充说明"])
        writer.writerow(["标题公式", "[当前标题风格]", "[新标题风格]", "如：疑问句 vs 陈述句"])
        writer.writerow(["封面风格", "[当前封面]", "[新封面]", "如：文字封面 vs 产品图"])
        writer.writerow(["内容结构", "[当前结构]", "[新结构]", "如：清单体 vs 故事体"])
    
    print(f"模板已生成: {filepath}")


# ─── 报告生成 ───────────────────────────────────────────────────────────────

def generate_experiment_plan(exp: Experiment, signals: List[SignalLight]) -> str:
    """生成实验设计 Markdown 报告"""
    now = datetime.now()
    start_date = now.strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=exp.test_duration_days)).strftime("%Y-%m-%d")
    
    lines = []
    lines.append(f"# 实验方案：{exp.name}")
    lines.append(f"")
    lines.append(f"**创建日期**: {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**测试周期**: {start_date} -> {end_date}（{exp.test_duration_days} 天）")
    lines.append(f"")
    lines.append(f"## 实验假设")
    lines.append(f"")
    lines.append(f"{exp.hypothesis}")
    lines.append(f"")
    lines.append(f"## 验证的模型假设")
    lines.append(f"")
    lines.append(f"{exp.model_assumption}")
    lines.append(f"")
    
    if exp.variables:
        lines.append(f"## 测试变量")
        for i, v in enumerate(exp.variables, 1):
            lines.append(f"")
            lines.append(f"### 变量 {i}：{v.name}")
            lines.append(f"")
            lines.append(f"| | 条件 |")
            lines.append(f"|------|------|")
            lines.append(f"| 控制组 | {v.control} |")
            lines.append(f"| 测试组 | {v.treatment} |")
            if v.notes:
                lines.append(f"| 补充 | {v.notes} |")
    
    lines.append(f"")
    lines.append(f"## 测试设计")
    lines.append(f"")
    lines.append(f"- **每组样本量**: {exp.sample_size} 篇")
    lines.append(f"- **总发帖量**: {exp.sample_size * max(len(exp.variables), 1)} 篇（含控制组）")
    lines.append(f"- **发布频率**: 每 {max(exp.test_duration_days // max(exp.sample_size, 1), 1)} 天 1 篇")
    lines.append(f"- **控制变量**: 除测试变量外，其他要素保持一致")
    lines.append(f"")
    lines.append(f"## 信号灯系统")
    lines.append(f"")
    lines.append(f"### [绿灯] 绿灯（加注信号）")
    for s in signals:
        if s.type == "green":
            lines.append(f"- **{s.metric}**: {s.condition}")
            lines.append(f"  -> 行动: {s.action}")
    lines.append(f"")
    lines.append(f"### [黄灯] 黄灯（观察信号）")
    for s in signals:
        if s.type == "yellow":
            lines.append(f"- **{s.metric}**: {s.condition}")
            lines.append(f"  -> 行动: {s.action}")
    lines.append(f"")
    lines.append(f"### [红灯] 红灯（止损信号）")
    for s in signals:
        if s.type == "red":
            lines.append(f"- **{s.metric}**: {s.condition}")
            lines.append(f"  -> 行动: {s.action}")
    
    lines.append(f"")
    lines.append(f"## 测试纪律")
    lines.append(f"")
    lines.append(f"1. **信号灯预设不可变** -- 实验开始前设定好的信号灯，在结果出来后不可修改")
    lines.append(f"2. **不挑数据** -- 所有发帖都计入统计，不剔除「感觉不好」的数据点")
    lines.append(f"3. **单一变量原则** -- 控制组和测试组只改变一个变量")
    lines.append(f"4. **到点判断** -- {end_date} 无论结果如何，必须做出判断")
    lines.append(f"5. **记录每篇数据** -- 每篇帖子的互动数据需完整记录")
    
    return "\n".join(lines)


# ─── JSON/CSV 输出 ─────────────────────────────────────────────────────────

def export_signals_csv(signals: List[SignalLight], filepath: str):
    """导出信号灯为 CSV"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["信号灯类型", "指标", "触发条件", "行动"])
        for s in signals:
            type_label = {"green": "绿灯", "yellow": "黄灯", "red": "红灯"}.get(s.type, s.type)
            writer.writerow([type_label, s.metric, s.condition, s.action])
    print(f"信号灯已导出: {filepath}")


# ─── 主入口 ─────────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="实验设计工具 ---- 设计精确的发帖测试实验"
    )
    parser.add_argument(
        "--template", "-t",
        action="store_true",
        help="生成空白实验设计模板 CSV"
    )
    parser.add_argument(
        "--output", "-o",
        default="experiment_plan.md",
        help="实验方案输出文件路径（默认: experiment_plan.md）"
    )
    parser.add_argument(
        "--output-dir", "-d",
        default=".",
        help="输出目录（默认当前工作目录）。数据文件写入此目录而非 skill 目录。"
    )
    
    args = parser.parse_args()
    output_dir = args.output_dir
    
    if args.template:
        template_path = os.path.join(output_dir, "experiment_template.csv")
        generate_template_csv(template_path)
        return
    
    # 交互式设计
    exp = interactive_design()
    
    # 信号灯
    print("\n信号灯设置：")
    print("1. 使用默认信号灯（推荐）")
    print("2. 自定义信号灯")
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "2":
        signals = custom_signals()
    else:
        signals = DEFAULT_SIGNALS
    
    # 生成报告
    plan = generate_experiment_plan(exp, signals)
    
    # 输出
    plan_path = os.path.join(output_dir, args.output)
    with open(plan_path, 'w', encoding='utf-8') as f:
        f.write(plan)
    print(f"\n[OK] 实验方案已生成: {plan_path}")
    
    # 同时导出信号灯 CSV
    signals_path = os.path.join(output_dir, "signal_lights.csv")
    export_signals_csv(signals, signals_path)
    
    # 保存 JSON 格式
    exp_data = {
        "experiment": asdict(exp),
        "signals": [asdict(s) for s in signals],
        "generated_at": datetime.now().isoformat(),
    }
    json_path = os.path.join(output_dir, ".experiment_design.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(exp_data, f, ensure_ascii=False, indent=2)
    print(f"[文件] 原始数据已保存至 {json_path}")
    
    print("\n" + "=" * 60)
    print("  实验方案摘要")
    print("=" * 60)
    print(plan)


def custom_signals() -> List[SignalLight]:
    """自定义信号灯"""
    signals = []
    
    for signal_type, label in [("green", "[绿灯] 绿灯（加注）"), ("yellow", "[黄灯] 黄灯（观察）"), ("red", "[红灯] 红灯（止损）")]:
        print(f"\n--- {label} ---")
        while True:
            metric = input(f"指标（回车结束）: ").strip()
            if not metric:
                break
            condition = input("触发条件: ").strip()
            action = input("行动: ").strip()
            signals.append(SignalLight(
                type=signal_type,
                metric=metric,
                condition=condition,
                action=action,
            ))
    
    return signals


if __name__ == "__main__":
    main()
