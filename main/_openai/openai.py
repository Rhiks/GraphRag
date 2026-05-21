import requests
import json
import base64
import os
import time


class DataExtractionError(Exception):
    pass


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def send_request(url, headers, data, max_retries=1):
    retries = 0
    while retries <= max_retries:
        try:
            response = requests.post(
                url, headers=headers, data=json.dumps(data), timeout=90
            )
            response.raise_for_status()  # 如果状态码不是200-299，将会抛出HTTPError
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")  # 打印HTTP错误信息
            print(f"Response body: {response.text}")  # 打印响应体
        except requests.exceptions.RequestException as req_err:
            print(f"Other error occurred: {req_err}")  # 打印其他错误信息
        retries += 1
        if retries <= max_retries:
            print(f"Retrying... ({retries}/{max_retries})")

    raise Exception(f"All {max_retries + 1} attempts have failed")


def completions(
    messages,
    model="claude-3-7-sonnet-20250219",
    url="https://one-api.aixuexiyouxuan.com/v1/chat/completions",
    api_key="sk-REPLACE_ME",
    stream=False,
    temperature=0.0,
):

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
        "stream": stream,
    }
    try:
        result = send_request(url, headers, data)
        print("Request succeeded:", result)
        return result
    except Exception as e:
        print(f"Final failure: {e}")


def request_llm(path, img_name, img_ori_name):
    # response = query_topic(img_name)
    response = None

    # 提取数据并赋值给相应变量
    if response is not None:
        question = response.get("question", "")
        answer_options = response.get("answer_options", [{}])[0].get("text", "")
        analysis = response.get("analysis", "")
        # difficulty = str(response.get("difficulty", ""))  # 转换为字符串类型

        text_system = f"""
        # 角色
        你是一个专业的手写作业内容识别者，请识别学生作业的手写体内容（其中可能包含中文和数学符号），并对作业进行得分分析。
        识别到的数学公式使用 latex 语法表示，内联数学模式使用$作为界定符，显示数学模式使用$$作为界定符。

        ## 技能
        ### 技能1：识别手写内容
        - 洞察学生的手写作业，拆解作业中的手写体内容（包括中文和数学符号）。 
        - 识别到的字符数少于10个，得分为0分。

        ### 技能2：作业得分分析
        - 深度分析学生手写作业，提供分数评估。
        - 严格分析题目答案是否正确，如果不是题目答案（比如照抄原题、书写与题目无关内容等），得分为0分。
        - 如果题目有多个提问，每问得分占比相同，答对一问得相应比例分数。例如，4问每问0.25分，答对2问得0.5分，答对1问得0.25分，全部答错得分为 0。
        - 如果是计算题，只要最后计算结果正确即可，得分 1，注意需要遵循多问的规则。
        - 分数范围在0-1之间。

        ### 技能3：判题依据与解析
        - 识别到的内容内不得掺杂自己的理解，不能抄袭原题和答案作为识别内容。
        - 可结合「题干」「题目答案」「解析」作为判题依据上下文（如果有的话）。

        ### 题目信息
        - 这道题的题目为{question}，标准答案为{answer_options}，答案解析为{analysis}。

        ## 约束条件
        - 不讨论非作业相关的题目或内容，只输出识别和得分。  
        - 使用用户提供的语言（简体中文）作为输出语言。
        - 除了图片内容外，无需多余解释。
        - 不可将「题干」「题目答案」「解析」等内容作为答案直接参考，只能作为判题依据上下文。
        - 如果识别到的内容信息量不做或者与提问信息无关。识别输出请认真书写哦～，得分输出0分。
        - 识别中如果含有latex公式，内联数学模式使用$作为界定符，显示数学模式使用$$作为界定符。

        ## 输出格式限定
        - 输出内容严格按照下面的规范，不得添加其他内容：
        **识别：** <识别到的手写内容>
        **得分：** <分析出的得分>
        **解析：** <分析给分的原因>
        """
    else:
        answer_options = ""
        text_system = f"""
        # 角色
        你是一个专业的手写作业内容识别者，请识别学生作业的手写体内容（其中可能包含中文和数学符号），并对作业进行得分分析。
        识别到的数学公式使用 latex 语法表示，内联数学模式使用$作为界定符，显示数学模式使用$$作为界定符。

        ## 技能
        ### 技能1：识别手写内容
        - 洞察学生的手写作业当中的填空题，识别填空题横线上的手写体内容（包括中文和数学符号）
        - 填空题每一空的识别结果都要输出，如果那一空没有填写答案或者书写潦草难以识别，也要输出“”空字符串
        - 识别到的字符数少于10个，得分为0分。
        - 只识别填空题横线上的手写做内容，不要识别非填空题横线上的内容，不要识别题干下面的草稿或者详细解答详情

        ### 技能2：作业得分分析
        - 深度分析学生手写作业，提供分数评估。
        - 严格分析题目答案是否正确，正确得分为1， 错误得分为0。

        ### 技能3：判题依据与解析
        - 识别到的内容内不得掺杂自己的理解，不能抄袭原题和答案作为识别内容。
        - 可结合「题干」「题目答案」「解析」作为判题依据上下文（如果有的话）。

        ## 约束条件
        - 不讨论非作业相关的题目或内容，只输出识别和得分。
        - 使用用户提供的语言（简体中文）作为输出语言。
        - 不可将「题干」「题目答案」「解析」等内容作为答案直接参考，只能作为判题依据上下文。
        - 如果识别到的内容信息量不做或者与提问信息无关。识别输出请认真书写哦～，得分输出0分。
        - 识别中如果含有latex公式，内联数学模式使用$作为界定符，显示数学模式使用$$作为界定符。

        ## 输出格式限定
        - 输出内容严格按照下面的规范，不得添加其他内容, 不得添加其他内容：
        **识别：** <识别到的填空题第一空手写答案,<识别到的填空题第二空手写答案>,<识别到的填空题第三空手写答案>, ...
        **得分：** <填空题第一空的得分>, <填空题第二空的得分>, <填空题第三空的得分>，...
        **解析：** <解析>
        """

    text_role = f"""
    请识别填空题横线上手写答案内容（中文和数学符号），并使用 LaTeX 语法表示数学公式。给出填空题题干的解析并对学生答案打分：
    - 只识别填空题横线上的手写内容，不识别题干下面其他的作答内容或草稿
    - 输出格式：
    {"answers":["answer1", "answer2", "answer3", ...],
     "scores":[0, 1, 1, ...],
     "analysis":""}

    """

    base64_image = encode_image(f"{path}{img_ori_name}.jpg")
    messages = [
        {"role": "system", "content": [{"type": "text", "text": text_system}]},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text_role},
                {
                    "type": "image_url",
                    # 需要注意，传入Base64，图像格式（即image/{format}）需要与支持的图片列表中的Content Type保持一致。"f"是字符串格式化的方法。
                    # PNG图像：  f"data:image/png;base64,{base64_image}"
                    # JPEG图像： f"data:image/jpeg;base64,{base64_image}"
                    # WEBP图像： f"data:image/webp;base64,{base64_image}"
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                        # "url": "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/17422091449919801246.1742209144954.jpg"
                    },
                },
            ],
        },
    ]
    return messages, answer_options


def extract_prefix(filename):
    # 使用 `split` 分割字符串，并提取第一个元素
    return filename.split("_")[0]


def main():
    model_list = [
        # "claude-3-7-sonnet-latest",
        # "claude-3-5-sonnet-latest",
        "gemini-3-flash-preview",
        # "gemini-2.0-flash-exp",
        # "gemini-1.5-pro",
        # "qwen-vl-max-latest",
        # "qvq-72b-preview"
        # "gpt-4o",
        # "qwen3-vl-plus",
    ]
    # path = "./answers_ocr/dataset/"
    path = "/"
    output_json_name = "output_gpt4o.json"
    i = 56
    for img in os.listdir(path):
        i += 1
        if not img.endswith(".jpg"):
            continue
        img_name = img.split("_")[0]
        img_ori_name = img.split(".")[0]
        print("img_name = ", img_name)
        messages, answers_options = request_llm(path, img_name, img_ori_name)
        for model in model_list:
            start_time = time.time()
            print("model = ", model)
            if model == "qvq-72b-preview" or model == "qwen-vl-max-latest":
                url = "https://one-api.aixuexi.com/v1/chat/completions"
                api_key = "sk-REPLACE_ME"
            else:
                url = "https://one-api.aixuexiyouxuan.com/v1/chat/completions"
                api_key = "sk-REPLACE_ME"
            response = completions(
                messages=messages, model=model, url=url, api_key=api_key
            )
            print("response = ", response)
            if response is None:
                print("response为空")
                end_time = time.time()
                time_all = end_time - start_time
                formatted_data = {
                    "id": i,
                    "question_id": img_ori_name,
                    "result": [
                        {
                            "model": model,
                            "time": time_all,
                            "content": "content为空",
                            "answers": answers_options,
                        }
                    ],
                }
                with open(output_json_name, "a", encoding="utf-8") as f:
                    f.write(json.dumps(formatted_data, ensure_ascii=False) + "\n")
                continue
            else:
                try:
                    # 提取 content 的内容之前进行检查
                    if "choices" not in response or len(response["choices"]) == 0:
                        raise DataExtractionError("Choices 列表不存在或为空")

                    content_value = response["choices"][0]["message"]["content"]
                    end_time = time.time()
                    time_all = end_time - start_time
                    formatted_data = {
                        "id": i,
                        "question_id": img_ori_name,
                        "result": [
                            {
                                "model": model,
                                "time": time_all,
                                "content": content_value,
                                "answers": answers_options,
                            }
                        ],
                    }
                    with open(output_json_name, "a", encoding="utf-8") as f:
                        f.write(json.dumps(formatted_data, ensure_ascii=False) + "\n")

                except DataExtractionError as e:
                    print(f"数据提取错误: {e}")
                except KeyError as e:
                    print(f"键错误: 缺少键 {e}")


if __name__ == "__main__":
    main()
