from constants.common import COMPRE_EXAMPLE_TEXT, EXAMPLE_TEXTS, QUESTION_TYPE_MAP
from prompt.blank_ocr_prompt_templates import (
    MULTI_BLANK_PROMPT_TEMPLATE,
    PROMPT_TEMPLATE1,
)
from utils.encodecode import mask_stem, parse_comprehensive_parttern


def general_prompt_engineering(
    question_type, tidy_stem, num_answers=-1, mode="plus", sub_index=0
):
    if num_answers > 1 and mode == "plus":
        # 多空题、主模型，走独立的 prompt
        prompt_text = prompt_engineering_multi_blank(
            question_type, tidy_stem, num_answers, sub_index
        )
    else:
        prompt_text = prompt_engineering(
            question_type, tidy_stem, num_answers, mode, sub_index
        )
    return prompt_text


def _get_sub_task_instruction(sub_index):
    """
    【新增】辅助函数：根据 sub_index 生成提示字符串
    逻辑：只有当题目类型为综合题中的一个小题时，才根据 sub_index 生成子题指令。
    """
    if sub_index is not None and sub_index >= 0:
        display_index = sub_index + 1
        return f"- 【重要】：本题为综合题中的一个小题，请务必仅定位并识别第({display_index})小问的作答，严格忽略第({display_index})小问以外的作答内容。"
    return ""


def prompt_engineering_multi_blank(question_type, tidy_stem, num_answers, sub_index=0):
    is_compre, compre_result = parse_comprehensive_parttern(tidy_stem)
    if is_compre:
        # 综合题单独处理
        stem = compre_result["main_text"]
        for q in compre_result["subitems"]:
            stem += f"\n- 第{q['index']+1}个小问：{q['content']}"
        example_text = COMPRE_EXAMPLE_TEXT
        num_subitems = len(compre_result["subitems"])
        question_type_str = f"综合题（{num_subitems}小题）"
    else:
        question_type_str = QUESTION_TYPE_MAP[question_type]
        example_text = EXAMPLE_TEXTS[int(question_type) - 1]
        stem = tidy_stem

    masked_stem = mask_stem(stem)

    instruction_str = _get_sub_task_instruction(sub_index)

    prompt_text = MULTI_BLANK_PROMPT_TEMPLATE.format(
        question_type=question_type_str,
        num_blanks=num_answers,
        example_text=example_text,
        stem=masked_stem,
        sub_task_instruction=instruction_str,
    )
    return prompt_text


def prompt_engineering(
    question_type, tidy_stem, num_answers=-1, mode="plus", sub_index=0
):

    #    prompt_text = """任务：识别指定题目的手写答案
    # 输入：
    # 题干：具体题目内容
    # 图片：包含1道或多道题的学生手写答案
    # 要求：
    # 精确匹配：仅识别与给定题干对应的那道题的答案
    # 定位填空：找到该题的空白处（横线上/下方）的手写数字
    # 忽略干扰：
    # - 忽略题干中的已知数字
    # - 忽略图片中其他题目的答案
    # - 忽略计算草稿或无关数字
    # 输出格式：
    # 单空：直接输出数字（如：20）
    # 多空：按顺序用逗号分隔（如：19,3,6）
    # 无法识别：输出?
    # 示例：
    # 题干：孙悟空吃了____个包子，猪八戒吃了____个
    # 图片显示答案：12，8
    # 输出：12,8
    # 请根据题干内容，在图片中找到对应题目并识别其手写答案。
    # 题目信息：""" + tidy_stem
    example_text = EXAMPLE_TEXTS[int(question_type) - 1]

    instruction_str = _get_sub_task_instruction(sub_index)

    # NOTE: 因为判断题的要求，题干信息必须在 prompt 的末尾
    prompt_template = (
        PROMPT_TEMPLATE1
        if mode == "plus"
        else """任务：识别指定题目的手写答案
输入：
题干：具体题目内容
图片：包含1道或多道题的学生手写答案
题型：{question_type}
{sub_task_instruction}
要求：
精确匹配：仅识别与给定题干对应的那道题的答案
定位填空：找到该题的空白处（横线上/下方）的手写答案
忽略干扰：
- 忽略题干中的已知数字
- 忽略图片中其他题目的答案
- 忽略计算草稿或无关文字
- 如果识别结果中有数学公式，请输出latex格式
- 按照空格个数输出，没有手写答案的地方用？占位
- 完全根据学生手写作答内容输出识别结果，不要解题
输出格式：
单空：直接输出手写答案（如：20）
多空：按顺序用逗号分隔（如：19,3,6）
无法识别：输出?
多空（含有未作答，未作答或者无法识别用?占位)（如果2空缺少第二空：20,？）
{example_text}
请根据题干内容，在图片中找到对应题目并识别其手写答案。
题目信息：{stem}"""
    )
    if mode == "plus":
        tidy_stem = mask_stem(tidy_stem)
    prompt_text = prompt_template.format(
        question_type=QUESTION_TYPE_MAP[question_type],
        example_text=example_text,
        stem=tidy_stem,
        sub_task_instruction=instruction_str,
    )
    if question_type == 3 and tidy_stem.startswith("判断下列说法是否正确"):
        prompt_text = prompt_text + generate_underscore_string(num_answers)
    return prompt_text


def generate_underscore_string(n):
    """
    生成指定数量的带括号编号和下划线的字符串

    参数:
    n -- 数字，表示要生成的数量

    返回:
    str -- 格式化的字符串
    """
    if not isinstance(n, int) or n <= 0:
        return "请输入一个正整数"

    # 生成列表：["（1）____", "（2）____", ...]
    parts = [f"（{i+1}）____" for i in range(n)]

    # 用空字符串连接所有部分
    return "".join(parts)


if __name__ == "__main__":
    prompt_text = prompt_engineering(3, "")
    print(prompt_text)
