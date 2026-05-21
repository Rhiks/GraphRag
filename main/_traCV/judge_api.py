"""
判题接口调用模块
提供调用判题 API 的功能
"""

import json
import requests
from typing import Dict, Any, Optional
from config.logger import logger
import pdb


def call_judge_api(
    ctx,
    judge_base_url: Optional[str] = None,
    judge_endpoint: str = "/api/cms/judge",
    timeout: int = 2,
    salt: str = "llm-router",
) -> Optional[Dict[str, Any]]:
    """
    调用判题接口

    注意：此函数只使用 ctx.cv_middle_results.get('ocr_answers') 进行判题，
    不会修改 ctx.recog_results 或 ctx.stu_answers 等属性。

    Args:
        ctx: 推理上下文对象（InferenceContext），包含：
            - topic_id: 题目ID（从 ctx.question_params.get("topic_id") 获取）
            - cv_middle_results: CV处理中间结果，包含 ocr_answers（仅读取，不修改）
        judge_base_url: 判题接口服务地址，如果为 None 则使用默认值
        judge_endpoint: 判题接口端点，默认 "/api/cms/judge"
        timeout: 超时时间（秒），默认 2
        salt: 请求头中的盐值，默认 "llm-router"

    Returns:
        判题结果字典，如果失败返回 None
        成功时返回格式：
        {
            "data": {
                "result": {
                    "judge": 1  # 1 表示正确，0 表示错误
                }
            }
        }
    """
    # 获取 topic_id
    topic_id = ctx.question_params.get("topic_id")
    if topic_id is None:
        logger.error(f"{ctx.request_id}_判题接口调用失败: topic_id 为空")
        return None

    # 获取识别结果
    # 只使用 CV 处理的结果，不能替换其他答案
    stu_answers = []
    if hasattr(ctx, "cv_middle_results") and ctx.cv_middle_results:
        # pdb.set_trace()
        ocr_answers = ctx.cv_middle_results.get("ocr_answers", [])
        if ocr_answers:
            stu_answers = ocr_answers
            logger.info(f"{ctx.request_id}_使用 CV 处理结果作为判题输入: {stu_answers}")
        else:
            logger.warning(
                f"{ctx.request_id}_判题接口调用: cv_middle_results 中没有 ocr_answers，使用空列表"
            )
    else:
        logger.warning(
            f"{ctx.request_id}_判题接口调用: 未找到 cv_middle_results，使用空列表"
        )

    # 构建识别结果字典
    recog_results = {"stu_answers": stu_answers}

    # 构建请求体
    judge_input = {
        "topic_id": topic_id,
        "recog_results": recog_results,
    }

    # 构建判题接口 URL
    if judge_base_url is None:
        # 使用默认的判题接口地址
        judge_base_url = "https://jzx.aixuexi.com/ai"

    judge_url = f"{judge_base_url}{judge_endpoint}"

    # 构建请求头
    headers = {"Content-Type": "application/json", "salt": salt}

    # 记录请求信息
    logger.info("=" * 60)
    logger.info(f"{ctx.request_id}_准备调用判题接口: {judge_url}")
    logger.info(
        f"{ctx.request_id}_请求头: {json.dumps(headers, ensure_ascii=False, indent=2)}"
    )
    logger.info(f"{ctx.request_id}_超时时间: {timeout} 秒")
    logger.info(
        f"{ctx.request_id}_请求体: {json.dumps(judge_input, ensure_ascii=False, indent=2)}"
    )
    logger.info("=" * 60)
    try:
        response = requests.post(
            judge_url, json=judge_input, headers=headers, timeout=timeout
        )
        response.raise_for_status()
        result = response.json()

        # 解析判题结果
        try:
            data = result.get("data", {})
            judge_result = data.get("result", {})
            judge_value = judge_result.get("judge")
            # judge: 1 表示正确，0 表示错误
            is_correct = (judge_value == 1) if judge_value is not None else None
            logger.info(
                f"{ctx.request_id}_判题结果: judge={judge_value}, is_correct={is_correct}"
            )

            # 将判题结果存入 ctx.cv_middle_results
            if hasattr(ctx, "cv_middle_results") and ctx.cv_middle_results is not None:
                ctx.cv_middle_results["judge_result"] = {
                    "judge": judge_value,
                    "is_correct": is_correct,
                    "response": result,
                }
                logger.info(f"{ctx.request_id}_判题结果已存入 cv_middle_results")
        except Exception as e:
            logger.warning(f"{ctx.request_id}_解析判题结果失败: {e}")

        return result
    except requests.exceptions.Timeout:
        logger.error(f"{ctx.request_id}_判题接口请求超时: {judge_url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"{ctx.request_id}_判题接口请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"{ctx.request_id}_判题接口响应解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"{ctx.request_id}_判题接口调用异常: {e}")
        return None
