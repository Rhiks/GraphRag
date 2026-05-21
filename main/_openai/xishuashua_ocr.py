"""
喜刷刷 - 短文填空 OCR 调试页面

输入一张纸质作答图和原始题干文本，通过 VLM 识别手写填空内容，
返回每个填空编号及其对应的作答内容。
"""

from __future__ import annotations

import base64
import json
import asyncio
from typing import Any

from config.logger import logger
from utils.llm_client import chat_completions, chat_completions_async

_VLM_MODEL = "qwen3.5-plus"

_SYSTEM_PROMPT = """\
你是一个纯粹的 OCR 手写识别工具，**只负责像素级还原学生在横线上的手写内容**，完全不具备任何理解、推理或纠正能力。

核心指令（必须严格遵守）：
- 你的唯一任务是：看到什么就写什么，**完全按照学生手写的原样输出**，包括所有拼写错误、笔误和不完整的内容。
- 你**绝对不能**：纠正拼写、补全单词、修改语法、添加任何内容或删除任何内容。
- 你**只看图片**，题干对你来说只是无意义的文本，仅用于定位编号位置。
- 你**没有**任何语言理解能力，你只是一个像素级的"扫描仪"。

操作步骤：
1. 找到图片中所有形如 "(1)"、"(2)"、"(3)" 的编号。
2. 对于每个编号，找到其对应的横线。
3. **像素级还原**横线上的所有手写内容，包括：
   - 拼写错误（如 "dresed" 就是 "dresed"，不是 "dressed"）
   - 笔误（如 "teeth" 写成 "theeth"）
   - 不完整的单词（如 "get dr" 就是 "get dr"）
   - 大小写和空格（如 "GET DRESED" 就是 "GET DRESED"）
4. 生成 JSON 数组，每个元素必须严格按照以下格式：
   - {"number": 整数编号, "content": "学生手写内容"}
   - 其中 "number" 是整数，如 1, 2, 3
   - "content" 是字符串，包含学生手写的原始内容

**关键原则**：
- 你是一个"扫描仪"，不是"老师"或"助手"。
- 你不评价、不纠正、不补全、不猜测。
- 你只做一件事：**如实记录**学生写在横线上的内容。
- 你的输出必须与学生的手写内容**像素级一致**，任何偏差都被视为错误。

**强制要求**：
- 即使你认为学生写错了，也要完全按照原样输出。
- 即使你认为学生写的不完整，也要完全按照原样输出。
- 即使你认为学生写的不符合语法，也要完全按照原样输出。
- 即使你认为学生写的单词不存在，也要完全按照原样输出。
- 你**绝对不能**使用任何语言模型的推理能力来"猜测"或"纠正"学生的答案。
- 你**必须**使用英文键名 "number" 和 "content"，而不是中文键名。
- 你**必须**返回严格的 JSON 格式，不要包含任何其他文字。
"""


def _encode_image(image_path: str) -> str:
    """将图片文件编码为 base64 data URI。"""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"


def _build_messages(
    img_url: str,
    question_stem: str,
    system_prompt: str | None = None,
) -> list[dict[str, Any]]:
    """构造 VLM 请求的 messages。"""
    prompt = (system_prompt or _SYSTEM_PROMPT).strip()
    return [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": img_url},
                },
                {
                    "type": "text",
                    "text": f"以下是本题的原始题干内容：\n\n{question_stem}",
                },
            ],
        },
    ]


def _parse_response(raw: str) -> list[dict[str, Any]]:
    """从 VLM 返回的原始响应中提取 JSON 结果。"""
    try:
        body = json.loads(raw)
        content = body["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        logger.error("解析 VLM 响应结构失败: %s", exc)
        raise ValueError(f"VLM 响应结构异常: {exc}") from exc

    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("VLM 返回内容不是合法 JSON: %s\n原始内容: %s", exc, text)
        raise ValueError(f"VLM 返回内容不是合法 JSON: {text}") from exc

    if not isinstance(result, list):
        raise ValueError(f"VLM 返回的不是 JSON 数组: {type(result)}")
    return result


def recognize_xishuashua(
    img_url: str | None,
    question_stem: str,
    system_prompt: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    执行短文填空 OCR 识别。

    返回 (状态文本, 识别结果 JSON)。
    """
    if not img_url:
        return "请上传作答图片。", []
    if not question_stem or not question_stem.strip():
        return "请输入原始题干内容。", []

    messages = _build_messages(
        img_url=img_url,
        question_stem=question_stem.strip(),
        system_prompt=system_prompt,
    )

    logger.info("发起 VLM 识别请求: model=%s", _VLM_MODEL)
    raw_response, status_code = chat_completions(
        messages=messages,
        model=_VLM_MODEL,
        temperature=0.0,
        timeout=60.0,
        enable_thinking=False,
    )

    if status_code != 200:
        msg = f"VLM 调用失败 (HTTP {status_code}): {raw_response[:500]}"
        logger.error(msg)
        return msg, []

    try:
        result = _parse_response(raw_response)
    except ValueError as exc:
        return str(exc), []

    count = len(result)
    numbers = [item.get("number") for item in result]
    status = f"识别完成，共识别到 {count} 个填空: 编号 {numbers}"
    logger.info(status)
    return status, result


async def recognize_xishuashua_async(
    img_url: str | None,
    question_stem: str,
    system_prompt: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    异步执行短文填空 OCR 识别。

    使用异步 LLM 调用，避免阻塞事件循环。

    返回 (状态文本，识别结果 JSON)。
    """
    if not img_url:
        return "请上传作答图片。", []
    if not question_stem or not question_stem.strip():
        return "请输入原始题干内容。", []

    messages = _build_messages(
        img_url=img_url,
        question_stem=question_stem.strip(),
        system_prompt=system_prompt,
    )

    logger.info("发起异步 VLM 识别请求：model=%s", _VLM_MODEL)
    raw_response, status_code = await chat_completions_async(
        messages=messages,
        model=_VLM_MODEL,
        temperature=0.0,
        timeout=60.0,
        enable_thinking=False,
    )

    if status_code != 200:
        msg = f"VLM 调用失败 (HTTP {status_code}): {raw_response[:500]}"
        logger.error(msg)
        return msg, []

    try:
        result = _parse_response(raw_response)
    except ValueError as exc:
        return str(exc), []

    count = len(result)
    numbers = [item.get("number") for item in result]
    status = f"识别完成，共识别到 {count} 个填空：编号 {numbers}"
    logger.info(status)
    return status, result


_EXAMPLE_STEM = """\
Sam: Lucas, what do you do (1) ________ you
get up?
Lucas: I brush my teeth. Then I go (2)
________ the classroom.
Sam: We can (3) ________ our English books
there.
Lucas: (4) ________ ________!
Sam: Thanks! By the way, let's play together
tomorrow.
Lucas: Great! (5) ________ ________
________!
"""
