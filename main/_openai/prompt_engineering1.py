def prompt_engineering(
    question_type, tidy_stem, add_hint=False, type="qwen3-vl-plus", num_answers=-1
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
    es_hints = {"qwen3-vl-plus": "答案是一个数学fractions", "qwen-vl-ocr-latest": ""}

    qus_dict = {1: "选择题", 2: "填空题", 3: "判断题"}
    choices_example_texts = """示例：
题干：孙悟空吃了____个包子，猪八戒吃了____个
图片显示答案：A，B
输出：A,B"""
    blanks_example_texts = """示例：
题干：孙悟空吃了____个包子，猪八戒吃了____个
图片显示答案：19，3
输出：19,3"""

    judge_example_texts = """示例1：
题干：1+2=1 ____
图片显示答案：√ 
输出：√
示例2：
题干：1+2=1 ____
图片显示答案：×
输出：×
"""

    example_texts = [choices_example_texts, blanks_example_texts, judge_example_texts]
    example_text = example_texts[int(question_type) - 1]
    if add_hint:
        hint_text = es_hints[type]
    else:
        hint_text = ""

    prompt_text = (
        f"""任务：识别指定题目的手写答案
输入：
题干：具体题目内容
图片：包含1道或多道题的学生手写答案
题型：{qus_dict[question_type]}
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
{hint_text}
题目信息："""
        + tidy_stem
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
