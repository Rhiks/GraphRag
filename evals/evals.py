#!/usr/bin/env python3
"""
统计 AI 判题准确率脚本
基于 infer_results.jsonl 文件，计算不同维度下的判题准确率
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


def get_dimension_value(item: Dict, dimension_key: str):
    """根据维度键获取维度值"""
    if dimension_key == "data_source_type":
        return item.get("meta_info", {}).get("data_source_type", "unknown")
    if dimension_key == "topic_type":
        dimension_value = item.get("question_info", {}).get("topic_info", {}).get(
            "topic_type"
        )
        return "unknown" if dimension_value is None else dimension_value
    if dimension_key == "topic_id":
        dimension_value = item.get("question_info", {}).get("topic_info", {}).get(
            "topic_id"
        )
        return "unknown" if dimension_value is None else dimension_value
    return "unknown"


def is_false_positive(item: Dict) -> bool:
    """学生实际做错，但接口判定作对"""
    gt_correct = item.get("gt", {}).get("is_correct")
    infer_correct = item.get("infer_results", {}).get("is_correct")
    return gt_correct is False and infer_correct is True


def calculate_penalized_accuracy(
    total: int, correct: int, false_positive: int
) -> Tuple[int, float]:
    """计算惩罚幻觉准确率: 1 - ((3*误判作对数 + 其他错误数) / 总数)"""
    error_count = total - correct
    other_errors = error_count - false_positive
    penalized_accuracy = (
        (1 - ((3 * false_positive + other_errors) / total)) * 100
        if total > 0
        else 0.0
    )
    return other_errors, penalized_accuracy


def load_jsonl(file_path: str) -> List[Dict]:
    """加载 JSONL 文件"""
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: 跳过无效的 JSON 行: {e}", file=sys.stderr)
    return data


def calculate_accuracy(data: List[Dict]) -> Tuple[int, int, float]:
    """计算整体准确率"""
    total = len(data)
    correct = 0

    for item in data:
        gt_correct = item.get("gt", {}).get("is_correct")
        infer_correct = item.get("infer_results", {}).get("is_correct")

        # 判断 AI 判题结果是否与 ground truth 一致
        if gt_correct == infer_correct:
            correct += 1

    accuracy = (correct / total * 100) if total > 0 else 0.0
    return total, correct, accuracy


def calculate_accuracy_by_dimension(data: List[Dict], dimension_key: str) -> Dict:
    """按指定维度计算准确率"""
    dimension_stats = defaultdict(
        lambda: {"total": 0, "correct": 0, "false_positive": 0}
    )

    for item in data:
        dimension_value = get_dimension_value(item, dimension_key)

        gt_correct = item.get("gt", {}).get("is_correct")
        infer_correct = item.get("infer_results", {}).get("is_correct")

        dimension_stats[dimension_value]["total"] += 1
        if gt_correct == infer_correct:
            dimension_stats[dimension_value]["correct"] += 1
        if is_false_positive(item):
            dimension_stats[dimension_value]["false_positive"] += 1

    # 计算准确率
    result = {}
    for dim_value, stats in dimension_stats.items():
        total = stats["total"]
        correct = stats["correct"]
        accuracy = (correct / total * 100) if total > 0 else 0.0
        false_positive = stats["false_positive"]
        false_positive_rate = (false_positive / total * 100) if total > 0 else 0.0
        other_errors, penalized_accuracy = calculate_penalized_accuracy(
            total, correct, false_positive
        )
        result[dim_value] = {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "false_positive": false_positive,
            "false_positive_rate": false_positive_rate,
            "other_errors": other_errors,
            "penalized_accuracy": penalized_accuracy,
        }

    return result


def calculate_cost_time_stats(data: List[Dict]) -> Dict:
    """计算整体耗时统计"""
    total_times = []

    for item in data:
        infer_results = item.get("infer_results", {})
        total_time = infer_results.get("total_cost_time_ms")

        if total_time is not None:
            total_times.append(total_time)

    def calc_stats(times: List[float]) -> Dict:
        if not times:
            return {"count": 0, "avg": 0.0, "p90": 0.0, "max": 0.0}
        sorted_times = sorted(times)
        n = len(sorted_times)
        p90_index = int(n * 0.9)
        if p90_index >= n:
            p90_index = n - 1
        p90_value = sorted_times[p90_index]

        return {"count": n, "avg": sum(times) / n, "p90": p90_value, "max": max(times)}

    return {"total": calc_stats(total_times)}


def calculate_cost_time_by_dimension(data: List[Dict], dimension_key: str) -> Dict:
    """按指定维度计算耗时统计"""
    dimension_stats = defaultdict(lambda: {"total_times": []})

    for item in data:
        dimension_value = get_dimension_value(item, dimension_key)

        infer_results = item.get("infer_results", {})
        total_time = infer_results.get("total_cost_time_ms")

        if total_time is not None:
            dimension_stats[dimension_value]["total_times"].append(total_time)

    # 计算统计信息
    result = {}
    for dim_value, stats in dimension_stats.items():

        def calc_stats(times: List[float]) -> Dict:
            if not times:
                return {"count": 0, "avg": 0.0, "p90": 0.0, "max": 0.0}
            sorted_times = sorted(times)
            n = len(sorted_times)
            p90_index = int(n * 0.9)
            if p90_index >= n:
                p90_index = n - 1
            p90_value = sorted_times[p90_index]

            return {
                "count": n,
                "avg": sum(times) / n,
                "p90": p90_value,
                "max": max(times),
            }

        result[dim_value] = {"total": calc_stats(stats["total_times"])}

    return result


def save_failed_cases(data: List[Dict], output_file: str):
    """保存失败 case 到 JSONL 文件，按 topicId 分组并按数量从多到少排序"""
    # 收集失败 case 并按 topicId 分组
    failed_cases_by_topic = defaultdict(list)

    for item in data:
        gt_correct = item.get("gt", {}).get("is_correct")
        infer_correct = item.get("infer_results", {}).get("is_correct")

        # 判断 AI 判题结果是否与 ground truth 一致
        if gt_correct != infer_correct:
            # 获取 topicId
            topic_id = (
                item.get("question_info", {}).get("topic_info", {}).get("topic_id")
            )
            if topic_id is None:
                topic_id = "unknown"
            failed_cases_by_topic[topic_id].append(item)

    # 按照每个 topicId 的失败 case 数量从多到少排序
    sorted_topics = sorted(
        failed_cases_by_topic.items(), key=lambda x: len(x[1]), reverse=True
    )

    # 按照排序后的顺序输出，相同 topicId 的 case 放在一起
    failed_cases = []
    for topic_id, cases in sorted_topics:
        failed_cases.extend(cases)

    # 保存到文件
    with open(output_file, "w", encoding="utf-8") as f:
        for case in failed_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"失败 case 已保存到: {output_file} (共 {len(failed_cases)} 条)")
    return failed_cases


def get_display_width(text: str) -> int:
    """计算文本的显示宽度（中文字符算2个宽度）"""
    width = 0
    for char in str(text):
        # 中文字符、全角字符等占2个宽度
        if ord(char) > 127:
            width += 2
        else:
            width += 1
    return width


def format_table(headers: List[str], rows: List[List], tablefmt: str = "grid") -> str:
    """格式化表格，中文宽度=2；首列左对齐，其余列右对齐"""
    col_widths = [get_display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], get_display_width(str(cell)))

    # 对齐策略：首列左对齐，其余列右对齐
    aligns = ["left"] + ["right"] * (len(headers) - 1)

    def pad_cell(text: str, width: int, align: str) -> str:
        """填充单元格，考虑中文字符宽度与对齐"""
        text_str = str(text)
        display_width = get_display_width(text_str)
        padding = width - display_width
        if padding <= 0:
            return text_str
        if align == "right":
            return " " * padding + text_str
        else:
            return text_str + " " * padding

    # 创建分隔线
    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    lines = [sep]
    # 表头
    header_row = (
        "|"
        + "|".join(
            f" {pad_cell(h, w, aligns[i])} "
            for i, (h, w) in enumerate(zip(headers, col_widths))
        )
        + "|"
    )
    lines.append(header_row)
    lines.append(sep)
    # 数据行
    for row in rows:
        data_row = (
            "|"
            + "|".join(
                f" {pad_cell(cell, w, aligns[i])} "
                for i, (cell, w) in enumerate(zip(row, col_widths))
            )
            + "|"
        )
        lines.append(data_row)
    lines.append(sep)
    return "\n".join(lines)


def generate_report(
    data: List[Dict], output_file: str = None, failed_cases_file: str = None
):
    """生成统计报告"""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("AI 判题准确率统计报告")
    report_lines.append("=" * 80)
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # 1. 整体统计（合并准确率和耗时统计）
    total, correct, accuracy = calculate_accuracy(data)
    false_positive = sum(1 for item in data if is_false_positive(item))
    false_positive_rate = (false_positive / total * 100) if total > 0 else 0.0
    other_errors, penalized_accuracy = calculate_penalized_accuracy(
        total, correct, false_positive
    )
    cost_time_stats = calculate_cost_time_stats(data)
    total_stats = cost_time_stats["total"]

    report_lines.append("【整体统计】")

    # 构建合并后的表格行
    overall_row = [
        total,
        correct,
        total - correct,
        f"{accuracy:.2f}%",
        false_positive,
        f"{false_positive_rate:.2f}%",
        other_errors,
        f"{penalized_accuracy:.2f}%",
    ]

    # 添加耗时统计
    if total_stats["count"] > 0:
        overall_row.extend(
            [
                f"{total_stats['avg']:.2f}",
                f"{total_stats['p90']:.2f}",
                f"{total_stats['max']:.2f}",
            ]
        )
    else:
        overall_row.extend(["-", "-", "-"])

    overall_table = format_table(
        headers=[
            "总样本数",
            "判题正确数",
            "判题错误数",
            "准确率",
            "误判作对数",
            "误判作对率",
            "其他错误数",
            "惩罚幻觉准确率",
            "平均耗时 (ms)",
            "P90耗时 (ms)",
            "最大耗时 (ms)",
        ],
        rows=[overall_row],
    )
    report_lines.append(overall_table)
    report_lines.append("")

    # 2. 按 data_source_type 统计
    report_lines.append("【按数据源类型 (data_source_type) 统计】")
    data_source_stats = calculate_accuracy_by_dimension(data, "data_source_type")
    data_source_cost_time = calculate_cost_time_by_dimension(data, "data_source_type")
    if data_source_stats:
        # 按维度值排序（字母顺序），确保不同报告的行顺序一致
        sorted_stats = sorted(data_source_stats.items(), key=lambda x: x[0])

        # 合并准确率和耗时统计表格
        merged_table_rows = []
        for ds_type, stats in sorted_stats:
            row = [
                ds_type,
                stats["total"],
                stats["correct"],
                stats["total"] - stats["correct"],
                f"{stats['accuracy']:.2f}%",
                stats["false_positive"],
                f"{stats['false_positive_rate']:.2f}%",
                stats["other_errors"],
                f"{stats['penalized_accuracy']:.2f}%",
            ]
            # 添加耗时统计
            if ds_type in data_source_cost_time:
                cost_stats = data_source_cost_time[ds_type]
                total_stats = cost_stats["total"]
                if total_stats["count"] > 0:
                    row.extend(
                        [
                            f"{total_stats['avg']:.2f}",
                            f"{total_stats['p90']:.2f}",
                            f"{total_stats['max']:.2f}",
                        ]
                    )
            else:
                row.extend(["-", "-", "-"])
            merged_table_rows.append(row)

        merged_table = format_table(
            headers=[
                "数据源类型",
                "样本数",
                "正确数",
                "错误数",
                "准确率",
                "误判作对数",
                "误判作对率",
                "其他错误数",
                "惩罚幻觉准确率",
                "平均耗时 (ms)",
                "P90耗时 (ms)",
                "最大耗时 (ms)",
            ],
            rows=merged_table_rows,
        )
        report_lines.append(merged_table)
        report_lines.append("")
    else:
        report_lines.append("  无数据")
        report_lines.append("")

    # 3. 按 topic_type 统计
    report_lines.append("【按题目类型 (topic_type) 统计】")
    topic_type_stats = calculate_accuracy_by_dimension(data, "topic_type")
    topic_type_cost_time = calculate_cost_time_by_dimension(data, "topic_type")
    if topic_type_stats:
        # 按维度值排序（数字顺序），确保不同报告的行顺序一致
        # 尝试转换为数字排序，如果失败则按字符串排序
        def sort_key_topic_type(x):
            key = x[0]
            try:
                # 如果是数字，转换为数字排序
                return (0, int(key)) if key != "unknown" else (1, key)
            except (ValueError, TypeError):
                return (1, str(key))

        sorted_stats = sorted(topic_type_stats.items(), key=sort_key_topic_type)

        # 合并准确率和耗时统计表格
        merged_table_rows = []
        for topic_type, stats in sorted_stats:
            row = [
                f"topic_type={topic_type}",
                stats["total"],
                stats["correct"],
                stats["total"] - stats["correct"],
                f"{stats['accuracy']:.2f}%",
                stats["false_positive"],
                f"{stats['false_positive_rate']:.2f}%",
                stats["other_errors"],
                f"{stats['penalized_accuracy']:.2f}%",
            ]
            # 添加耗时统计
            if topic_type in topic_type_cost_time:
                cost_stats = topic_type_cost_time[topic_type]
                total_stats = cost_stats["total"]
                if total_stats["count"] > 0:
                    row.extend(
                        [
                            f"{total_stats['avg']:.2f}",
                            f"{total_stats['p90']:.2f}",
                            f"{total_stats['max']:.2f}",
                        ]
                    )
            else:
                row.extend(["-", "-", "-"])
            merged_table_rows.append(row)

        merged_table = format_table(
            headers=[
                "题目类型",
                "样本数",
                "正确数",
                "错误数",
                "准确率",
                "误判作对数",
                "误判作对率",
                "其他错误数",
                "惩罚幻觉准确率",
                "平均耗时 (ms)",
                "P90耗时 (ms)",
                "最大耗时 (ms)",
            ],
            rows=merged_table_rows,
        )
        report_lines.append(merged_table)
        report_lines.append("")
    else:
        report_lines.append("  无数据")
        report_lines.append("")

    # 4. 按 topic_id 统计
    report_lines.append("【按题目ID (topic_id) 统计】")
    topic_id_stats = calculate_accuracy_by_dimension(data, "topic_id")
    topic_id_cost_time = calculate_cost_time_by_dimension(data, "topic_id")
    if topic_id_stats:
        # 先过滤掉准确率=100%的，然后按样本数从大到小排序；
        # 当样本数相同时，再按 topic_id 排序（数字优先，其次 unknown，最后其他字符串）
        filtered_stats = [
            (k, v) for k, v in topic_id_stats.items() if v["accuracy"] < 100.0
        ]

        def topic_id_sort_value(topic_id):
            try:
                # 数字 topic_id 按数值升序
                return (0, int(topic_id)) if topic_id != "unknown" else (1, topic_id)
            except (ValueError, TypeError):
                # 非数字按字符串排序，排在数字和 unknown 之后
                return (2, str(topic_id))

        # 先按样本数（total）从大到小，再按 topic_id 升序
        sorted_stats = sorted(
            filtered_stats, key=lambda x: (-x[1]["total"], topic_id_sort_value(x[0]))
        )[:20]
        if sorted_stats:
            # 合并准确率和耗时统计表格
            merged_table_rows = []
            for topic_id, stats in sorted_stats:
                row = [
                    f"topic_id={topic_id}",
                    stats["total"],
                    stats["correct"],
                    stats["total"] - stats["correct"],
                    f"{stats['accuracy']:.2f}%",
                    stats["false_positive"],
                    f"{stats['false_positive_rate']:.2f}%",
                    stats["other_errors"],
                    f"{stats['penalized_accuracy']:.2f}%",
                ]
                # 添加耗时统计
                if topic_id in topic_id_cost_time:
                    cost_stats = topic_id_cost_time[topic_id]
                    total_stats = cost_stats["total"]
                    if total_stats["count"] > 0:
                        row.extend(
                            [
                                f"{total_stats['avg']:.2f}",
                                f"{total_stats['p90']:.2f}",
                                f"{total_stats['max']:.2f}",
                            ]
                        )
                else:
                    row.extend(["-", "-", "-"])
                merged_table_rows.append(row)

            merged_table = format_table(
                headers=[
                    "题目ID",
                    "样本数",
                    "正确数",
                    "错误数",
                    "准确率",
                    "误判作对数",
                    "误判作对率",
                    "其他错误数",
                    "惩罚幻觉准确率",
                    "平均耗时 (ms)",
                    "P90耗时 (ms)",
                    "最大耗时 (ms)",
                ],
                rows=merged_table_rows,
            )
            report_lines.append(merged_table)
            report_lines.append("")
        else:
            report_lines.append("  所有 topic_id 的准确率均为 100%")
            report_lines.append("")
    else:
        report_lines.append("  无数据")
        report_lines.append("")

    report_lines.append("=" * 80)

    report_text = "\n".join(report_lines)

    # 输出到控制台
    print(report_text)

    # 保存到文件
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"\n报告已保存到: {output_file}")

    # 保存失败 case
    if failed_cases_file:
        save_failed_cases(data, failed_cases_file)

    return report_text


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="统计 AI 判题准确率")
    parser.add_argument(
        "--input",
        type=str,
        default="results/test_infer_results.jsonl",
        help="输入的 JSONL 文件路径 (默认: results/test_infer_results.jsonl)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出的报告文件路径 (默认: 不保存文件，仅输出到控制台)",
    )
    parser.add_argument(
        "--failed-cases",
        type=str,
        default=None,
        help="输出的失败 case JSONL 文件路径 (默认: 不保存)",
    )

    args = parser.parse_args()

    # 检查输入文件是否存在
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 加载数据
    print(f"正在加载数据: {input_path}")
    data = load_jsonl(str(input_path))
    print(f"已加载 {len(data)} 条数据\n")

    if len(data) == 0:
        print("错误: 没有有效数据", file=sys.stderr)
        sys.exit(1)

    # 生成报告
    generate_report(data, args.output, args.failed_cases)


if __name__ == "__main__":
    main()
