#!/usr/bin/env python3
"""
帖子信号分析工具 -- analyze_post_signals.py

用途：分析已发布帖子的互动数据，对照信号灯系统给出"止损/加注/观察"建议。
本工具不采集任何数据，所有数据由用户手动输入。

用法：
  python analyze_post_signals.py                    # 交互模式
  python analyze_post_signals.py --file posts.csv   # CSV 模式
  python analyze_post_signals.py --check-signals      # 只查看当前信号灯状态

数据格式（CSV）：
  date,title,impressions,likes,collects,comments,shares,note
  2024-01-01,标题1,5000,350,85,42,15,"教程类"
  2024-01-05,标题2,3000,200,120,30,8,"清单体"
"""

import sys
import io

# 强制 UTF-8 输出，兼容 Windows PowerShell（包括管道场景）
if sys.platform == 'win32':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # 设置控制台代码页为 UTF-8
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except Exception:
        pass

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
elif hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8', errors='replace')

import csv
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime, timedelta
import math


# ─── 数据结构 ───────────────────────────────────────────────────────────────

@dataclass
class Post:
    """单篇帖子数据"""
    date: str                 # 发布日期
    title: str                # 标题
    impressions: int          # 曝光量
    likes: int                # 点赞数
    collects: int             # 收藏数
    comments: int             # 评论数
    shares: int = 0           # 分享/转发数
    note: str = ""            # 备注（如内容类型、测试组别）


@dataclass
class PostMetrics:
    """计算得到的帖子指标"""
    title: str
    date: str
    click_rate: float         # 互动率（(点赞+收藏*3+评论*2+分享) / 曝光）
    like_rate: float          # 点赞率
    collect_rate: float       # 收藏率
    comment_rate: float       # 评论率
    collect_like_ratio: float # 收藏/点赞比
    share_rate: float         # 分享率
    note: str


@dataclass
class SignalStatus:
    """信号灯状态"""
    signal_type: str          # "green" / "yellow" / "red"
    metric: str
    triggered: bool
    detail: str
    posts_involved: int = 0


@dataclass
class AnalysisResult:
    """分析结果"""
    posts: List[PostMetrics]
    signals: List[SignalStatus]
    trend: str                # "上升" / "下降" / "波动" / "稳定"
    recommendation: str
    overall_status: str       # "加注" / "观察" / "止损"


# ─── 指标计算 ───────────────────────────────────────────────────────────────

def compute_metrics(post: Post, now: Optional[datetime] = None) -> PostMetrics:
    """计算单篇帖子的互动指标，含新鲜度权重"""
    if now is None:
        now = datetime.now()
    
    imp = max(post.impressions, 1)
    
    # 综合互动得分（收藏权重最高，因为小红书看重"有用性"）
    total_interaction = post.likes + post.collects * 3 + post.comments * 2 + post.shares * 1.5
    
    return PostMetrics(
        title=post.title,
        date=post.date,
        click_rate=total_interaction / imp,
        like_rate=post.likes / imp,
        collect_rate=post.collects / imp,
        comment_rate=post.comments / imp,
        collect_like_ratio=post.collects / max(post.likes, 1),
        share_rate=post.shares / imp,
        note=post.note,
    )


# ─── 信号灯检查 ─────────────────────────────────────────────────────────────

def check_signals(metrics_list: List[PostMetrics], posts_raw: List[Post]) -> List[SignalStatus]:
    """根据信号灯规则检查状态，含时间维度的分析"""
    signals = []
    now = datetime.now()
    
    if len(metrics_list) < 3:
        signals.append(SignalStatus(
            signal_type="yellow",
            metric="样本量不足",
            triggered=True,
            detail=f"只有 {len(metrics_list)} 篇数据，需要至少 3-5 篇才能做出可靠判断",
            posts_involved=len(metrics_list),
        ))
        return signals
    
    # ── 时间维度分析 ──
    
    # 1. 发帖时间新鲜度：帖子是否太久没更新了？
    if posts_raw:
        dates = [datetime.strptime(p.date, "%Y-%m-%d") for p in posts_raw if p.date]
        if dates:
            last_post_date = max(dates)
            days_since_last = (now - last_post_date).days
            if days_since_last > 14:
                signals.append(SignalStatus(
                    signal_type="yellow",
                    metric="长时间未更新",
                    triggered=True,
                    detail=f"最近一篇帖子发布于 {days_since_last} 天前（{last_post_date.date()}），超过 14 天未更新将影响账号活跃度权重",
                    posts_involved=1,
                ))
            elif days_since_last > 30:
                signals.append(SignalStatus(
                    signal_type="red",
                    metric="长期断更",
                    triggered=True,
                    detail=f"最近一篇帖子发布于 {days_since_last} 天前（{last_post_date.date()}），断更超过 30 天严重损害账号权重",
                    posts_involved=1,
                ))
            
            # 2. 发帖频率分析（计算相邻帖子之间的时间间隔）
            sorted_dates = sorted(dates)
            if len(sorted_dates) >= 3:
                gaps = [(sorted_dates[i+1] - sorted_dates[i]).days for i in range(len(sorted_dates)-1)]
                avg_gap = sum(gaps) / len(gaps)
                max_gap = max(gaps)
                
                if avg_gap <= 1:
                    freq_status = "高频（每天多篇）"
                elif avg_gap <= 3:
                    freq_status = "中高频（每 1-3 天一篇）"
                elif avg_gap <= 7:
                    freq_status = "中频（每周 1-2 篇）"
                elif avg_gap <= 14:
                    freq_status = "低频（每 1-2 周一篇）"
                else:
                    freq_status = "极低频（超过 2 周一更）"
                
                if max_gap > avg_gap * 3 and max_gap > 14:
                    signals.append(SignalStatus(
                        signal_type="yellow",
                        metric="发帖节奏不稳定",
                        triggered=True,
                        detail=f"平均每 {avg_gap:.0f} 天发一篇（{freq_status}），但最长间隔达 {max_gap} 天，存在断更风险",
                        posts_involved=len(gaps),
                    ))
    
    # ── 互动趋势分析 ──
    
    # 用最后5篇（不够则全部）
    recent = metrics_list[-5:] if len(metrics_list) >= 5 else metrics_list
    
    # 1. 检查互动率趋势（连续递增多篇 -> 绿灯）
    if len(recent) >= 3:
        rates = [m.click_rate for m in recent[-3:]]
        if rates[0] < rates[1] < rates[2]:
            signals.append(SignalStatus(
                signal_type="green",
                metric="互动率持续上升",
                triggered=True,
                detail=f"连续 3 篇互动率递增: {rates[0]:.4f} -> {rates[1]:.4f} -> {rates[2]:.4f}",
                posts_involved=3,
            ))
        elif rates[0] > rates[1] > rates[2]:
            signals.append(SignalStatus(
                signal_type="red",
                metric="互动率持续走低",
                triggered=True,
                detail=f"连续 3 篇互动率递减: {rates[0]:.4f} -> {rates[1]:.4f} -> {rates[2]:.4f}",
                posts_involved=3,
            ))
    
    # 2. 检查收藏率
    if len(recent) >= 3:
        collect_rates = [m.collect_rate for m in recent[-3:]]
        # 判断收藏是否归零
        zero_collects = sum(1 for r in recent if r.collect_rate == 0)
        if zero_collects >= 3:
            signals.append(SignalStatus(
                signal_type="red",
                metric="收藏率归零",
                triggered=True,
                detail=f"最近 {len(recent)} 篇中有 {zero_collects} 篇收藏数为 0",
                posts_involved=zero_collects,
            ))
    
    # 3. 检查收藏/点赞比
    cl_ratios = [m.collect_like_ratio for m in recent]
    avg_cl = sum(cl_ratios) / len(cl_ratios)
    if avg_cl >= 0.5:
        signals.append(SignalStatus(
            signal_type="green",
            metric="收藏/点赞比高",
            triggered=True,
            detail=f"平均收藏/点赞比 {avg_cl:.2f}，内容'有用性'强",
            posts_involved=len(recent),
        ))
    elif avg_cl < 0.1 and len(recent) >= 3:
        signals.append(SignalStatus(
            signal_type="red",
            metric="收藏/点赞比极低",
            triggered=True,
            detail=f"平均收藏/点赞比 {avg_cl:.2f}，内容缺乏「有用性」",
            posts_involved=len(recent),
        ))
    
    # 4. 检查数据波动（CV > 50% -> 黄灯）
    if len(recent) >= 3:
        rates = [m.click_rate for m in recent]
        mean = sum(rates) / len(rates)
        if mean > 0:
            variance = sum((r - mean) ** 2 for r in rates) / len(rates)
            cv = math.sqrt(variance) / mean
            if cv > 0.5:
                signals.append(SignalStatus(
                    signal_type="yellow",
                    metric="数据波动大",
                    triggered=True,
                    detail=f"互动率变异系数 {cv:.2f}（> 0.5），数据波动较大",
                    posts_involved=len(recent),
                ))
    
    # 5. 粉丝增长加速（需要有粉丝数据，这里简化处理）
    # 如果用户提供了粉丝数据可以在 CSV 中扩展
    
    return signals


def analyze_trend(metrics_list: List[PostMetrics]) -> str:
    """分析整体趋势"""
    if len(metrics_list) < 3:
        return "数据不足"
    
    # 看最近 5 篇 vs 之前 5 篇
    half = len(metrics_list) // 2
    first_half = metrics_list[:half]
    second_half = metrics_list[half:]
    
    avg_first = sum(m.click_rate for m in first_half) / len(first_half)
    avg_second = sum(m.click_rate for m in second_half) / len(second_half)
    
    diff = (avg_second - avg_first) / max(avg_first, 0.0001)
    
    if diff > 0.2:
        return "上升"
    elif diff < -0.2:
        return "下降"
    else:
        # 检查波动
        cv = sum((m.click_rate - avg_second) ** 2 for m in second_half) / len(second_half)
        if cv**0.5 / max(avg_second, 0.0001) > 0.5:
            return "波动"
        return "稳定"


def determine_overall_status(signals: List[SignalStatus]) -> str:
    """综合判断整体状态"""
    has_red = any(s.signal_type == "red" and s.triggered for s in signals)
    has_green = any(s.signal_type == "green" and s.triggered for s in signals)
    has_yellow = any(s.signal_type == "yellow" and s.triggered for s in signals)
    
    if has_red:
        return "止损"
    elif has_green and not has_yellow:
        return "加注"
    elif has_green and has_yellow:
        return "谨慎加注"
    else:
        return "观察"


# ─── 数据输入 ───────────────────────────────────────────────────────────────

def parse_csv(filepath: str) -> List[Post]:
    """从 CSV 读取帖子数据"""
    posts = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            posts.append(Post(
                date=row['date'],
                title=row['title'],
                impressions=int(row['impressions']),
                likes=int(row['likes']),
                collects=int(row['collects']),
                comments=int(row['comments']),
                shares=int(row.get('shares', 0)),
                note=row.get('note', ''),
            ))
    return posts


def interactive_input() -> List[Post]:
    """交互模式输入帖子数据"""
    print("\n" + "=" * 60)
    print("  帖子信号分析工具 -- 交互模式")
    print("  请输入你的帖子数据")
    print("=" * 60)
    
    posts = []
    while True:
        print(f"\n--- 帖子 #{len(posts) + 1} ---")
        title = input("标题: ").strip()
        if not title and len(posts) == 0:
            print("请至少输入一篇帖子")
            continue
        elif not title:
            break
        
        date = input("发布日期 (YYYY-MM-DD): ").strip()
        try:
            impressions = int(input("曝光量: ") or "0")
            likes = int(input("点赞数: ") or "0")
            collects = int(input("收藏数: ") or "0")
            comments = int(input("评论数: ") or "0")
            shares = int(input("分享数（可选，默认0）: ") or "0")
        except ValueError:
            print("输入格式错误")
            continue
        
        note = input("备注（如：测试组/控制组，可选）: ").strip()
        
        posts.append(Post(
            date=date,
            title=title,
            impressions=impressions,
            likes=likes,
            collects=collects,
            comments=comments,
            shares=shares,
            note=note,
        ))
        
        more = input("\n添加下一篇？(y/n): ").strip().lower()
        if more != 'y':
            break
    
    return posts


# ─── 报告生成 ───────────────────────────────────────────────────────────────

def print_analysis(posts_raw: List[Post], output_dir: str = "."):
    """打印分析报告"""
    if not posts_raw:
        print("没有数据")
        return
    
    now = datetime.now()
    metrics_list = [compute_metrics(p, now) for p in posts_raw]
    
    print("\n" + "=" * 60)
    print("  帖子信号分析报告")
    print("=" * 60)
    
    # 各帖指标
    print(f"\n[数据] 帖子互动指标")
    print(f"  {'日期':<12} {'标题':<20} {'互动率':<10} {'收藏率':<10} {'收藏/点赞比':<12}")
    print(f"  {'-'*64}")
    for m in metrics_list:
        title_display = m.title[:18] if len(m.title) > 18 else m.title
        print(f"  {m.date:<12} {title_display:<20} {m.click_rate:<10.4f} {m.collect_rate:<10.4f} {m.collect_like_ratio:<12.2f}")
    
    # 趋势分析
    trend = analyze_trend(metrics_list)
    print(f"\n[趋势] 整体趋势: {trend}")
    
    # 信号检查
    signals = check_signals(metrics_list, posts_raw)
    status = determine_overall_status(signals)
    
    print(f"\n[信号] 信号灯状态")
    print(f"  {'信号':<20} {'状态':<8} {'详情'}")
    print(f"  {'-'*60}")
    
    for s in signals:
        if s.triggered:
            icon = {"green": "[绿灯]", "yellow": "[黄灯]", "red": "[红灯]"}.get(s.signal_type, "[无]")
            print(f"  {icon} {s.metric:<17} {'触发':<8} {s.detail}")
    
    # 综合建议
    print(f"\n{'='*60}")
    print(f"  🏁 综合判断: {status}")
    print(f"{'='*60}")
    
    if status == "加注":
        print("""
  [绿灯] 当前信号良好，建议：
  - 增加发布频率
  - 深化当前内容方向
  - 制作系列化内容
  - 投入更多资源在该模型上
""")
    elif status == "谨慎加注":
        print("""
  [黄灯][绿灯] 有积极信号但存在不确定性，建议：
  - 保持当前频率，增加样本量
  - 关注黄灯信号是否消退
  - 检查数据波动的原因
""")
    elif status == "观察":
        print("""
  [黄灯] 暂无明显趋势，建议：
  - 保持当前节奏继续发布
  - 确保每篇内容都在验证同一个变量
  - 达到最少样本量后再做判断
""")
    elif status == "止损":
        print("""
  [红灯] 触发止损信号，建议：
  - 暂停发帖，回到对照验证阶段
  - 重新评估内容模型假设
  - 检查是模型问题还是执行问题
  - 考虑调整方向或人群定位
""")
    
    # 输出 JSON
    result = AnalysisResult(
        posts=metrics_list,
        signals=signals,
        trend=trend,
        recommendation=status,
        overall_status=status,
    )
    
    json_path = os.path.join(output_dir, ".signal_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "posts": [asdict(m) for m in metrics_list],
            "signals": [asdict(s) for s in signals],
            "trend": trend,
            "status": status,
        }, f, ensure_ascii=False, indent=2)
    print(f"[文件] 原始报告已保存至 {json_path}")


# ─── 主入口 ─────────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="帖子信号分析工具 ---- 分析帖子数据并给出止损/加注建议"
    )
    parser.add_argument(
        "--file", "-f",
        help="CSV 数据文件路径"
    )
    parser.add_argument(
        "--check-signals",
        action="store_true",
        help="只查看当前定义的信号灯规则"
    )
    parser.add_argument(
        "--output-dir", "-d",
        default=".",
        help="输出目录（默认当前工作目录）。数据文件写入此目录而非 skill 目录。"
    )
    
    args = parser.parse_args()
    output_dir = args.output_dir
    
    if args.check_signals:
        print("\n当前信号灯规则：")
        print("=" * 60)
        print("\n[绿灯] 加注信号")
        for s in DEFAULT_SIGNALS:
            if s["type"] == "green":
                print(f"  - {s['metric']}: {s['condition']}")
                print(f"    -> {s['action']}")
        print("\n[黄灯] 观察信号")
        for s in DEFAULT_SIGNALS:
            if s["type"] == "yellow":
                print(f"  - {s['metric']}: {s['condition']}")
                print(f"    -> {s['action']}")
        print("\n[红灯] 止损信号")
        for s in DEFAULT_SIGNALS:
            if s["type"] == "red":
                print(f"  - {s['metric']}: {s['condition']}")
                print(f"    -> {s['action']}")
        return
    
    # 获取数据
    if args.file:
        try:
            posts = parse_csv(args.file)
            print(f"从 {args.file} 读取了 {len(posts)} 条帖子数据")
        except Exception as e:
            print(f"读取文件失败: {e}")
            return
    else:
        posts = interactive_input()
    
    if not posts:
        print("没有数据，退出。")
        return
    
    print_analysis(posts, output_dir)


# 默认信号灯规则（与 design_experiment.py 保持一致，供独立引用）
DEFAULT_SIGNALS = [
    {"type": "green", "metric": "互动率持续上升", "condition": "连续 5 篇互动率递增", "action": "增加发布频率"},
    {"type": "green", "metric": "收藏率超预期", "condition": "单篇收藏率 > 平台同类 top 25%", "action": "投入更多资源"},
    {"type": "yellow", "metric": "数据波动大", "condition": "CV > 50%", "action": "增加样本量"},
    {"type": "yellow", "metric": "互动分散", "condition": "无稳定模式", "action": "检查内容一致性"},
    {"type": "red", "metric": "点击率低于预期", "condition": "连续 5 篇 < 中位数", "action": "停止该方向"},
    {"type": "red", "metric": "互动率持续走低", "condition": "连续 5 篇递减", "action": "暂停发帖"},
    {"type": "red", "metric": "收藏率归零", "condition": "连续 3 篇收藏为 0", "action": "重新评估价值定位"},
]


if __name__ == "__main__":
    main()
