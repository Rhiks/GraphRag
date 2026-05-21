import cv2
import base64
import numpy as np
import re
import pdb
import io
from PIL import Image
from collections import Counter
from collections import OrderedDict


def tidy_indices_and_subitems(indices, subitems, subitems_withidxes, is_analysis=False):
    if len(indices) != len(subitems):
        return indices, subitems
    if indices == [] or subitems == []:
        return indices, subitems
    try:
        delete_indices = []
        for i in range(len(indices) - 1):
            if (
                subitems[i].endswith("由")
                or subitems[i].endswith("代入")
                or subitems[i].endswith("在")
            ):
                delete_indices.append(i)
        for idx in delete_indices:
            subitems[idx] = subitems[idx] + subitems_withidxes[idx + 1]
        for idx in sorted(delete_indices, reverse=True):
            indices.pop(idx + 1)
            subitems.pop(idx + 1)

        #### 故答案为：
        # if not is_analysis:
        #    return indices, subitems

        return indices, subitems
    except Exception as e:
        return indices, subitems


def parse_comprehensive_parttern(text):
    """
    解析综合题模式，提取主文本和带编号的子项。

    该函数用于识别和解析包含多个编号子项的综合题文本。它支持中文括号（如"（1）"）和
    英文括号（如"(1)"）两种编号格式，并提取每个子项的内容。

    参数:
        text (str): 待解析的文本内容，应包含主文本和多个带编号的子项。

    返回:
        tuple: 包含两个元素的元组
            - bool: 解析是否成功。成功返回True，失败返回False。
            - dict or None: 解析成功时返回包含以下键的字典，失败时返回None。
                - "main_text" (str): 主文本内容（编号子项之前的部分）
                - "subitems" (list): 子项列表，每个元素为包含"index"和"content"的字典
                - "pattern_name" (str): 匹配的模式名称（当前为"paren_pattern"）

    要求:
        - 文本中必须包含至少2个带编号的子项
        - 编号必须从1开始且连续（1, 2, 3, ...）
        - 支持中文括号"（"、"）"和英文括号"("、")"两种格式

    示例:
        >>> text = "这是一道综合题（1）第一个子项（2）第二个子项"
        >>> success, result = parse_comprehensive_parttern(text)
        >>> if success:
        ...     print(result["main_text"])  # "这是一道综合题"
        ...     print(result["subitems"])   # [{"index": 0, "content": "(1) 第一个子项"}, ...]
    """
    paren_pattern = r"[（(](\d+)[）)]\s*(.*?)(?=[(（]\d+[）)]|$)"

    try:
        matches = list(re.finditer(paren_pattern, text, re.DOTALL))
    except re.error as e:
        print(f"正则表达式错误: {e}")
        return False, None
    # if not (matches or matches1):
    if not (matches):
        return False, None
    indices = []
    subitems = []
    subitems_withidxes = []
    pattern_names = ["paren_pattern", "xila_pattern"]
    if matches and len(matches) >= 2:
        pattern_name = pattern_names[0]
        for match in matches:
            # 检查三种可能的编号格式
            num = match.group(1)
            content = match.group(2).strip() if match.group(2) else ""
            try:
                indices.append(int(num))
                subitems.append(content)
                subitems_withidxes.append("（{}）".format(num) + content)
            except ValueError:
                continue
        indices, subitems = tidy_indices_and_subitems(
            indices, subitems, subitems_withidxes
        )
        if not (
            (not indices)
            or (sorted(indices) != list(range(1, len(indices) + 1)))
            or len(indices) < 2
        ):
            main_text = text[: matches[0].start()].strip()
            result = {
                "main_text": main_text,
                "subitems": [
                    {"index": i, "content": "({}) ".format(str(i + 1)) + c}
                    for i, c in enumerate(subitems)
                ],
                "pattern_name": pattern_name,
            }
            return True, result
    return False, None


def is_physics(stem, topic_typ):
    try:
        is_compre, result = parse_comprehensive_parttern(stem)
        if is_compre and topic_typ == 2 and ("实验" in stem):
            is_compre = True
        else:
            is_compre = False
        return is_compre
    except Exception as e:
        return False


def is_judge_subitems(stem, topic_typ):
    try:
        is_compre, result = parse_comprehensive_parttern(stem)
        if is_compre and topic_typ == 3:
            is_compre = True
        else:
            is_compre = False
        return is_compre
    except Exception as e:
        return False


def base64_to_bgr_image(img_base64):
    """
    将已经 decode('utf-8') 的 Base64 字符串转换为 OpenCV 的 BGR 图像。

    参数:
        img_base64 (str): 已经 decode('utf-8') 的 Base64 字符串。

    返回:
        bgr_im (numpy.ndarray): OpenCV 的 BGR 格式图像。
    """
    # 将 Base64 字符串重新编码为字节数据
    img_bytes = base64.b64decode(img_base64.encode("utf-8"))

    # 将字节数据转换为 NumPy 数组
    img_np = np.frombuffer(img_bytes, dtype=np.uint8)

    # 使用 OpenCV 解码为 BGR 图像
    bgr_im = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

    # 确保图像解码成功
    if bgr_im is None:
        raise ValueError("Base64 字符串解码失败，请检查输入是否正确")

    return bgr_im


def numpy_bgr_to_urlsafe_base64(bgr_img):
    # 1. 将 BGR 转换为 RGB (OpenCV 使用 BGR 格式，而 PIL 使用 RGB)
    rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)

    # 2. 将 NumPy 数组转换为 PIL 图像
    pil_img = Image.fromarray(rgb_img)

    # 3. 将 PIL 图像转换为字节流
    img_byte_arr = io.BytesIO()
    pil_img.save(img_byte_arr, format="JPEG")  # 也可以使用 'PNG'
    img_byte_arr = img_byte_arr.getvalue()

    # 4. 将字节流编码为 Base64
    base64_str = base64.b64encode(img_byte_arr).decode("utf-8")

    # 5. 转换为 URL-safe 版本
    # urlsafe_base64 = base64_str.replace('+', '-').replace('/', '_').rstrip('=')

    return base64_str


def tidy(res):
    output = {"latex_string": ""}
    if res.get("text") is not None:

        output["latex_string"] = res["text"]
        if "confidence" in res:
            output["confidence"] = res["confidence"]

    return output


def tidy_baidu(res):
    output = {"latex_string": ""}
    words_result = res.get("words_result")
    if words_result is not None and len(words_result) >= 1:
        for i in range(len(words_result)):
            output["latex_string"] = output["latex_string"] + words_result[i]["words"]
    return output


def tidy_tteller(res):
    output = {}

    output["latex_string"] = res
    return output


def filter_white_backgrounds(img):
    if (
        np.sum(img == (np.ones(img.shape) * 255).astype("uint8"))
        == img.shape[0] * img.shape[1] * img.shape[2]
    ):
        return True
    return False


def filter_single_color_backgroud(img):
    first_pixel = img[0, 0]
    if np.all(img == first_pixel):
        return True
    return False


def filter_white_backgrounds_update(img):
    h, w, _ = img.shape
    if h <= 60 and w <= 60:
        inner_img = img
    elif h <= 60 and w > 60:
        inner_img = img[:, 20 : w - 10, :]
    elif h > 60 and w <= 60:
        inner_img = img[20 : h - 10, :, :]
    else:
        inner_img = img[20 : h - 10, 20 : w - 10, :]
        nh, nw, _ = inner_img.shape
    return filter_single_color_backgroud(inner_img)


def contains_only_chinese(string):
    # 正则表达式匹配汉字字符范围
    pattern = re.compile(r"[\u4e00-\u9fff]+")
    return bool(re.fullmatch(pattern, string))


def contains_chinese(string):
    # 正则表达式匹配汉字字符范围
    pattern = re.compile(r"[\u4e00-\u9fff]")
    if pattern.search(string):
        return True
    else:
        return False


def contains_letters(string):
    return bool(re.search(r"[a-zA-Z]", string))


def is_use_comma(string):
    return bool(re.fullmatch(r"^\(-?\d+.-?\d+\)$", string)) or bool(
        re.fullmatch(r"^\\left\(-?\d+.-?\d+\\right\)$", string)
    )


def is_just_letters(string):
    return bool(re.fullmatch(r"[a-zA-Z]+", string))


def is_just_Uletters(string):
    return bool(re.fullmatch(r"[A-Z]+", string))


def is_just_number_letters(string):
    return bool(re.fullmatch(r"[a-z0-9]+", string))


def is_pm_candidates(string):
    pattern = r"^([1-9])或-(\1)$"
    return bool(re.fullmatch(pattern, string))


def is_pm_number(string):
    x = None
    pattern = r"^([1-9])或-(\1)$"
    match = re.fullmatch(pattern, string)
    if match:
        x = match.group(1)
    return x


def edit_numwithcls(content, string):
    if string.replace("^{0}", "0", 1) == content:
        return content
    else:
        return string


def edit_letterwithcls(content, string):
    # pdb.set_trace()
    if bool(re.fullmatch(r"[A-Z][0-9]", string)) and bool(
        re.fullmatch(r"{{[A-Z]}_{[0-9]}}", content)
    ):
        if len(string) == 2:
            string = string[:-1] + "_{" + format(string[-1]) + "}"
    return string

    if string.replace("^{0}", "0", 1) == content:
        return content
    else:
        return string


def edit_pm_res(content, string):
    pm_candidates = ["土", "士"]
    three_candidates = ["了", "弓"]
    for e in pm_candidates:
        if string.startswith(e):
            string = "\\pm" + string[1:]
    pm_number = is_pm_number(content)
    if pm_number == "1":
        if string.endswith("/") or string.endswith("|"):
            string = string[:-1] + "1"
    if pm_number == "3":
        for e in three_candidates:
            if e in string:
                string = string.replace(e, "3")
    return string


def contains_latex_formula(text):
    # 定义一个简单的正则表达式，检查是否包含 LaTeX 公式的标志
    latex_patterns = [
        r"\$.*?\$",  # 匹配 $...$ 形式的内联公式
        r"\\begin\{.*?\}.*?\\end\{.*?\}",  # 匹配 \begin{...} 和 \end{...} 环境
        r"\$\$.+?\$\$",  # 匹配 $$...$$ 形式的块级公式
        r"\\[a-zA-Z]+",  # 匹配以反斜杠开头的 LaTeX 命令，如 \frac, \sum 等
    ]

    # 检查字符串中是否包含上述任何一个 LaTeX 公式标志
    for pattern in latex_patterns:
        if re.search(pattern, text):
            return True
    return False


def remove_latex_delimiters(formula):
    # 使用正则表达式去除 \\( 和 \\)
    cleaned_formula = re.sub(r"\\\(|\\\)", "", formula)
    return cleaned_formula


def remove_math_dollars(text):
    if text.startswith("$") and text.endswith("$"):
        return text[1:-1]  # 去掉首尾的 $
    return text  # 如果没有 $ 包裹，返回原字符串


def tidy_open_bracket(s):
    if bool(re.fullmatch(r"^\\\[-?\d+(.\d)?\d*\\\]$", s)):
        s = re.sub(r"\\\[|\\\]", "", s)
    return s


def tidy_dirty_es(s):
    s = s.replace("^{}", "")
    s = s.replace("{}", "")
    s = re.sub(r"\\text\{(\d+)\}", r"\1", s)
    return s


def clean_string_with_latex(string):
    # 匹配 LaTeX 命令及其后的第一个空格（保护这个空格）
    pattern = r"(\\[a-zA-Z]+|\\[^a-zA-Z])( )"

    # 找到所有 LaTeX 命令及其后的第一个空格
    latex_matches = re.finditer(pattern, string)

    # 记录需要保护的位置（索引）
    protect_indices = []
    for match in latex_matches:
        # 获取空格的位置
        space_pos = match.start(2)
        protect_indices.append(space_pos)

    # 构建新字符串，保留被保护的空格，删除其他空格
    result = []
    for i, char in enumerate(string):
        if char != " ":
            result.append(char)
        elif i in protect_indices:
            result.append(" ")
        # 其他空格被跳过（即删除）

    return "".join(result)


def keep_only_specific_nbsp(text, keep_in_pattern="是&nbsp;．"):
    """
    最简单的实现：只保留特定模式中的 &nbsp;

    Args:
        text (str): 输入字符串
        keep_in_pattern (str): 包含 &nbsp; 的完整模式

    Returns:
        str: 处理后的字符串
    """
    if "&nbsp;" not in keep_in_pattern:
        # 如果模式中不包含 &nbsp;，直接替换所有
        return text.replace("&nbsp;", " ")

    # 分割字符串为需要保留的部分和不需要保留的部分
    parts = []
    remaining = text
    pattern = keep_in_pattern

    while pattern in remaining:
        # 找到模式的位置
        index = remaining.find(pattern)

        # 添加模式前面的部分（替换其中的 &nbsp;）
        before = remaining[:index].replace("&nbsp;", " ")
        parts.append(before)

        # 添加模式本身（不修改）
        parts.append(pattern)

        # 更新剩余字符串
        remaining = remaining[index + len(pattern) :]

    # 添加最后剩余的部分（替换其中的 &nbsp;）
    parts.append(remaining.replace("&nbsp;", " "))

    return "".join(parts)


def tidy_es_stem(
    topic_tigan, num_answers, es_answers, question_type=2, options: list[str] = None
):
    _is_physics = False
    _is_judge_subitems = False
    _need_split = False
    # pattern = r'．（[^）]*[\u4e00-\u9fff][^）]*）&nbsp;$'
    pattern0 = r"([.|．])\s*((&nbsp;( |&nbsp;)*)+$)"
    pattern = r"．（[^）]*[\u4e00-\u9fff][^）]*）(&nbsp;( |&nbsp;)*)+$"
    pattern1 = r"(．（[^）]*[\u4e00-\u9fff][^）]*）)((&nbsp;( |&nbsp;)*)+$)"
    pattern2 = r"([.|．])\s*((&nbsp;( |&nbsp;)*)+)（2）"
    topic_tigan = re.sub(r"<[^>]+>", "", topic_tigan)  # 移除HTML标签
    if question_type == 1:  # 选择题，在题干后添加选项
        if options:
            options_list = [
                f"{chr(ord('A') + i)}. {option.get('text', '(空选项)')}"
                for i, option in enumerate(options)
            ]
            options_str = "    ".join(options_list)
            topic_tigan = topic_tigan + "\n\n" + options_str
    if question_type == 2:

        topic_tigan = topic_tigan.replace(
            "=&nbsp;； &nbsp; &nbsp;（2）", "=&nbsp;； （2）"
        )
        pa_match0 = re.search(pattern0, topic_tigan)
        if topic_tigan.count("&nbsp;") > num_answers and pa_match0:
            topic_tigan = re.sub(pattern0, r"\1", topic_tigan)
        pa_match = re.search(pattern, topic_tigan)
        if topic_tigan.count("&nbsp;") > num_answers and pa_match:
            topic_tigan = re.sub(pattern1, r"\1", topic_tigan)
        pa_match2 = re.search(pattern2, topic_tigan)
        # pdb.set_trace()
        if topic_tigan.count("&nbsp;") > num_answers and pa_match2:
            topic_tigan = re.sub(pattern2, r"\1（2）", topic_tigan)
        if topic_tigan.count("&nbsp;") > num_answers and num_answers == 1:
            if topic_tigan.endswith("是&nbsp;．"):
                topic_tigan = keep_only_specific_nbsp(topic_tigan)
        topic_tigan = topic_tigan.replace("&nbsp;", "____")  # 替换HTML空格

        if topic_tigan.count("____") == 0 and num_answers == 1:
            topic_tigan = topic_tigan + " ____"
        _is_physics = is_physics(topic_tigan, question_type)
        if not (len(es_answers) == 1 and _is_physics):
            _is_physics = False
        # if is_physics(topic_tigan, question_type):
        #    topic_tigan = topic_tigan.replace("（\u3000\u3000）", '____')
    if question_type == 3 and len(es_answers) == 1:
        _is_judge_subitems = is_judge_subitems(es_answers[0], question_type)

    topic_tigan = topic_tigan.strip()
    _need_split = _is_physics or _is_judge_subitems
    return topic_tigan, _need_split


def tidy_es_content0(answers):
    tidy_answers = []
    for answer in answers:
        tidy_answer = tidy_content(answer)
        tidy_answers.append(tidy_answer)
    return tidy_answers


# print (clean_string_with_latex("\\sqrt{ }"))
def tidy_es_content(answers, need_split=False, question_type=-1):
    if len(answers) == 1 and need_split and question_type == 2:
        tidy_answers = []
        check, split0 = parse_comprehensive_parttern(answers[0])
        if check:
            subitems = split0.get("subitems", [])
            if subitems == []:
                tidy_answers = tidy_es_content0(answers)
                return tidy_answers
            for element in subitems:
                content = element.get("content", "")[4:].split("；")
                content = [tidy_content(e) for e in content]
                tidy_answers += content
            return tidy_answers
    if len(answers) == 1 and need_split and question_type == 3:
        tidy_answers = []
        check, split0 = parse_comprehensive_parttern(answers[0])
        if check:
            subitems = split0.get("subitems", [])
            if subitems == []:
                tidy_answers = tidy_es_content0(answers)
                return tidy_answers
            for element in subitems:
                content = (
                    element.get("content", "")[4:].strip().rstrip("；").rstrip("．")
                )
                tidy_answers.append(content)
            return tidy_answers

    tidy_answers = tidy_es_content0(answers)
    return tidy_answers


def pm_edit(es_answer, stu_answer):
    if stu_answer.startswith("-") and stu_answer[1:] == es_answer:
        return es_answer
    return stu_answer


def nums_17(es_answer, stu_answer):
    if is_just_number(es_answer) and len(es_answer) <= 2:
        return stu_answer
    if is_just_number(stu_answer) and is_just_number(es_answer):
        if stu_answer.replace("1", "7", 1) == es_answer:
            return es_answer
    # 逐个尝试替换每个 '1'
    for i in range(len(stu_answer)):
        if stu_answer[i] == "1":
            # 替换第 i 个位置的 '1' 为 '7'
            modified = stu_answer[:i] + "7" + stu_answer[i + 1 :]
            if modified == es_answer:
                return es_answer
    return stu_answer


def nums_miss1(es_answer, stu_answer):
    if is_just_number(stu_answer) and is_just_number(es_answer):
        if "1" + stu_answer == es_answer:
            return es_answer
    return stu_answer


def wrong_dot(es_answer, stu_answer):
    if is_just_number(stu_answer) and is_just_number(es_answer):
        if stu_answer.replace(".", "", 1) == es_answer:
            return es_answer
    return stu_answer


def frac_edit(es_answer, stu_answer):
    pa = r"^(\d+)/(\d+)$"
    if is_number_fractions(es_answer) or is_just_number(es_answer):
        if bool(re.fullmatch(pa, stu_answer)):
            d1 = re.fullmatch(pa, stu_answer)[1]
            d2 = re.fullmatch(pa, stu_answer)[2]
            output = f"\\frac{{{d1}}}{{{d2}}}"
            return output
    return stu_answer


def sqrt_edit(es_answer, stu_answer):
    pa = r"^(\d*)\\sqrt\{(\d+)\}"
    pa1 = r"^(\d*)√(\d+)"

    if bool(re.fullmatch(pa, es_answer)):
        if bool(re.fullmatch(pa1, stu_answer)):
            d1 = re.fullmatch(pa1, stu_answer)[1]
            d2 = re.fullmatch(pa1, stu_answer)[2]

            out = f"{d1}\\sqrt{{{d2}}}"
            return out
    return stu_answer


def options_edit(es_answer, stu_answer):
    if stu_answer == "13" and es_answer == "B":
        return es_answer
    if (
        remove_latex_delimiters(remove_math_dollars(stu_answer)) == "\\beta"
        and es_answer == "B"
    ):
        return es_answer
    return stu_answer


def llm_pipe(es_answer, stu_answer):
    if es_answer == stu_answer:
        return stu_answer
    stu_answer = nums_17(es_answer, stu_answer)
    stu_answer = wrong_dot(es_answer, stu_answer)
    stu_answer = pm_edit(es_answer, stu_answer)
    stu_answer = frac_edit(es_answer, stu_answer)
    stu_answer = sqrt_edit(es_answer, stu_answer)
    stu_answer = options_edit(es_answer, stu_answer)
    # stu_answer = nums_miss1(es_answer, stu_answer)
    return stu_answer


def match_answers(es_answers, stu_answers):
    updated_stu_answers = []
    if len(es_answers) != len(stu_answers):
        return stu_answers
    for i in range(len(stu_answers)):
        es_answer = es_answers[i]
        stu_answer = stu_answers[i]
        updated_stu_answer = llm_pipe(es_answer, stu_answer)
        updated_stu_answers.append(updated_stu_answer)
    return updated_stu_answers


def match_answers0(es_answers, stu_answers, mode="plus"):
    updated_stu_answers = []
    if mode == "plus":
        if len(stu_answers) < len(es_answers):
            stu_answers.extend([""] * (len(es_answers) - len(stu_answers)))
        if len(stu_answers) > len(es_answers):
            stu_answers = stu_answers[: len(es_answers)]

    for e in stu_answers:
        if e == "?":
            updated_stu_answers.append("")
        else:
            updated_stu_answers.append(e)
    return updated_stu_answers


def format_list_to_numbered(items):
    """
    将列表转换为编号格式：(1)内容；(2)内容；(3)内容...
    """
    result = []
    for i, item in enumerate(items, 1):
        result.append(f"（{i}）{item}")
    return "；".join(result) + "．"


def mark2numbers(answers, es_answers):
    es_string = "".join(es_answers)
    if ("√" in es_string) or ("×" in es_string):
        return answers
    answers_update = []
    for answer in answers:
        if answer == "√":
            answers_update.append("1")
        elif answer == "×":
            answers_update.append("0")
        else:
            answers_update.append("")
    return answers_update


def join_answers(answers, question_type=3):
    updated_stu_answers = []
    if question_type == 2:
        updated_stu_answers = ["；".join(answers)]
    elif question_type == 3:
        updated_stu_answers = [format_list_to_numbered(answers)]
    else:
        updated_stu_answers = answers
    return updated_stu_answers


def clean_recognition_result(raw_result: str) -> str:
    """
    清理和处理识别结果
    """
    import re

    # 如果返回无法识别标识
    # if '?' in raw_result or '无法识别' in raw_result:
    #    return '?'
    if "无法识别" in raw_result:
        raw_result = raw_result.replace("无法识别", "?")
    return raw_result

    ## 提取所有数字
    # numbers = re.findall(r'\d+', raw_result)
    #
    ##if not numbers:
    ##    return '?'
    # if len(numbers) == 1:
    #    # 单空题
    #    return numbers[0]
    # else:
    #    # 多空题，用逗号连接
    #    return ','.join(numbers)


def smart_split_answers_v2(answers, mode=0, num_es=1, page_source=0):
    if mode == 0:
        answers = answers.replace("\n", ",")
    """
    使用栈来跟踪括号层级，正确处理嵌套括号
    支持：圆括号、大括号、$...$、\(...\)
    """
    result = []
    current_start = 0
    i = 0

    # 使用栈来跟踪各种括号的嵌套层级
    paren_stack = []  # 圆括号栈
    brace_stack = []  # 大括号栈
    dollar_stack = []  # $ 栈
    latex_stack = []  # \( 栈

    while i < len(answers):
        char = answers[i]

        # 处理圆括号 (
        if char == "(" and (i == 0 or answers[i - 1] != "\\"):
            paren_stack.append(i)
        elif char == ")" and (i == 0 or answers[i - 1] != "\\"):
            if paren_stack:
                paren_stack.pop()

        # 处理大括号 {
        elif char == "{" and (i == 0 or answers[i - 1] != "\\"):
            brace_stack.append(i)
        elif char == "}" and (i == 0 or answers[i - 1] != "\\"):
            if brace_stack:
                brace_stack.pop()

        # 处理 $...$
        elif char == "$" and (i == 0 or answers[i - 1] != "\\"):
            if dollar_stack:
                dollar_stack.pop()
            else:
                dollar_stack.append(i)

        # 处理 \(...\)
        elif i < len(answers) - 1 and answers[i : i + 2] == "\\(":
            latex_stack.append(i)
            i += 1  # 跳过下一个字符
        elif i < len(answers) - 1 and answers[i : i + 2] == "\\)":
            if latex_stack:
                latex_stack.pop()
            i += 1  # 跳过下一个字符

        # 处理逗号分割
        elif char == ",":
            # 检查是否在任何括号内
            in_paren = len(paren_stack) > 0
            in_brace = len(brace_stack) > 0
            in_dollar = len(dollar_stack) > 0
            in_latex = len(latex_stack) > 0

            # 如果不在任何括号内，则分割
            if not (in_paren or in_brace or in_dollar or in_latex):
                result.append(answers[current_start:i].strip())
                current_start = i + 1

        i += 1

    # 添加最后一部分
    if current_start < len(answers):
        result.append(answers[current_start:].strip())
    output = [part for part in result if part]
    if num_es == 2 and len(output) == 1:
        if len(remove_math_dollars(output[0]).split(",")) == 2:
            output = remove_math_dollars(output[0]).split(",")
    if num_es == 3 and len(output) == 1:
        if len(remove_math_dollars(output[0]).split(",")) == 3:
            output = remove_math_dollars(output[0]).split(",")
    if (mode == 1) or (mode == 0 and page_source == 0):
        update_output = []
        for e in output:
            update_output += e.split("，")
        return update_output

    # return [part for part in result if part]
    return output


def tidy_content(string, mode="std_answer"):
    string = string.strip()
    while string.endswith("&nbsp;"):
        string = string[:-6]
    while string.startswith("&nbsp;"):
        string = string[6:]
    string = remove_latex_delimiters(string)
    string = remove_math_dollars(string)
    string = string.replace("：", ":")
    string = string.replace(chr(8758), ":")
    string = string.replace("\\text{ }", "")
    string = string.replace("\\mathrm{ }", "")
    string = string.replace("\!", "")
    string = "".join([e for e in string if e != " "])
    string = tidy_gtlteq(string)
    if mode == "std_answer":
        string = tidy_dirty_es(string)
        string = tidy_open_bracket(string)
    return string


def tidy_gtlteq(string):
    math_map = {
        "<": ["&lt;", "\\lt", chr(65308)],
        "=": [chr(65309)],
        ">": ["&gt;", "\\gt", chr(65310)],
        "\\leq": ["\\le", "\\leqslant"],
        "\\geq": ["\\ge", "\\geqslant"],
    }
    reverse_map = grab_reverse(math_map)
    for key in reverse_map:
        if key not in ["\\le", "\\ge"]:
            string = string.replace(key, reverse_map[key][0])
        elif (
            key == "\\le"
            and ("\\leqslant" not in string)
            and ("\\leq" not in string)
            and ("\\left" not in string)
        ):
            string = string.replace(key, reverse_map[key][0])
        elif key == "\\ge" and ("\\geqslant" not in string) and ("\\geq" not in string):
            string = string.replace(key, reverse_map[key][0])
    return string


def edit_ltgteq(content, string):
    is_target = False
    eq_content = tidy_gtlteq(content)
    targets = [">", "<", "\\geq", "leq"]
    for e in targets:
        if e in eq_content:
            is_target = True
    if is_target is False:
        return string
    eq_string = tidy_gtlteq(string)
    gtlteq_map = {
        "<": ["L", "∠", "C", "\\leftarrow", "c", "\\angle"],
        ">": ["7", "J", "\\rightarrow", ")", "?"],
    }
    reverse_map = grab_reverse(gtlteq_map)
    for key in reverse_map:
        eq_string = eq_string.replace(key, reverse_map[key][0])
        if eq_string == eq_content:
            return eq_content
    return string


def is_number_fractions(string):
    """
    判断字符串是否为LaTeX格式的分数形式

    检查字符串是否符合分数格式：可选的符号（±或-）+ 可选的整数部分 + LaTeX分数格式
    例如："\\frac{1}{2}", "-\\frac{3}{4}", "2\\frac{5}{6}", "\\pm\\frac{7}{8}" 等都会返回True

    Args:
        string (str): 待检查的字符串

    Returns:
        bool: 如果是LaTeX分数格式返回True，否则返回False
    """
    pattern = r"^(\\pm|-)?\d*\\frac\{\d+\}\{\d+\}$"
    return bool(re.fullmatch(pattern, string))


def is_just_number(s):
    s = s.strip()  # 去掉前后空格
    if s.startswith(("-", "+")):  # 处理正负号
        s = s[1:]
    return s.replace(".", "", 1).isdigit()  # 最多去掉一个小数点


def is_just_colons(s):
    out = False
    if ":" in s:
        es = s.split(":")
        res = [is_just_number(e) for e in es]
        if False not in res:
            out = True
    return out


def is_latex_fraction(s):
    while s.startswith(" "):
        s = s[1:]
    while s.endswith(" "):
        s = s[:-1]
    pattern = r"^\\frac\{[a-zA-Z0-9]+\}\{[a-zA-Z0-9]+\}$"
    return bool(re.fullmatch(pattern, s))


def convert_to_scientific_notation(num_str):
    try:
        num = int(num_str)
    except ValueError:
        return num_str  # 非数字不处理

    if num == 0:
        return "0"

    n = 0
    temp = abs(num)
    while temp >= 10:
        temp //= 10
        n += 1

    a = num // (10**n)  # 首位数字
    if a * (10**n) == num and n >= 3:  # 必须严格相等且 n ≥ 3
        return f"{a}\\times10^{n}"
    else:
        return num_str  # 不满足条件则不转换


def split_by_llm_answer(answer):
    typ = None
    tidy_string = tidy_content(string)
    if tidy_string in [
        "<",
        ">",
        "=",
        chr(65308),
        chr(65310),
        chr(65309),
        "&lt;",
        "&gt;",
        "+",
        "-",
        "\\geq",
        "\\leq",
    ]:
        typ = "math"
    if contains_latex_formula(string):
        typ = "math"
    if contains_only_chinese(string):
        typ = "chinese"
    if is_just_number(tidy_string):
        typ = "number"
    return typ


def split_by_answers(string):
    tidy_string = tidy_content(string)
    use_mode = "use_tt"
    use_crop = False
    if tidy_string in [
        "<",
        ">",
        "=",
        chr(65308),
        chr(65310),
        chr(65309),
        "&lt;",
        "&gt;",
        "+",
        "-",
        "\\geq",
        "\\leq",
    ]:
        use_mode = "use_paddle_formula"
        return use_mode, use_crop, tidy_string
    if "\\rho_水" in tidy_string and not contains_chinese(
        tidy_string.replace("\\rho_水", "")
    ):
        return use_mode, use_crop, tidy_string

    if (is_just_Uletters(tidy_string) and len(tidy_string) == 1) and tidy_string != "R":
        use_mode = "use_paddle_formula"
        return use_mode, use_crop, tidy_string

    if contains_chinese(string):
        if contains_latex_formula(string):
            use_mode = "use_mathpix"
        else:
            use_mode = "use_baidu"
    if is_just_number(tidy_string):
        # if is_just_number(tidy_string) or is_just_letters(tidy_string):
        use_crop = True
    return use_mode, use_crop, tidy_string


def find_most_common(lst):
    if not lst:  # 如果列表为空
        return None, 0
    counter = Counter(lst)
    max_count = max(counter.values())
    most_common_values = [val for val, cnt in counter.items() if cnt == max_count]
    return most_common_values, max_count


def vote_numbers_without_content(pres, origin_res):
    if not is_just_number(pres):
        return origin_res, False
    nv = origin_res
    reverse_map = {
        "\\geq ": ["3", "2"],
        "\\nu": ["0"],
        "\\cup ": ["0"],
        "u": ["0", "4"],
        "\\sum ": ["2"],
        "c": ["0"],
    }
    sorted_dict = {
        k: v for k, v in sorted(reverse_map.items(), key=lambda x: -len(x[0]))
    }
    for key in sorted_dict:
        for possible_value in sorted_dict[key]:
            temp_nv = nv.replace(key, possible_value)
            # nv = nv.replace(key, sorted_dict[key])
            # if nv == pres:
            if temp_nv == pres:
                return pres, True
    return origin_res, False


def vote_numbers_strategy(pres, origin_res, content):
    if not is_just_number(pres):
        return origin_res
    if is_just_number(pres) and origin_res.replace("-", "", 1) == pres:
        return pres
    if (
        origin_res
        in [
            "i",
            "!",
            "?",
            "x",
            "u",
            "y",
            "s",
            "n",
            "f",
            "k",
            "\\gamma",
            "Y",
            "v",
            "2k",
            "G",
        ]
    ) or ("k" in origin_res):
        return pres
    vlist = [pres, origin_res, content]
    values, count = find_most_common(vlist)
    if pres + "^{\\circ}" == origin_res:
        return origin_res
    if origin_res.endswith("^0"):
        if origin_res[:-2] == content and origin_res[:-2] + "0" == pres:
            return origin_res[:-2] + "^{\\circ}"
    if len(values) == 1:
        return values[0]
    else:
        another, check = vote_numbers_without_content(pres, origin_res)
        if check is True:
            return another
        return origin_res


def vote_chardays_strategy(pres, origin_res, content):
    if origin_res == "":
        return pres
    vlist = [pres, origin_res, content]
    values, count = find_most_common(vlist)
    if len(values) == 1:
        return values[0]
    else:
        return origin_res


def vote_half_strategy(latex, origin_res, content):
    if content in ["一半"]:
        if latex in ["\\frac{1}{2}", "\\frac{1}{z}", "\\frac{1}{Z}"]:
            return latex
    return origin_res


def paddle2chardays(string):
    ppocrv5_days_map = {
        "一": ["-", "_", "—", "…", "）", "～", ")"],
        "二": ["="],
        "四": ["π", "八"],
        "五": ["王", "万"],
        "1": ["|"],
    }

    reverse_map = grab_reverse(ppocrv5_days_map)
    for key in reverse_map:
        string = string.replace(key, reverse_map[key][0])
    return string


def paddle2numbers1(string):
    ppocrv5_numbers_map = {
        "0": ["o", "u", "D", "O", "C", "U"],
        "1": [")", "|", "/", "I", "("],
        "2": ["√", "L", "N", "ユ", "乙", "Z", "d", "∑"],
        "4": [
            "×",
        ],
        "5": ["S", "j", "t", "ち", "厂", "广", "t", "f", "七", "J", "子"],
        "6": ["G"],
        "7": ["T"],
        "00": ["∞"],
        "9": ["a"],
    }
    reverse_map = grab_reverse(ppocrv5_numbers_map)
    if "frac" in string or "\\" in string:
        return string
    elif string == "V":
        return "2"
    else:
        for key in reverse_map:
            string = string.replace(key, reverse_map[key][0])
        if string.endswith("V"):
            string = string[:-1] + "0"
    return string


def paddle2numbers(string):
    paddle_numbers_map = {
        "V": "2",
        "Z": "2",
        "z": "2",
        "?": "3",
        "~": "-",
        "/": "1",
        "(": "1",
        "f": "5",
        "t": "5",
        "u": "0",
        "v": "0",
        "c": "0",
        "l": "1",
        "I": "1",
        "L": "2",
        "g": "8",
        "q": "9",
        "%": "8",
        "d": "2",
        "b": "6",
        "I": "1",
        "D": "0",
        "O": "0",
        "o": "0",
        " ": "",
    }
    if "\\" in string:
        return string
    else:
        outlist = []
        outlist = [paddle_numbers_map.get(e, e) for e in string]
        string = "".join(outlist)
        if string.startswith("U"):
            string = "2" + string[1:]
        elif string.endswith("U"):
            string = string[:-1] + "0"
    return string


def replace_latex_brackets(text):
    # 正则匹配 \left[ 数字 \right] 格式
    pattern = r"\\left\[\s*(\w+)\s*\\right\]"

    # 替换为 \( 数字 \)
    replaced_text = re.sub(pattern, r"\\(\1\\)", text)
    return replaced_text


def replace_boxed_expression(text):
    # 正则匹配 \\boxed{数字} 格式
    # pattern = r"\\boxed\{(\w+)\}"
    pattern = r"\\boxed\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
    pattern1 = r"\\begin\{array\}\{c\}(.*?)\\\\ \\end\{array\}"

    # 替换为数字
    replaced_text = re.sub(pattern, r"\1", text)
    replaced_text = re.sub(pattern1, r"\1", replaced_text)
    return replaced_text


def replace_matrix_expression(text):
    # 正则匹配 \\left[ \\begin{matrix} 数字 \\ \\end{matrix} \\right] 格式
    # pattern = r"\\left\[\s*\\begin{matrix}.*?(\d+).*?\\end{matrix}\s*\\right\]"
    pattern = r"\\left\[\s*\\begin{matrix}.*?(\w+).*?\\end{matrix}\s*\\right\]"

    # 替换为数字
    replaced_text = re.sub(pattern, r"\1", text)
    return replaced_text


def remove_latex_formatting(input_str):
    # 首先，去除最内层的 \\phantom 和 \\rule
    input_str = re.sub(r"\\rule{[^}]*}{[^}]*}", "", input_str)
    input_str = re.sub(r"\\phantom{[^}]*}", "", input_str)

    # 再去除 \\hskip 和 \\mid 等
    input_str = re.sub(r"\\hskip [^ ]*pt", "", input_str)
    input_str = re.sub(r"\\mid", "", input_str)

    return input_str.strip()


def replace_pipe(text):
    if len(text) >= 400:
        text = remove_latex_formatting(text)
    text = replace_matrix_expression(text)
    text = replace_boxed_expression(text)
    text = replace_latex_brackets(text)
    text = text.replace("\\big", "")
    text = text.replace("\\Big", "")
    if text in ["\\vdots", "\\dot", "\\cdot", "、", "\\bullet", "\\prime"]:
        # if text == "\\vdots" or text=="\\dot" or text=="\\cdot":
        text = ""
    return text


def dealwith_cdot(string):
    if string.startswith("\\cdot"):
        string = string[5:]
    if string.endswith("\\cdot"):
        string = string[:-5]
    elif ("\\cdot" in string) and is_just_number(string.replace("\\cdot", ".")):
        string = string.replace("\\cdot", ".")
    return string


def remove_numberdot(string):
    if string.startswith("."):
        return string.lstrip(".").strip()


def remove_overline(string):
    pattern = r"\\overline\{([^}]+)\}"
    replaced_text = re.sub(pattern, r"\1", string)
    return replaced_text


def replacement_(match):
    """
    替换逻辑：
    - 如果 \overline{xxx} 的第一个数字是 1，则替换为 \sqrt{剩余部分}
    - 否则直接返回 xxx
    """
    content = match.group(1)  # 提取 \overline{xxx} 中的内容
    if len(content) >= 1 and content[0] == "1":
        return r"\\sqrt{" + content[1:] + "}"
    else:
        return content


def replace_custom_overlined(text):
    """
    替换文本中的所有 \overline{xxx}：
    - 使用 re.sub() 和外部定义的 replacement 函数
    """
    pattern = r"\\overline\{([^}]+)\}"
    replaced_text = re.sub(pattern, replacement_, text)
    return replaced_text


def remove_dot(string, content):
    pattern = r"\\dot\{([^}]+)\}"
    pattern1 = r"\\overset\{([.]+)\}"
    if re.search(pattern, content):
        return string
    if re.search(pattern1, content):
        return string
    replaced_text = re.sub(pattern, r"\1", string)
    return replaced_text


def replace_with_map(text, replacement_map):
    """
    根据替换映射字典替换文本中的内容

    参数:
        text (str): 要替换的原始文本
        replacement_map (dict): 替换映射字典 {被替换字符串: 替换值}

    返回:
        str: 替换后的文本
    """
    for key, value in replacement_map.items():
        text = text.replace(key, str(value))
    text = text.replace(" ", "")
    return text


def replace_decimal(content, string):
    decimals_candidates = ["、", "-", ",", "，"]
    for e in decimals_candidates:
        new_string = string.replace(e, ".", 1)
        if content == new_string:
            string = new_string
    return string


def strip_nonsense(string):
    while string.startswith("\\left."):
        string = string[6:]
    while string.endswith("\\right."):
        string = string[:-7]
    if (
        string.endswith(".")
        and (not string.endswith("\\right."))
        and (not string.endswith("\\left."))
    ):
        string = string[:-1]
    return string


def compare_strings(A, B):
    """
    检查 B 是否包含 A 的所有字符（按顺序），如果是则返回 A，否则返回 B
    """
    if A == B:
        return A
    if A == "\\(y\\)轴":
        A = "y轴"
    hx_candidates = {"—": "-"}
    for c in hx_candidates:
        if c in B and c not in A:
            B = B.replace(c, hx_candidates[c])
    it = iter(B)  # 转换为迭代器以逐个检查字符
    # 检查 A 的每个字符是否按顺序出现在 B 中
    if all(char in it for char in A):
        missing_chars = [char for char in B if char not in A]
        if len(missing_chars) == 1 and not contains_chinese(missing_chars[0]):
            return A
    similarity_map = ap_config.get_dict("similarity_map", "application")
    candidates_char_pairs = ap_config.get_list("candidates_char_pairs", "application")
    # B = find_best_replacement_optimized_pipe(A, B, similarity_map)
    B = find_best_replacement_optimized_pipe(
        A, B, similarity_map, candidates_char_pairs
    )
    B = remove_duplicate_chinese_chars(A, B)
    return B


def replace_subscripts(text):
    """
    替换 m_{n} → mn 和 -m_{n} → -mn，其中 m, n 是数字
    """
    # 替换 -m_{n} → -mn
    text = re.sub(r"-(\d+)\s*_\s*\{(\d+)\}", r"-\1\2", text)
    # 替换 m_{n} → mn
    text = re.sub(r"(\d+)\s*_\s*\{(\d+)\}", r"\1\2", text)
    return text


def replace_subscripts1(text):
    """
    替换 m_n → mn 和 -m_n → -mn，其中 m, n 是数字
    """
    # 替换 -m_{n} → -mn
    pattern = r"(-?\d)_(\d)"
    text = re.sub(pattern, r"\1\2", text)
    return text


def is_subscripts(text):
    pattern0 = r"-\d+_\d"
    pattern1 = r"\d+_\d"
    return (bool(re.fullmatch(pattern0, text))) or (bool(re.fullmatch(pattern1, text)))


def grab_reverse(map_in):
    reverse_map = {}
    for standard_char, similar_chars in map_in.items():
        for char in similar_chars:
            if char not in reverse_map:
                reverse_map[char] = []
            reverse_map[char].append(standard_char)
    return reverse_map


def just_for_ltgteq(content, string):
    if content in [
        "<",
        ">",
        "=",
        chr(65308),
        chr(65310),
        chr(65309),
        "&lt;",
        "&gt;",
        "大于",
        "等于",
        "小于",
        "\\geq",
        "\\leq",
    ]:
        if string in ["L", "∠", "C", "\\leftarrow", "c", "\\angle"]:
            return "<"
        if string in ["7", "J", "\\rightarrow", ")", "?"]:
            return ">"
        if string in ["二", "\\Xi", "\\sum"]:
            return "="
        if string in ["71"]:
            return "\\geq"
    return string


def just_for_single_Ucase(content, string):
    if content in ["A", "B", "C", "D"]:
        if string in ["("]:
            return "C"
    if content in ["F", "T"]:
        if string in ["7", "I", ",7"]:
            return "T"
        if string in ["f", "T-", "k"]:
            return "F"
    if content in ["J"]:
        if string in ["了", "丁"]:
            return "J"
    return string


def extract_dot_numbers(s):
    if not bool(re.fullmatch(r"\.\d+", s)):
        return s
    match = re.match(r"^\.(\d+)$", s)
    if match:
        return match.group(1)
    else:
        return s


def extract_dot_numbers1(s):
    if not bool(re.fullmatch(r"\d+\.", s)):
        return s
    match = re.match(r"^(\d+)\.$", s)
    if match:
        return match.group(1)
    else:
        return s


def extract_commas(s):
    if s.startswith(","):
        s = s[1:]
    if s.startswith("、"):
        s = s[1:]
    return s


def final_step_withoutcontent(string):
    if string == "P2UI":
        string = "P=UI"
    if string in [
        "P=\\frac{m}{v}",
        "P=\\frac{M}{v}",
        "P=\\frac{m}{V}",
        "e=\\frac{m}{v}",
    ]:
        string = "\\rho=\\frac{m}{v}"
    if string in ["\\rho:"]:
        string = "\\rho"
    if is_use_comma(string):
        string = string.replace(".", ",")
    if string in ["\\vert", "\\mid"]:
        string = "1"
    if "(" in string:
        if string.replace("(", "C") != "C" and is_just_Uletters(
            string.replace("(", "C")
        ):
            string = string.replace("(", "C")
    if "13" in string:
        if string.replace("13", "B") != "B" and is_just_Uletters(
            string.replace("13", "B")
        ):
            string = string.replace("13", "B")
    if "15" in string:
        if string.replace("15", "B") != "B" and is_just_Uletters(
            string.replace("15", "B")
        ):
            string = string.replace("15", "B")
    if string == "\\mu_{m}":
        string = "μm"
    if re.fullmatch(r"\d+\^\{0\}\d+\^\{1\}\d+\^\{11\}", string):
        degrees, minutes, seconds = re.findall(r"(\d+)\^{", string)
        string = (
            degrees
            + "^{\\circ}"
            + minutes
            + "^{\\prime}"
            + seconds
            + "^{\\prime\\prime}"
        )
    string = extract_dot_numbers(string)
    string = extract_dot_numbers1(string)
    string = extract_commas(string)
    return string


def latex_std(string):
    dealwith_vert = ["\\left|", "\\right|"]
    for e in dealwith_vert:
        string = string.replace(e, "|")
    return string


def multi_pattern_replace(text, pattern_dict):
    """
    使用字典中的pattern-value对替换字符串中的所有匹配项

    参数:
        text (str): 要处理的原始字符串
        pattern_dict (dict): 键是正则表达式模式，值是对应的替换字符串

    返回:
        str: 替换后的字符串
    """

    # 逐个替换
    for pattern, replacement in pattern_dict.items():
        if re.search(pattern, text):
            text = re.sub(pattern, replacement, text)
    return text


def latex_textcircled(string):
    pattern = re.compile(r"\\textcircled\{[1-9]\}")
    if not re.search(r"\\textcircled\{[1-9]\}", string):
        return string
    pattern1 = re.compile(r"\\textcircled\{1\}")
    pattern2 = re.compile(r"\\textcircled\{2\}")
    pattern3 = re.compile(r"\\textcircled\{3\}")
    pattern4 = re.compile(r"\\textcircled\{4\}")
    pattern5 = re.compile(r"\\textcircled\{5\}")
    pattern6 = re.compile(r"\\textcircled\{6\}")
    pattern7 = re.compile(r"\\textcircled\{7\}")
    pattern8 = re.compile(r"\\textcircled\{8\}")
    pattern9 = re.compile(r"\\textcircled\{9\}")
    pattern_dict = {
        pattern1: chr(9312),
        pattern2: chr(9313),
        pattern3: chr(9314),
        pattern4: chr(9315),
        pattern5: chr(9316),
        pattern6: chr(9317),
        pattern7: chr(9318),
        pattern8: chr(9319),
        pattern9: chr(9320),
    }
    string = multi_pattern_replace(string, pattern_dict)
    return string


def final_latex_std(string):
    dealwith_vert = ["\\left|", "\\right|"]
    for e in dealwith_vert:
        string = string.replace(e, "|")

    string = latex_textcircled(string)

    latex_formatting = [
        "\\leq",
        "\\geq",
        "\\lt",
        "\\gt",
        "\\neq",
        "\\pm",
        "\\leftarrow",
        "\\rightarrow",
        "\\uparrow",
        "\\downarrow",
        "\\alpha",
        "\\beta",
        "\\gamma",
        "\\sigma",
        "\\omega",
        "\\cdots",
        "\\cdot",
        "\\cap",
        "\\cup",
        "\\theta",
        "\\triangle",
        "\\Delta",
        "\\delta",
        "\\partial",
        "\\times",
        "\\lambda",
        "\\angle",
        "\\varphi",
        "\\Sigma",
        "\\square",
        "\\cos",
        "\\sine",
        "\\sinh",
        "\\sin",
        "\\cosine",
        "\\cosh",
        "\\tanh",
        "\\tan",
        "\\subseteq",
        "\\seubseteqq",
        "\\Subset",
        "\\subset",
        "\\subsetneqq",
        "\\subsetneq",
        "\\pi",
        "\\div",
        "\\phi",
        "\\in",
        "\\infty",
        "\\notin",
        "\\vert",
    ]
    sorted_list = sorted(latex_formatting, key=lambda x: -len(x))
    pattern = r"(" + "|".join(map(re.escape, sorted_list)) + r")"

    # 替换函数，确保每个匹配项只被处理一次
    def replace_match(match):
        return match.group(1) + " "

    # 执行替换
    string = re.sub(pattern, replace_match, string)
    return string


def final_step(content, string):
    if content in [
        "<",
        ">",
        "=",
        chr(65308),
        chr(65310),
        chr(65309),
        "&lt;",
        "&gt;",
        "大于",
        "等于",
        "小于",
        "\\geqslant",
        "\\leqslant",
    ]:
        if string in ["L", "∠", "C", "\\leftarrow", "c", "\\angle"]:
            return "<"
        if string in ["7", "J", "\\rightarrow", ")", "?"]:
            return ">"
        if string in ["二", "\\Xi", "\\sum"]:
            return "="
        if string in ["3"]:
            return "\\geq"
    if content == "2" and string == "=":
        return "二"
    if is_just_colons(content) or is_latex_fraction(content):
        if (
            "=" in string
            and is_just_colons(string.replace("=", ":"))
            and (not string.startswith("="))
        ):
            string = string.replace("=", ":")
    if is_just_colons(content):
        if (
            "i" in string
            and is_just_colons(string.replace("i", ":", 1))
            and (not string.startswith("i"))
        ):
            string = string.replace("i", ":", 1)
    if is_just_colons(content):
        if (
            "!" in string
            and is_just_colons(string.replace("!", ":", 1))
            and (not string.startswith("!"))
        ):
            string = string.replace("!", ":", 1)
    if is_just_Uletters(content) and string == "\\Delta":
        return "A"
    if (
        is_just_Uletters(content)
        and (string in ["13", "15"])
        and (content not in ["F"])
    ):
        return "B"
    if is_just_Uletters(content) and "\\Delta" in string:
        string = string.replace("\\Delta", "A")
    if is_just_Uletters(content) and string.startswith("0"):
        if "O" + string[1:] == content:
            return content
    if is_just_Uletters(content) and is_just_Uletters(string.replace("(", "C")):
        string = string.replace("(", "C")
    if content == "A" and string == "q":
        string = "a"
    if content == "μm" and string in ["um", "\\mu_{m}"]:
        return content
    if (is_just_number(content) or is_number_fractions(content)) and string in [
        ")",
        "(",
        "l",
        "\\backslash",
        "\\vert",
        "\\mid",
        "|",
    ]:
        return "1"
    if is_just_letters(content) and "\\beta" in string:
        string = string.replace("\\beta", "B")
    if is_just_number(content) and (",") in string:
        if is_just_number(string.replace(",", ".", 1)):
            return string.replace(",", ".", 1)
    if is_just_number(content) and ("，") in string:
        if is_just_number(string.replace("，", ".", 1)):
            return string.replace("，", ".", 1)
    if is_just_number(content) and ("、") in string:
        if is_just_number(string.replace("、", ".", 1)):
            return string.replace("、", ".", 1)
    if (
        is_just_number(content)
        and ("v" in string)
        and string.replace("v", "0") == content
    ):
        return content
    if (
        is_just_number(content)
        and ("n" in string)
        and string.replace("n", "0") == content
    ):
        return content
    if content.endswith("\\times") and (string.endswith("x") or string.endswith("X")):
        string = string[:-1] + "\\times"
    # if is_just_number(content) and string.endswith("u") and string[:-1]+"0"==content:
    #    return content
    string = textcircled(content, string)
    string = string.replace("\\psi", "4")
    if (
        is_just_number(content)
        and string.endswith("y")
        and string[:-1] + "9" == content
    ):
        return content
    if is_just_number(content) and string.replace("a", "9", 1) == content:
        return content
    if (
        is_just_number(content)
        and string.endswith("h")
        and string[:-1] + "6" == content
    ):
        return content
    if (
        is_just_number(content)
        and string.startswith("h")
        and "6" + string[1:] == content
    ):
        return content
    if (
        is_just_number(content)
        and "h" in string
        and "6" in content
        and "h" not in content
    ):
        if string.replace("h", "6", 1) == content:
            return content
    if (
        is_just_number(content)
        and string.endswith("V")
        and string[:-1] + "2" == content
    ):
        return content
    if is_just_number(content) and is_just_number(string.replace("L", "2", 1)):
        string = string.replace("L", "2", 1)
    # if is_just_number(content) and string.startswith('\\geq'):
    #    if is_just_number(string[4:]):
    #        string = "2"+string[4:]
    if is_just_number(content) and "\\geq" in string:
        if string.replace("\\geq", "2", 1) == content:
            return content
    if is_just_number(content) and string == "-\\nu":
        return "-2"
    if is_just_number(content) and string == "\\nu":
        return "2"
    if content == "5" and string in ["j", "t", "T", "\\sqrt{}"]:
        string = "5"
    if content == "-5" and string == "-f":
        string = "-5"
    if is_just_number(content) and is_just_number(string.replace("j", "5")):
        string = string.replace("j", "5")
    if is_just_number(content) and string.replace("c", "0") == content:
        return content

    if content == "0" and string == "D":
        string = "0"
    if content in ["A", "B", "C", "D"] and string == "R":
        string = "B"
    if "H" in string and "H" not in content and "4" in content:
        if string.replace("H", "4", 1) == content:
            return content
    if "T" in string and "T" not in content and "5" in content:
        if string.replace("T", "5", 1) == content:
            return content
    if "L" in string and "L" not in content and "2" in content:
        if string.replace("L", "2", 1) == content:
            return content
    if is_just_number_letters(content) and "/" in string:
        if "I" not in content and "l" not in content:
            string = string.replace("/", "1")
    if (
        is_just_number(content)
        and ("(" in string)
        and (")" not in string)
        and ("\\" not in string)
    ):
        if is_just_number(string.replace("(", "", 1)):
            string = string.replace("(", "1", 1)
    if is_pm_candidates(content):
        string = edit_pm_res(content, string)
    if string == "\\geq" and "\\geq" not in content:
        string = "2"
    huo_candidates = ["戈", "式", "成", "戎"]
    for e in huo_candidates:
        if (not contains_chinese(string.replace(e, "", 1))) and (
            string.replace(e, "", 1) != ""
        ):
            string = string.replace(e, "或", 1)
    if "b" in string and ("b" not in content and "6" in content):
        if string.replace("b", "6") == content:
            string = content
    if "z" in string and ("z" not in content and "2" in content):
        if string.replace("z", "2") == content:
            string = content
    if "Z" in string and ("Z" not in content and "2" in content):
        if string.replace("Z", "2") == content:
            string = content
    if "S" in string and ("S" not in content and "5" in content):
        if string.replace("S", "5") == content:
            string = content
    if "s" in string and ("s" not in content and "5" in content):
        if string.replace("s", "5") == content:
            string = content
    if content == "20" and string == "w":
        return content
    if is_just_number(content) and string.replace("w", "00", 1) == content:
        return content
    string = edit_ltgteq(content, string)
    string = edit_letterwithcls(content, string)
    if content == "\\in" and string in ["C", "6", "\\epsilon", "E", "G"]:
        return content
    if content == "\\notin" and string in ["t", "4", "f", "F"]:
        return content
    string = latex_std(string)
    string = degrees_edit(content, string)
    rho_candidates = [
        "P_{3}K",
        "P_{1}k",
        "P-KL",
        "P_{7/2}",
        "P_{2K}",
        "P_{2k}",
        "P_{3K}",
        "P_{3k}",
        "Pek",
        "\\varphi_{2k}",
        "\\beta_{k}",
        "\\beta_{jk}",
        "P_{ik}",
        "\\rho_{ak}",
        "\\rho_{1}",
        "P_{x}",
        "\\beta k",
        "\\rho_{gk}",
        "\\rho_{c}",
        "P_{x}k",
        "\\rho_{jk}",
        "\\rho_{R}",
        "\\rho_{2k}",
        "P_{zk}",
        "P_{2}k",
        "p_{ek}",
        "p_{2k}",
        "\\rho_{zk}",
        "P_{e}k",
        "P_{ck}",
    ]
    if "\\rho_水" in content and not contains_chinese(content.replace("\\rho_水", "")):
        for e in rho_candidates:
            if e in string:
                string = string.replace(e, "\\rho_水")
        if string in ["2k", "7k"]:
            string = "水"
    string = deal_double_cdots(string, content)
    string = final_latex_std(string)
    return string


def deal_double_cdots(string, content):
    answer_pattern = r"\d+\s*\\cdots\s*\\cdots\s*\d+"
    res_pattern = r"(\d+)\s*\\cdots\s*(\d+)"
    if bool(re.fullmatch(answer_pattern, content)) and bool(
        re.fullmatch(res_pattern, string)
    ):
        match = re.search(res_pattern, string)
        num0 = match[1]
        num1 = match[2]
        string = f"{num0}\\cdots\\cdots{num1}"
        return string
    return string


def degrees_edit(content, string):
    if bool(re.fullmatch(r"^\d+°\d+′\d+″$", content)):
        if bool(re.fullmatch(r"\d+\^0", string)):
            number = re.match(r"(\d+)\^0", string).group(1)
            string = number + "^{\\circ}"
        if bool(re.fullmatch(r"\d+\^\{0\}", string)):
            number = re.match(r"(\d+)\^\{0\}", string).group(1)
            string = number + "^{\\circ}"
        if bool(re.fullmatch(r"\d+\^\{1\}", string)):
            number = re.match(r"(\d+)\^\{1\}", string).group(1)
            string = number + "^{\\prime}"

    return string


def final_step_ans(content, string):
    if content in [
        "<",
        ">",
        "=",
        chr(65308),
        chr(65310),
        chr(65309),
        "&lt;",
        "&gt;",
        "大于",
        "等于",
        "小于",
    ]:
        if string in ["L", "∠", "C", "\\leftarrow", "c", "\\angle"]:
            return "<"
        if string in ["7", "J", "\\rightarrow", ")", "?"]:
            return ">"
        if string in ["二", "\\Xi", "\\sum"]:
            return "="
    if content == "2" and string == "=":
        return "二"
    if is_just_colons(content) or is_latex_fraction(content):
        if (
            "=" in string
            and is_just_colons(string.replace("=", ":"))
            and (not string.startswith("="))
        ):
            string = string.replace("=", ":")
    if is_just_Uletters(content) and string == "\\Delta":
        return "A"
    if is_just_Uletters(content) and string in ["13", "15"]:
        return "B"
    if is_just_Uletters(content) and "\\Delta" in string:
        string = string.replace("\\Delta", "A")
    if is_just_Uletters(content) and string.startswith("0"):
        if "O" + string[1:] == content:
            return content
    if is_just_Uletters(content) and "(" in string:
        string = string.replace("(", "C")
    if (is_just_number(content) or is_number_fractions(content)) and string == ")":
        return "1"
    if (is_just_number(content) or is_number_fractions(content)) and string == "(":
        return "1"
    if is_just_letters(content) and "\\beta" in string:
        string = string.replace("\\beta", "B")
    if is_just_number(content) and (",") in string:
        if is_just_number(string.replace(",", ".", 1)):
            return string.replace(",", ".", 1)
    if is_just_number(content) and ("，") in string:
        if is_just_number(string.replace("，", ".", 1)):
            return string.replace("，", ".", 1)
    if is_just_number(content) and ("、") in string:
        if is_just_number(string.replace("、", ".", 1)):
            return string.replace("、", ".", 1)
    if (
        is_just_number(content)
        and ("v" in string)
        and string.replace("v", "0") == content
    ):
        return content
    if (
        is_just_number(content)
        and ("n" in string)
        and string.replace("n", "0") == content
    ):
        return content
    if content.endswith("\\times") and string.endswith("x"):
        string = string[:-1] + "\\times"
    # if is_just_number(content) and string.endswith("u") and string[:-1]+"0"==content:
    #    return content
    # string = textcircled(content, string)
    string = string.replace("\\psi", "4")
    if (
        is_just_number(content)
        and string.endswith("y")
        and string[:-1] + "9" == content
    ):
        return content
    if (
        is_just_number(content)
        and string.endswith("h")
        and string[:-1] + "6" == content
    ):
        return content
    if (
        is_just_number(content)
        and string.startswith("h")
        and "6" + string[1:] == content
    ):
        return content
    if (
        is_just_number(content)
        and "h" in string
        and "6" in content
        and "h" not in content
    ):
        if string.replace("h", "6", 1) == content:
            return content
    if (
        is_just_number(content)
        and string.endswith("V")
        and string[:-1] + "2" == content
    ):
        return content
    if is_just_number(content) and is_just_number(string.replace("L", "2", 1)):
        string = string.replace("L", "2", 1)
    if is_just_number(content) and string.startswith("\\geq"):
        if is_just_number(string[4:]):
            string = "2" + string[4:]
    if is_just_number(content) and "\\geq" in string:
        if string.replace("\\geq", "2", 1) == content:
            return content
    if is_just_number(content) and string == "-\\nu":
        return "-2"
    if is_just_number(content) and string == "\\nu":
        return "2"
    if content == "5" and string in ["j", "t", "T"]:
        string = "5"
    if content == "-5" and string == "-f":
        string = "-5"
    if is_just_number(content) and is_just_number(string.replace("j", "5")):
        string = string.replace("j", "5")
    if content == "0" and string == "D":
        string = "0"
    if content in ["A", "B", "C", "D"] and string == "R":
        string = "B"
    if "H" in string and "H" not in content and "4" in content:
        if string.replace("H", "4", 1) == content:
            return content
    if "T" in string and "T" not in content and "5" in content:
        if string.replace("T", "5", 1) == content:
            return content
    if "L" in string and "L" not in content and "2" in content:
        if string.replace("L", "2", 1) == content:
            return content
    if is_just_number_letters(content) and "/" in string:
        if "I" not in content and "l" not in content:
            string = string.replace("/", "1")
    if is_pm_candidates(content):
        string = edit_pm_res(content, string)
    if string == "\\geq" and "\\geq" not in content:
        string = "2"
    huo_candidates = ["戈", "式", "成", "戎"]
    for e in huo_candidates:
        if not contains_chinese(string.replace(e, "", 1)):
            string = string.replace(e, "或", 1)
    if "b" in string and ("b" not in content and "6" in content):
        if string.replace("b", "6") == content:
            string = content
    if "z" in string and ("z" not in content and "2" in content):
        if string.replace("z", "2") == content:
            string = content
    if "Z" in string and ("Z" not in content and "2" in content):
        if string.replace("Z", "2") == content:
            string = content
    if "S" in string and ("S" not in content and "5" in content):
        if string.replace("S", "5") == content:
            string = content
    if "s" in string and ("s" not in content and "5" in content):
        if string.replace("s", "5") == content:
            string = content
    if content == "20" and string == "w":
        return content
    if is_just_number(content) and string.replace("w", "00", 1) == content:
        return content
    rho_candidates = [
        "P_{3}K",
        "P-KL",
        "P_{7/2}",
        "P_{2K}",
        "P_{2k}",
        "P_{3K}",
        "P_{3k}",
    ]
    if "\\rho_水" in content and not contains_chinese(content.replace("\\rho_水", "")):
        for e in rho_candidates:
            if e in string:
                string = string.replace(e, "\\rho_水")
    return string


def edit_ocr_result_bytopic(content, ocr_result, topic, child_index):
    key = f"{topic}_{child_index}"
    candidates_map = {"6734407_3": ["A", "B", "C", "D"]}
    pattern_candidates_map = {
        "6969484_0": {
            "result_pattern": r"\d+\\pi",
            "content_pattern": r"\d+",
            "replace_pattern": {"\\pi": "元"},
        },
        "6969484_1": {
            "result_pattern": r"\d+\\pi",
            "content_pattern": r"\d+",
            "replace_pattern": {"\\pi": "元"},
        },
    }
    if (key not in candidates_map) and (key not in pattern_candidates_map):
        return ocr_result
    replace_candidates = {"p": "D", "P": "D"}
    if key in candidates_map:
        if ocr_result not in candidates_map[key]:
            for e in replace_candidates:
                if (
                    ocr_result.replace(e, replace_candidates[e], 1)
                    in candidates_map[key]
                ):
                    ocr_result = ocr_result.replace(e, replace_candidates[e], 1)
    if key in pattern_candidates_map:
        if bool(
            re.fullmatch(pattern_candidates_map[key]["result_pattern"], ocr_result)
        ) and bool(
            re.fullmatch(pattern_candidates_map[key]["content_pattern"], content)
        ):
            operate_map = pattern_candidates_map[key]["replace_pattern"]
            for okey in operate_map:
                ocr_result = ocr_result.replace(okey, operate_map[okey])
    return ocr_result


def remove_all_duplicates(input_string):
    # pdb.set_trace()
    # 匹配所有 \textcircled{数字}
    matches = re.findall(r"\\textcircled\{[1-9]\}", input_string)
    # 用集合去重，并保持顺序
    unique_matches = []
    seen = set()
    for m in matches:
        if m not in seen:
            unique_matches.append(m)
            seen.add(m)
    # 重新组合成字符串
    return "".join(unique_matches)


def replace_left_right_circled(input_string):
    """
    将 \left(\textcircled{数字}\right) 替换为 \textcircled{数字}
    """
    pattern = re.compile(r"\\left\(\\textcircled\{([1-9])\}\\right\)")
    replaced_string = pattern.sub(r"\\textcircled{\1}", input_string)
    return replaced_string


def textcircled(contetnt, string):
    characters = [
        chr(9312),
        chr(9313),
        chr(9314),
        chr(9315),
        chr(9316),
        chr(9317),
        chr(9318),
        chr(9319),
        chr(9320),
    ]
    pattern = re.compile(r"\\textcircled\{[1-9]\}")
    pattern0 = re.compile(r"(?<!\d)(?<!\\textcircled\{)0(?!\d)(?!\})")
    pattern1 = re.compile(r"(?<!\d)(?<!\\textcircled\{)1(?!\d)(?!\})")
    pattern2 = re.compile(r"(?<!\d)(?<!\\textcircled\{)2(?!\d)(?!\})")
    pattern3 = re.compile(r"(?<!\d)(?<!\\textcircled\{)3(?!\d)(?!\})")
    pattern4 = re.compile(r"(?<!\d)(?<!\\textcircled\{)4(?!\d)(?!\})")
    pattern5 = re.compile(r"(?<!\d)(?<!\\textcircled\{)5(?!\d)(?!\})")
    pattern6 = re.compile(r"(?<!\d)(?<!\\textcircled\{)6(?!\d)(?!\})")
    pattern7 = re.compile(r"(?<!\d)(?<!\\textcircled\{)7(?!\d)(?!\})")
    pattern8 = re.compile(r"(?<!\d)(?<!\\textcircled\{)8(?!\d)(?!\})")
    pattern9 = re.compile(r"(?<!\d)(?<!\\textcircled\{)9(?!\d)(?!\})")
    for e in characters:
        if e in contetnt:
            string = string.replace("\\textcircled{<}", "\\textcircled{2}")
            string = string.replace("\\textcircled{>}", "\\textcircled{2}")
            res_string = pattern.sub("", string)
            if res_string != "":
                string = pattern0.sub(r"\\textcircled{1}", string)
                string = pattern1.sub(r"\\textcircled{1}", string)
                string = pattern2.sub(r"\\textcircled{2}", string)
                string = pattern3.sub(r"\\textcircled{3}", string)
                string = pattern4.sub(r"\\textcircled{4}", string)
                string = pattern5.sub(r"\\textcircled{5}", string)
                string = pattern6.sub(r"\\textcircled{6}", string)
                string = pattern7.sub(r"\\textcircled{7}", string)
                string = pattern8.sub(r"\\textcircled{8}", string)
                string = pattern9.sub(r"\\textcircled{9}", string)
                string = replace_left_right_circled(string)
            res_string = pattern.sub("", string)
            if res_string == "":
                string = remove_all_duplicates(string)
    return string


def edit_ocr_result(content, ocr_result):
    replacement_map = {
        "b": "6",
        "z": "2",
        "Z": "2",
        "s": "5",
        "S": "5",
        "o": "0",
        "q": "9",
        "l": "1",
    }
    replacement_map1 = {"\\alpha": 2, "\\delta": 8, "J": "5"}

    tidy_ocr_result = tidy_content(ocr_result, mode="ocr_result")
    # if is_just_number(content) or is_just_number(content.replace(":", "", 1)) or is_just_number(content.replace("：","",1)) or is_just_number(content.replace(chr(8758), "", 1)):
    if is_just_number(content) or is_just_colons(content):
        tidy_ocr_result = replace_with_map(tidy_ocr_result, replacement_map1)
    if content.endswith(chr(176)) and (
        tidy_ocr_result.endswith("^{0}")
        or tidy_ocr_result.endswith("^{o}")
        or tidy_ocr_result.endswith("^{c}")
    ):
        tidy_ocr_result = tidy_ocr_result[:-4] + chr(176)
    if (content.endswith("^{\\circ}") or content.endswith("^\\circ")) and (
        tidy_ocr_result.endswith("^{0}")
        or tidy_ocr_result.endswith("^{o}")
        or tidy_ocr_result.endswith("^{c}")
    ):
        tidy_ocr_result = tidy_ocr_result[:-4] + "^{\\circ}"
    if (
        content.endswith(chr(176))
        or content.endswith("^{\\circ}")
        or content.endswith("^\\circ")
    ) and (tidy_ocr_result.endswith("^0") or tidy_ocr_result.endswith("^o")):
        tidy_ocr_result = tidy_ocr_result[:-2] + "^{\\circ}"
    # if not contains_letters(content) and contains_letters(tidy_ocr_result) and not (contains_latex_formula(tidy_ocr_result)):
    if (
        ((not contains_letters(content)) or is_number_fractions(content))
        and contains_letters(tidy_ocr_result)
        and not (contains_latex_formula(tidy_ocr_result))
    ):
        if content != "111":
            corrected_ocr_result = []
            # for char in tidy_ocr_result:
            for char_idx in range(len(tidy_ocr_result)):
                char = tidy_ocr_result[char_idx]
                if tidy_ocr_result[char_idx - 2 : char_idx + 2] == "^{o}":
                    corrected_ocr_result.append(char)
                else:
                    corrected_ocr_result.append(replacement_map.get(char, char))
            tidy_ocr_result = "".join(corrected_ocr_result)
    if (is_just_number(content) or content == "\\frac{\\pi}{3}") and (
        tidy_ocr_result.endswith("^o") and is_just_number(tidy_ocr_result[:-2])
    ):
        tidy_ocr_result = tidy_ocr_result[:-2] + "^{\\circ}"
    if (is_just_number(content) or content == "\\frac{\\pi}{3}") and (
        tidy_ocr_result.endswith("^{o}") and is_just_number(tidy_ocr_result[:-4])
    ):
        tidy_ocr_result = tidy_ocr_result[:-4] + "^{\\circ}"
    if (
        is_just_number(content)
        and content.endswith("0")
        and tidy_ocr_result.endswith("^{0}")
    ):
        tidy_ocr_result = edit_numwithcls(content, tidy_ocr_result)
    if is_just_number(content) and "_{" in tidy_ocr_result:
        tidy_ocr_result = replace_subscripts(tidy_ocr_result)
    if is_just_number(content) and is_subscripts(tidy_ocr_result):
        tidy_ocr_result = replace_subscripts1(tidy_ocr_result)
    if (content == "1" or content == "-1") and tidy_ocr_result in ["!", "/", "|", "i"]:
        return "1"
    if is_just_number(content) and "/" in tidy_ocr_result:
        tidy_ocr_result = tidy_ocr_result.replace("/", "1")
    tidy_ocr_result = strip_nonsense(tidy_ocr_result)

    if (
        (is_just_number(content) or is_number_fractions(content))
        and "|" in tidy_ocr_result
        and ("\\left|" not in tidy_ocr_result)
        and ("\\right|" not in tidy_ocr_result)
    ):
        return tidy_ocr_result.replace("|", "1")
    tidy_ocr_result = remove_dot(tidy_ocr_result, content)
    tidy_ocr_result = dealwith_cdot(tidy_ocr_result)
    tidy_ocr_result = replace_custom_overlined(tidy_ocr_result)
    if is_just_number(content) and "." in content:
        tidy_ocr_result = replace_decimal(content, tidy_ocr_result)
    tidy_ocr_result = final_step(content, tidy_ocr_result)
    tidy_ocr_result = final_step_withoutcontent(tidy_ocr_result)
    return tidy_ocr_result


def edit_ocr_result_ans(content, ocr_result):
    replacement_map = {
        "b": "6",
        "z": "2",
        "Z": "2",
        "s": "5",
        "S": "5",
        "o": "0",
        "q": "9",
        "l": "1",
    }
    replacement_map1 = {"\\alpha": 2, "\\delta": 8, "J": "5"}

    tidy_ocr_result = tidy_content(ocr_result)
    # if is_just_number(content) or is_just_number(content.replace(":", "", 1)) or is_just_number(content.replace("：","",1)) or is_just_number(content.replace(chr(8758), "", 1)):
    if is_just_number(content) or is_just_colons(content):
        tidy_ocr_result = replace_with_map(tidy_ocr_result, replacement_map1)
    if content.endswith(chr(176)) and (
        tidy_ocr_result.endswith("^{0}")
        or tidy_ocr_result.endswith("^{o}")
        or tidy_ocr_result.endswith("^{c}")
    ):
        tidy_ocr_result = tidy_ocr_result[:-4] + chr(176)
    if (content.endswith("^{\\circ}") or content.endswith("^\\circ")) and (
        tidy_ocr_result.endswith("^{0}")
        or tidy_ocr_result.endswith("^{o}")
        or tidy_ocr_result.endswith("^{c}")
    ):
        tidy_ocr_result = tidy_ocr_result[:-4] + "^{\\circ}"
    if (
        content.endswith(chr(176))
        or content.endswith("^{\\circ}")
        or content.endswith("^\\circ")
    ) and (tidy_ocr_result.endswith("^0") or tidy_ocr_result.endswith("^o")):
        tidy_ocr_result = tidy_ocr_result[:-2] + "^{\\circ}"
    # if not contains_letters(content) and contains_letters(tidy_ocr_result) and not (contains_latex_formula(tidy_ocr_result)):
    if (
        ((not contains_letters(content)) or is_number_fractions(content))
        and contains_letters(tidy_ocr_result)
        and not (contains_latex_formula(tidy_ocr_result))
    ):
        corrected_ocr_result = []
        # for char in tidy_ocr_result:
        for char_idx in range(len(tidy_ocr_result)):
            char = tidy_ocr_result[char_idx]
            if tidy_ocr_result[char_idx - 2 : char_idx + 2] == "^{o}":
                corrected_ocr_result.append(char)
            else:
                corrected_ocr_result.append(replacement_map.get(char, char))
        tidy_ocr_result = "".join(corrected_ocr_result)
    if (
        is_just_number(content)
        and content.endswith("0")
        and tidy_ocr_result.endswith("^{0}")
    ):
        tidy_ocr_result = edit_numwithcls(content, tidy_ocr_result)
    if is_just_number(content) and "_{" in tidy_ocr_result:
        tidy_ocr_result = replace_subscripts(tidy_ocr_result)
    if is_just_number(content) and is_subscripts(tidy_ocr_result):
        tidy_ocr_result = replace_subscripts1(tidy_ocr_result)
    if (content == "1" or content == "-1") and tidy_ocr_result in ["!", "/", "|", "i"]:
        return "1"
    if is_just_number(content) and "/" in tidy_ocr_result:
        tidy_ocr_result = tidy_ocr_result.replace("/", "1")
    if (
        is_just_number(content) or is_number_fractions(content)
    ) and "|" in tidy_ocr_result:
        return tidy_ocr_result.replace("|", "1")
    tidy_ocr_result = remove_dot(tidy_ocr_result, content)
    tidy_ocr_result = dealwith_cdot(tidy_ocr_result)
    tidy_ocr_result = replace_custom_overlined(tidy_ocr_result)
    if is_just_number(content) and "." in content:
        tidy_ocr_result = replace_decimal(content, tidy_ocr_result)
    tidy_ocr_result = strip_nonsense(tidy_ocr_result)
    tidy_ocr_result = final_step_ans(content, tidy_ocr_result)
    return tidy_ocr_result


def match_fractions(raw_result, ocr_result):
    same = False
    pa = r"\\frac\{(\d+)\}\{(\d+)\}$"
    if bool(re.fullmatch(pa, raw_result)):
        match = re.search(pa, raw_result)
        up = match[3]
        down = match[4]
        join = f"{str(up)}/{str(down)}"
        if join == ocr_result:
            same = True
            return same
    return same


def is_ocr_equation(ocr_answer):
    """
    判断OCR识别的答案是否为方程形式

    检查答案是否符合方程格式：任意字符 + 等号 + 数字结尾
    例如："x=5", "2x+3=7", "y=123" 等都会返回True

    Args:
        ocr_answer (str): OCR识别的答案字符串

    Returns:
        bool: 如果是方程形式返回True，否则返回False
    """
    pa = "^.*?=\d+$"
    if bool(re.fullmatch(pa, ocr_answer)):
        return True
    return False


def mask_stem(stem: str) -> str:
    """
    模糊题干中的数字，将所有数字替换成"*"。
    先对数字进行替换（每个数字字符替换成对应数量的"*"号），
    注意：题号形式（如"(1)"、"（1）"等）不会被模糊处理。

    Args:
        stem (str): 题干字符串

    Returns:
        str: 替换后的题干字符串
    """

    # 保护题号：匹配半角括号 (1) 或全角括号 （1） 中的数字
    # 使用临时占位符来保护题号
    question_number_pattern = r"[（(](\d+)[）)]"
    placeholders = {}
    placeholder_counter = 0

    def replace_with_placeholder(match):
        nonlocal placeholder_counter
        placeholder = f"__QUESTION_NUMBER_{placeholder_counter}__"
        placeholders[placeholder] = match.group(0)  # 保存原始题号
        placeholder_counter += 1
        return placeholder

    # 第一步：用占位符替换所有题号
    protected_stem = re.sub(question_number_pattern, replace_with_placeholder, stem)

    # 第二步：替换数字，每个数字字符替换成对应数量的"*"号
    def replace_digits(match):
        return "*" * len(match.group())

    result = re.sub(r"\d+", replace_digits, protected_stem)

    # 第三步：将占位符还原为原始题号
    for placeholder, original in placeholders.items():
        result = result.replace(placeholder, original)

    return result


def reedit_by_multi_results(raw_stu_answers, tidy_es_answers, ocr_answers):
    try:

        es_answer = tidy_es_answers[0]
        stu_answer = raw_stu_answers[0]

        if len(ocr_answers) == 1:
            if "\n" in ocr_answers[0]:
                return raw_stu_answers
            if ocr_answers[0].count(es_answer) == 0:
                if not match_fractions(stu_answer, ocr_answers[0]):
                    if (not is_number_fractions(es_answer)) and (
                        not is_ocr_equation(ocr_answers[0])
                    ):
                        # if ocr_answers[0] != es_answer:
                        return ocr_answers
        return raw_stu_answers
    except Exception as e:
        return raw_stu_answers


def reedit_by_multi_results1(raw_stu_answers, tidy_es_answers, ocr_answers):
    try:

        es_answer = tidy_es_answers[0]
        stu_answer = raw_stu_answers[0]

        if len(ocr_answers) == 1:
            if "\n" in ocr_answers[0]:
                return raw_stu_answers
            ocr_answer = ocr_answers[0]
            ocr_answer = remove_latex_delimiters(ocr_answer)
            ocr_answer = remove_math_dollars(ocr_answer)
            if ocr_answer == es_answer:
                if not match_fractions(stu_answer, ocr_answer):
                    return ocr_answers
        return raw_stu_answers
    except Exception as e:
        return raw_stu_answers


def reedit_by_multi_results2(raw_stu_answers, tidy_es_answers, ocr_answers):
    try:
        if raw_stu_answers == tidy_es_answers:
            if ocr_answers == [""]:
                return [""] * len(tidy_es_answers)
        return raw_stu_answers
    except Exception as e:
        return raw_stu_answers


# print(edit_ocr_result('6','b'))
# 示例文本
# text = "This is a test: \\left[ \\begin{matrix} 6 \\\\ \\end{matrix} \\right] and \\left[ \\begin{matrix} 42 \\\\ \\end{matrix} \\right]."
# text = "\\left[ \\begin{matrix} 6 \\\\ \\hline \\end{matrix} \\right]"
# text='\\left[ \\begin{matrix} q \\\\ \\hline \\end{matrix} \\right]'
# text = "This is a test: \\left[ 7 \\right]."
# text = '\\left[ \\begin{matrix} 6 \\\\ \\end{matrix} \\right]'
# text = '\\boxed{6}'
# text = "j\u00ec\u5b63ji\u00e9\u8282g\u014dng\u5de5&nbsp;\sqrt(5)"
# text = '\u2460\u2461\u2462\u2463\u2464'
# text = '\\boxed{\\phantom{\\rule{0.0pt}{12.9pt}}\\boxed{4}\\rule{0.0pt}{12.9pt}}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\hskip 14.226378pt\\mid \\phantom{\\rule{0.0pt}{12.9pt}}\\rule{0.0pt}{12.9pt}\\rule{0.0pt}{12.9pt}}'
# text = '\\rule{0.0pt}{12.9pt}'
# print (contains_chinese(text))
# print ("text:", text)
# print ("text length: ", len(text))
#
## 替换并输出
# new_text = replace_latex_brackets(text)
# print(text)
# print(split_by_answers(text))
# 示例文本
# print ("text:", text)

# 替换并输出
# new_text = replace_latex_brackets(text)
# new_text = replace_pipe(text)
# pdb.set_trace()
# print (f"new_text: {new_text}")
# new_text = replace_pipe(text)
# print(new_text)

# 测试
# test_cases = ["6000", "500", "12345", "7000", "70", "0", "-8000", "abc"]
# for s in test_cases:
#    print(f"输入: {s} → 输出: {convert_to_scientific_notation(s)}")
# 测试
# print (remove_overline('\\overline{uineiw}78jeo'))
# print (replace_custom_overlined('\\overline{1uineiw}78jeo'))
# string = '\\boxed{\\begin{array}{c}0\\\\\\end{array}}'
# pdb.set_trace()

# print (replace_pipe(string))
# print (is_just_letters('A'))
if __name__ == "__main__":
    test_strings = [
        "选项A,选项B,(-3,4),$f(x,y)$,普通分割",
        "简单,测试,没有公式",
        "在\\(1,2\\)中不分割,但这里要分割,$\\frac{a,b}{c}$也不分割",
        "多重((1,2),3),分割测试",
    ]

    for test in test_strings:
        print(f"输入: {test}")
        print(f"输出: {smart_split_answers_v2(test)}")
        print()
