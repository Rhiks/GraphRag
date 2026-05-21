"""
VLM 短文填空识别模块
使用 qwen3-vl-plus 模型识别学生作答结果
"""

from __future__ import annotations

import json
from typing import List, Dict, Any, Tuple, Optional

from config.logger import logger
from service.chat.chat_service import ChatService
from model.chat import ChatMessage


async def recognize_vlm(
    img_url: str | None,
    question_stem: str,
    system_prompt: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    使用 VLM 模型执行短文填空识别

    Args:
        img_url: 图片URL
        question_stem: 题干内容
        system_prompt: 系统提示词

    Returns:
        (状态文本, 识别结果 JSON)
    """
    if not img_url:
        return "请上传作答图片。", []
    if not question_stem or not question_stem.strip():
        return "请输入原始题干内容。", []

    logger.info(f"使用 qwen3-vl-plus 模型识别图片: {img_url}")

    # 构建系统提示词
    if not system_prompt:
        system_prompt = """你是一个严格的 OCR 手写识别助手，**仅负责识别图片中学生真实书写在横线上的内容，绝对不可以自行推理、补全、猜测或做题**。 

 任务说明： 
 1. 用户会提供一张纸质试卷照片，及该题原始题干文本（用于参考编号位置）。 
 2. 你必须**仅从图像中提取学生手写在横线上的内容**，编号以"1."、"2."、"3."等形式标记在纸上。 
 3. 图像中每个编号对应的横线上的手写内容就是该编号的答案，不依赖题干语法或语义。 

 识别规则（重点）： 
 - 只看图片！题干仅用于核对编号是否存在，不用于"推理"答案。 
 - 只识别横线上的内容，不要识别横线前后的其他内容。 
 - 如果图片里没有编号4，就不输出编号4；哪怕题干有10个空，也只输出图片中存在的。 
 - 学生手写内容可能拼写错误、不完整、或与题干不匹配——都必须如实记录。 
 - 绝对禁止"根据题干推断学生应该填什么"或"把题干词当作答案"。 
 - 严禁编造、联想、补全——"看不到就跳过"，"识别不清就略过"。 

 特别提醒： 
 若题干是"1. ________ you tomorrow!"，而图片中学生在横线上写的是"see"，那你就输出： 
   {"number": 1, "content": "see"} 

 哪怕你心里知道"see you tomorrow"是固定搭配——你也不可以自行把"you"或"tomorrow"加进去！ 

 输出要求： 
 - 严格 JSON 数组格式，无额外文字。 
 - 每项：{"number": 整数编号, "content": 学生手写在横线上的内容} 
 - 只输出图像中实际存在的编号及其对应手写内容。 
 - 内容保留原样，包括错别字、大小写、标点、空格等。 

 示例（根据你本次上传的图片）： 
 [ 
   {"number": 1, "content": "see"}, 
   {"number": 2, "content": "you"}, 
   {"number": 3, "content": "tomorrow"} 
 ] 

 ⚠️ 再次强调：你不答题，你只识字！  
 你不纠错，你只照录！  
 你看图像，不看题干含义！  
 只识别横线上的内容！  
 看不到的，就跳过！别发明！ 
"""

    # 构建用户提示词
    user_prompt = f"请识别图片中学生的作答，根据图片中实际存在的编号，提取每个编号对应的横线上的手写内容。\n\n题干：\n{question_stem}\n\n请严格按照以下JSON格式返回结果：\n[\n  {{\"number\": 1, \"content\": \"横线上的手写内容\"}},\n  {{\"number\": 2, \"content\": \"横线上的手写内容\"}}\n]\n\n注意：只输出图片中实际存在的编号及其对应横线上的手写内容，不要根据题干推断答案，也不要识别横线前后的其他内容。"

    # 构建消息列表
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=[
            {
                "type": "text",
                "text": user_prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": img_url
                }
            }
        ])
    ]

    try:
        # 调用模型服务
        service = ChatService.create_model_service("qwen3-vl-plus")
        response = await service.create_chat_completions(messages=messages, temperature=0.1)

        # 解析响应
        logger.info(f"模型响应: {json.dumps(response, ensure_ascii=False)}")
        
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                choice = choices[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                logger.info(f"模型返回内容: {content}")

                # 提取 JSON 部分
                import re
                # 尝试匹配 JSON 数组
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        answers = json.loads(json_str)
                        if isinstance(answers, list):
                            # 整理结果
                            formatted_answers = []
                            for answer in answers:
                                if isinstance(answer, dict):
                                    number = answer.get("number")
                                    content = answer.get("content", "")
                                    if number:
                                        formatted_answers.append({
                                            "number": number,
                                            "content": content.strip()
                                        })
                            
                            count = len(formatted_answers)
                            numbers = [item.get("number") for item in formatted_answers]
                            status = f"VLM识别完成，共识别到 {count} 个填空: 编号 {numbers}"
                            logger.info(status)
                            return status, formatted_answers
                    except json.JSONDecodeError as e:
                        logger.error(f"解析JSON失败: {e}")
                # 如果没有匹配到数组，尝试匹配对象
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        result = json.loads(json_str)
                        answers = result.get("answers", [])
                        if isinstance(answers, list):
                            # 整理结果
                            formatted_answers = []
                            for answer in answers:
                                if isinstance(answer, dict):
                                    number = answer.get("number")
                                    content = answer.get("content", "")
                                    if number:
                                        formatted_answers.append({
                                            "number": number,
                                            "content": content.strip()
                                        })
                            
                            count = len(formatted_answers)
                            numbers = [item.get("number") for item in formatted_answers]
                            status = f"VLM识别完成，共识别到 {count} 个填空: 编号 {numbers}"
                            logger.info(status)
                            return status, formatted_answers
                    except json.JSONDecodeError as e:
                        logger.error(f"解析JSON失败: {e}")

        # 如果解析失败，返回默认结果
        logger.error("VLM识别失败，返回空结果")
        return "VLM识别失败", []

    except Exception as e:
        logger.error(f"VLM识别失败: {e}")
        return f"VLM识别失败: {e}", []
