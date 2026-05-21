import requests
import json
import base64
from typing import List, Dict, Union, Optional
from requests.exceptions import Timeout
import pdb
import concurrent.futures

from constants.model_names import GEMINI_3_FLASH

# Few-shot 示例（与正式请求相同的输出风格；仅 GEMINI 路径注入）
_FEW_SHOT_EXAMPLE_IMAGE = (
    "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/"
    "1774682299146_19_7887974.1774682299138.jpg"
)
_FEW_SHOT_ASSISTANT = (
    "- 定位作答区: 横线上方手写迹\n"
    "- 特征: 清晰\n"
    "- 结果: 3598"
)

def encode_image_to_base64(image_path: str) -> str:
    """将本地图片编码为base64格式"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def create_image_message(
    text: str, images: Optional[List[Union[str, Dict]]] = None
) -> Dict:
    """
    创建支持图片的消息

    Args:
        text: 文本内容
        images: 图片列表，可以是：
               - 本地文件路径字符串
               - URL字符串
               - {"type": "base64", "data": "base64_string"}
               - {"type": "url", "url": "http://..."}
    """
    content = [{"type": "text", "text": text}]

    if images:

        for image in images:
            print(f"image is {image}")
            if isinstance(image, str):
                if image.startswith(("http://", "https://")):
                    # URL图片
                    content.append({"type": "image_url", "image_url": {"url": image}})
                else:
                    # 本地图片文件
                    base64_image = encode_image_to_base64(image)
                    # 根据文件扩展名确定MIME类型
                    if image.lower().endswith(".png"):
                        mime_type = "image/png"
                    elif image.lower().endswith(".jpg") or image.lower().endswith(
                        ".jpeg"
                    ):
                        mime_type = "image/jpeg"
                    elif image.lower().endswith(".gif"):
                        mime_type = "image/gif"
                    elif image.lower().endswith(".webp"):
                        mime_type = "image/webp"
                    else:
                        mime_type = "image/jpeg"  # 默认

                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        }
                    )
            elif isinstance(image, dict):
                if image.get("type") == "base64":
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image['data']}"
                            },
                        }
                    )
                elif image.get("type") == "url":
                    content.append(
                        {"type": "image_url", "image_url": {"url": image["url"]}}
                    )

    return {"role": "user", "content": content}


def completions(messages, model, stream=False, temperature=0.0):
    if model in [GEMINI_3_FLASH]:
        few_shot_turns = [
            create_image_message(
                text="识别图中手写填空答案，按「定位作答区、特征、结果」分条输出。",
                images=[_FEW_SHOT_EXAMPLE_IMAGE],
            ),
            {"role": "assistant", "content": _FEW_SHOT_ASSISTANT},
        ]
        messages = few_shot_turns + list(messages)
        # 原key
        url = "https://one-api.aixuexi.com/v1/chat/completions"
        api_key = "sk-REPLACE_ME"
        # api_key = "sk-REPLACE_ME"

        # url = "https://one-api.aixuexiyouxuan.com/v1/chat/completions"
        # api_key = "sk-REPLACE_ME"
    else:
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        api_key = "sk-REPLACE_ME"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
        "stream": stream,
    }
    try:
        # response = requests.post(url, headers=headers, data=json.dumps(data), timeout=20)
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=9)
        # response = requests.post(url, headers=headers, data=json.dumps(data), timeout=120)

        if response.status_code != 200:
            return response.text, response.status_code
        return response.text, 200
    except Exception as e:
        return str(e), 403


# 使用示例

# 1. 纯文本消息
# messages = [
#     {"role": "user", "content": "你是谁？你的版本是什么"}
# ]

# 2. 文本 + 本地图片
# messages = [
#    create_image_message(
#        text="题干是：孙悟空、猪八戒、沙僧进行吃包子比赛．结果沙僧吃的包子数量是孙悟空的3倍，猪八戒吃的比沙僧的2倍少4个，三人共吃了196个包子．那么孙悟空吃了____个包子．识别图中填空题上下划线上的答案。只输出数字答案就行",
#        images=["./填空题图片/10286436_4506420.jpg"]
#    )
# ]

# 3. 文本 + 网络图片
# messages = [
#     create_image_message(
#         text="请分析这张图片",
#         images=["https://example.com/image.jpg"]
#     )
# ]

# 4. 文本 + 多张图片
# messages = [
#     create_image_message(
#         text="比较这两张图片的差异",
#         images=[
#             "path/to/image1.jpg",
#             "https://example.com/image2.jpg"
#         ]
#     )
# ]

# 5. 使用base64格式的图片
# base64_image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
# messages = [
#     create_image_message(
#         text="请识别这张图片",
#         images=[{"type": "base64", "data": base64_image_data}]
#     )
# ]

# model = 'qwen-vl-ocr-latest'  # 确保使用的模型支持视觉功能
# response = completions(messages, model=model)
# print(response)
