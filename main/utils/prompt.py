"""
Prompt 工具类
用于构建聊天完成请求的 Prompt 模板
"""

import re
import base64
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

import requests
import cairosvg

from config.logger import logger
from model.question import QuestionRequest, QuestionPart
from model.chat import ChatCompletionRequest, ChatMessage

# 正则表达式模式
PATTERN_HTML_TEXT = re.compile(r"<[^>]+>")
PATTERN_IMG_TAG = re.compile(
    r"<img[^>]+src\s*=\s*['\"]([^'\"]+)['\"][^>]*>", re.IGNORECASE
)


def extract_text_and_images_from_html(html: Optional[str]) -> Tuple[str, List[str]]:
    """
    从 HTML 中提取文本和图片 URL
    按照 Java 代码逻辑实现：使用正则表达式移除 HTML 标签并提取图片 URL

    Args:
        html: HTML 字符串

    Returns:
        Tuple[str, List[str]]: (文本内容, 图片 URL 列表)
    """
    if not html:
        return "", []

    # 移除所有 HTML 标签
    text = PATTERN_HTML_TEXT.sub("", html)
    # 替换 &nbsp; 为空字符串
    text = text.replace("&nbsp;", "")

    # 提取所有 img 标签的 src 属性值
    image_urls: List[str] = []
    for match in PATTERN_IMG_TAG.finditer(html):
        image_urls.append(match.group(1))

    return text, image_urls


def is_svg_url(image_url: str) -> bool:
    """
    检查图片 URL 是否为 SVG 格式
    
    Args:
        image_url: 图片 URL
    
    Returns:
        如果是 SVG 返回 True，否则返回 False
    """
    parsed_url = urlparse(image_url)
    path = parsed_url.path.lower()
    return path.endswith('.svg')


def _svg_to_png_sync(svg_data: bytes) -> bytes:
    """
    同步函数：使用 cairosvg 将 SVG 数据转换为 PNG 数据
    
    Args:
        svg_data: SVG 字节数据
    
    Returns:
        PNG 字节数据
    """
    return cairosvg.svg2png(bytestring=svg_data)


def _download_svg_sync(image_url: str, timeout: int) -> bytes:
    """
    同步函数：下载 SVG 图片并返回字节数据
    
    Args:
        image_url: SVG 图片 URL
        timeout: 下载超时时间（秒）
    
    Returns:
        SVG 字节数据
    """
    response = requests.get(image_url, timeout=timeout)
    response.raise_for_status()
    return response.content


async def svg_url_to_base64_data_url(
    image_url: str, timeout: int = 10
) -> Optional[str]:
    """
    异步将 SVG 图片 URL 下载并转换为 base64 data URL（PNG 格式）
    
    Args:
        image_url: SVG 图片 URL
        timeout: 下载超时时间（秒）
    
    Returns:
        base64 data URL 字符串（PNG 格式），如果失败返回 None
    """
    try:
        # 使用 asyncio.to_thread 将同步的下载函数转为异步
        svg_data = await asyncio.to_thread(_download_svg_sync, image_url, timeout)
        
        # 使用 asyncio.to_thread 将同步的 cairo 转换函数转为异步
        png_data = await asyncio.to_thread(_svg_to_png_sync, svg_data)
        
        # 转换为 base64
        base64_data = base64.b64encode(png_data).decode('utf-8')
        
        # 返回 PNG 格式的 data URL
        return f"data:image/png;base64,{base64_data}"
    
    except Exception as e:
        # 如果下载或转换失败，返回 None（跳过该图片）
        logger.warning(
            f"Failed to convert SVG URL to base64 data URL: {image_url}, error: {str(e)}"
        )
        return None


async def add_text_and_images_to_content(
    user_content: List[Dict[str, Any]],
    text: str,
    image_urls: List[str],
) -> None:
    """
    异步将文本和图片添加到用户消息内容中
    只有 SVG 格式的图片会被转换为 base64 data URL（PNG 格式），其他格式保留原始 URL

    Args:
        user_content: 用户消息内容列表
        text: 文本内容
        image_urls: 图片 URL 列表
    """
    if text:
        user_content.append({"type": "text", "text": text})
    
    for image_url in image_urls:
        # 只有 SVG 格式才转换为 base64 data URL
        if is_svg_url(image_url):
            data_url = await svg_url_to_base64_data_url(image_url)
            if data_url:
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"},
                    }
                )
            # 如果转换失败，跳过该图片（不添加）
        else:
            # 非 SVG 格式，直接使用原始 URL
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": image_url, "detail": "high"},
                }
            )


class PromptTemplate:
    """Prompt 模板类"""

    def __init__(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = 0.0,
    ):
        """
        初始化 Prompt 模板

        Args:
            model_name: 模型名称
            system_prompt: 系统提示词
            user_prompt: 尾部用户提示词
            temperature: 温度参数
        """
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.temperature = temperature

    async def build_chat_completion_request(
        self, question_request: QuestionRequest
    ) -> ChatCompletionRequest:
        """
        异步根据 QuestionRequest 构建 ChatCompletionRequest

        Args:
            question_request: 题目请求对象

        Returns:
            ChatCompletionRequest: 聊天完成请求对象
        """
        messages: List[ChatMessage] = []

        topic_info = question_request.topic_info

        # 检查题干中是否包含"计算"字样
        has_calculation = False
        if topic_info.stem and topic_info.stem.html:
            stem_text, _ = extract_text_and_images_from_html(topic_info.stem.html)
            if ("计算" in stem_text):
                has_calculation = True

        # 根据是否包含"计算"设置思考过程格式
        if has_calculation:
            thinking_process_format = "**思考过程：** <多小问：（1）标准答案，手写最终答案，是否一致， （2）标准答案，手写最终答案，是否一致， ...， 非多小问：标准答案，手写最终答案，是否一致>\n"
        else:
            thinking_process_format = ""

        # 1. 添加系统提示词（替换占位符）
        try:
            system_prompt_formatted = self.system_prompt.format(
                thinking_process_format=thinking_process_format
            )
        except KeyError:
            # 如果没有 thinking_process_format 占位符，直接使用原 prompt
            system_prompt_formatted = self.system_prompt
        messages.append(ChatMessage(role="system", content=system_prompt_formatted))

        # 2. 构建用户消息内容（多模态消息）
        user_content: List[Dict[str, Any]] = []

        # 2.1 处理题干
        if topic_info.stem and topic_info.stem.html:
            user_content.append(
                {"type": "text", "text": "下面是「题干」描述和可选的题干图片。"}
            )
            text, image_urls = extract_text_and_images_from_html(topic_info.stem.html)
            await add_text_and_images_to_content(user_content, text, image_urls)

        # 2.2 处理答案
        if topic_info.answers:
            user_content.append(
                {"type": "text", "text": "下面是「题目答案」描述和可选的题目答案图片。"}
            )
            for answer in topic_info.answers:
                if answer.html:
                    text, image_urls = extract_text_and_images_from_html(answer.html)
                    await add_text_and_images_to_content(user_content, text, image_urls)

        # 2.3 处理解析
        if topic_info.jiexis:
            user_content.append(
                {"type": "text", "text": "下面是「解析」描述和可选的解析图片。"}
            )
            for jiexi in topic_info.jiexis:
                if jiexi.html:
                    text, image_urls = extract_text_and_images_from_html(jiexi.html)
                    await add_text_and_images_to_content(user_content, text, image_urls)

        # 2.4 添加学生手写体内容提示和图片（支持多张作答图）
        user_content.append(
            {
                "type": "text",
                "text": "下面是学生的手写体内容，可能包含中文和数学符号。除了图片内容外，无需多余解释。",
            }
        )
        student_image_urls: List[str]
        raw_img = question_request.img_url
        if isinstance(raw_img, list):
            student_image_urls = list(raw_img)
        else:
            student_image_urls = [raw_img]
        for url in student_image_urls:
            if not url:
                continue
            # 只有 SVG 格式才转换为 base64 data URL，其他格式保留原始 URL
            if is_svg_url(url):
                student_image_url = await svg_url_to_base64_data_url(url)
                if student_image_url:
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": student_image_url,
                                "detail": "high",
                            },
                        }
                    )
            else:
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": url,
                            "detail": "high",
                        },
                    }
                )

        # 3. 添加用户消息
        messages.append(ChatMessage(role="user", content=user_content))

        # 4. 添加尾部用户提示词（替换占位符）
        if self.user_prompt:
            # 如果 user_prompt 中还有 {thinking_process_format} 占位符，则替换它
            # sub_task_instruction 应该已经在创建 PromptTemplate 时被替换了
            try:
                user_prompt_formatted = self.user_prompt.format(
                    thinking_process_format=thinking_process_format
                )
            except KeyError:
                # 如果没有 thinking_process_format 占位符，直接使用原 prompt
                user_prompt_formatted = self.user_prompt
            messages.append(ChatMessage(role="user", content=user_prompt_formatted))

        return ChatCompletionRequest(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
        )
