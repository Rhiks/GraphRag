"""
主观题判题服务
"""

import asyncio
from typing import AsyncIterator, Dict, List

from config.logger import logger
from model.subjective.judge import (
    JudgeRequest,
    CommonJudgeResponse,
    STATUS_NORMAL,
    STATUS_ERROR,
)
from model.chat import ChatMessage
from utils.prompt import PromptTemplate
from prompt.subjective_prompt_templetes import PROMPT_TEMPLATES
from model.subjective.judge_result import JudgeResult
from utils.sse_handler import SSEHandler
from utils.score_parser import ScoreParser
from utils.result_elector import ResultElector
from service.judge.concurrent_stream_handler import ConcurrentStreamHandler


class SubjectiveJudgeService:
    """主观题判题服务"""

    # 类变量：prompt 模板列表（在多个请求间共享）
    _prompt_templates: List[PromptTemplate] = []
    _templates_initialized: bool = False

    @classmethod
    def _initialize_templates(cls):
        """
        初始化 prompt 模板
        从 prompt_templates 模块加载模板
        """
        if cls._templates_initialized:
            return
        cls._prompt_templates = PROMPT_TEMPLATES
        cls._templates_initialized = True
        logger.info(f"Initialized {len(cls._prompt_templates)} prompt templates")

    @classmethod
    def _collect_results(
        cls,
        result_collectors: Dict[str, List[str]],
        subject_product_id: int,
    ) -> Dict[str, JudgeResult]:
        """
        收集所有模板的完整结果

        Args:
            result_collectors: 结果收集器，template_id -> chunks 的映射
            subject_product_id: 学科产品ID

        Returns:
            Dict[str, JudgeResult]: template_id -> JudgeResult 的映射
        """
        results: Dict[str, JudgeResult] = {}
        for template in cls._prompt_templates:
            template_id = template.model_name
            chunks = result_collectors.get(template_id, [])

            # 从 chunks 中提取完整响应文本
            full_response = SSEHandler.parse_sse_content(chunks)

            # 解析得分
            score = ScoreParser.parse_score(full_response)

            # 判断是否成功（有得分且不是错误响应）
            last_index = (
                0
                if score is not None
                and not any("error" in chunk.lower() for chunk in chunks)
                else -1
            )

            results[template_id] = JudgeResult(
                template_id=template_id,
                model=template.model_name,
                full_response=full_response,
                chunks=chunks,
                score=score,
                subject_product_id=subject_product_id,
                last_index=last_index,
            )

            logger.info(
                f"Result for {template_id}: score={score}, "
                f"last_index={last_index}, "
                f"response_length={len(full_response)}"
            )

        return results

    @classmethod
    def _build_final_response(
        cls, best_result: JudgeResult, conversation_id: str
    ) -> CommonJudgeResponse:
        """
        构建最终响应

        Args:
            best_result: 最佳判题结果
            conversation_id: 会话ID

        Returns:
            CommonJudgeResponse: 最终响应对象
        """
        # 构建最终响应内容（添加批改结果）
        final_content = best_result.full_response
        if best_result.score is not None:
            judge_result = ScoreParser.calculate_judge_result(best_result.score)
            # 检查是否已经包含批改结果
            if "**批改结果：**" not in final_content:
                # 添加批改结果到最终输出
                judge_result_text = f"\n**批改结果：** {judge_result}"
                final_content += judge_result_text

        # 创建最终结果的 CommonJudgeResponse
        return CommonJudgeResponse(
            conversation_id=conversation_id,
            is_finished=True,
            index=0,  # 最终结果的 index 为 0
            message=ChatMessage(role="assistant", content=final_content),
            code=STATUS_NORMAL,
            error_message=None,
        )

    @classmethod
    def _build_error_response(
        cls, conversation_id: str, error_message: str
    ) -> CommonJudgeResponse:
        """
        构建错误响应

        Args:
            conversation_id: 会话ID
            error_message: 错误消息

        Returns:
            CommonJudgeResponse: 错误响应对象
        """
        return CommonJudgeResponse(
            conversation_id=conversation_id,
            is_finished=True,
            index=-1,
            message=ChatMessage(role="assistant", content=""),
            code=STATUS_ERROR,
            error_message=error_message,
        )

    @classmethod
    async def judge(cls, request: JudgeRequest) -> AsyncIterator[Dict[str, str]]:
        """
        执行判题流程

        流程：
        1. 并发请求所有 prompt 模板
        2. 第一个开始返回的抢占输出机会，开始流式返回
        3. 所有请求完成后，收集结果
        4. 通过选举机制决定最终判题结果
        5. 流式返回最终判题信息

        Args:
            request: 判题请求

        Yields:
            Dict[str, str]: SSE 事件字典，包含：
                - event: 事件类型（message / flush / done）
                - data: 事件数据字符串
        """
        # 确保模板已初始化
        cls._initialize_templates()

        if not cls._prompt_templates:
            logger.error("No prompt templates available")
            error_response = cls._build_error_response(
                request.conversation_id, "No prompt templates available"
            )
            yield {
                "event": "message",
                "data": error_response.model_dump_json(by_alias=True),
            }
            yield {
                "event": "done",
                "data": "[DONE]",
            }
            return

        logger.info(
            f"Starting judge with {len(cls._prompt_templates)} templates, "
            f"student_id={request.student_info.student_user_id}, "
            f"question_id={request.question_info.question_id}"
        )

        try:

            instruction_suffix = ""
            # 安全获取 sub_index
            if request.question_info and request.question_info.topic_info:
                topic_info = request.question_info.topic_info
                sub_index = getattr(topic_info, "sub_index", 0)
                topic_type = getattr(topic_info, "topic_type", 2)
                if topic_type == 5 and sub_index is not None and sub_index >= 0:
                    instruction_suffix = (
                        f"\n\n**【重要指令】**\n"
                        f"本题为综合题，请务必**仅识别并判分第({sub_index + 1})小问**的作答内容，"
                        f"严格忽略其他小问的作答。"
                    )

            request_templates = [
                PromptTemplate(
                    model_name=t.model_name,
                    system_prompt=t.system_prompt,
                    # 【核心修改】：使用 format 替换占位符
                    # 先临时替换 thinking_process_format，然后替换 sub_task_instruction，最后恢复 thinking_process_format
                    user_prompt=t.user_prompt.replace("{thinking_process_format}", "__TEMP_THINKING_PLACEHOLDER__")
                                         .format(sub_task_instruction=instruction_suffix)
                                         .replace("__TEMP_THINKING_PLACEHOLDER__", "{thinking_process_format}"),
                    temperature=t.temperature
                ) for t in cls._prompt_templates
            ]

            # ========== 第1部分：最快模型临时返回 ==========
            # 并发请求所有模板，第一个返回的抢占输出机会
            temp_output_stream, tasks, result_collectors = (
                await ConcurrentStreamHandler.concurrent_stream_with_race(
                    request, request_templates
                )
            )

            # 流式返回临时输出（ConcurrentStreamHandler 已封装为 message 事件字典）
            async for event in temp_output_stream:
                if event.get("data"):
                    yield event

            # ========== 第2部分：FLUSH 标记 ==========
            yield {
                "event": "flush",
                "data": "[FLUSH]",
            }

            # 等待所有任务完成
            await asyncio.gather(*tasks)

            # 获取学科产品ID
            subject_product_id = request.question_info.topic_info.subject_product_id

            # 收集所有完整结果
            results = cls._collect_results(result_collectors, subject_product_id)
            logger.info(f"request: {request}")

            # 输出所有结果的详细信息（包含请求上下文信息）
            student_user_id = request.student_info.student_user_id
            question_id = request.question_info.question_id
            image_urls = request.question_info.img_url
            topic_id = request.question_info.topic_info.topic_id
            logger.info(
                f"All results collected for student_user_id={student_user_id}, question_id={question_id}, "
                f"img_url_count={len(image_urls)}, image_urls={image_urls}, total count: {len(results)}"
            )

            for template_id, result in results.items():
                logger.info(
                    f"Result_modelname={template_id} - student_user_id={student_user_id}, topic_id={topic_id}, "
                    f"image_urls={image_urls}, "
                    f"question_id={question_id}: "
                    f"model_name={result.model}, "
                    f"score={result.score}, "
                    f"full_response={result.full_response}"
                )

            # ========== 第3部分：选举后的结果 ==========
            # 选举最佳结果
            best_result = ResultElector.elect_best_result(results, subject_product_id)
            if not best_result:
                logger.error("No valid result after election")
                # 返回错误响应
                error_response = cls._build_error_response(
                    request.conversation_id, "No valid result after election"
                )
                yield {
                    "event": "message",
                    "data": error_response.model_dump_json(by_alias=True),
                }
                yield {
                    "event": "done",
                    "data": "[DONE]",
                }
                return

            logger.info(
                f"Result_modelname={best_result.template_id} - student_user_id={student_user_id}, topic_id={topic_id}, "
                f"image_urls={image_urls}, "
                f"question_id={question_id}: "
                f"Elected best result: template_id={best_result.template_id}, "
                f"score={best_result.score}"
            )

            # 构建并返回最终响应
            final_response = cls._build_final_response(
                best_result, request.conversation_id
            )
            yield {
                "event": "message",
                "data": final_response.model_dump_json(by_alias=True),
            }

            # ========== 第4部分：DONE 标记 ==========
            yield {
                "event": "done",
                "data": "[DONE]",
            }

        except asyncio.TimeoutError as e:
            # 所有任务都超时，直接返回超时错误给客户端
            logger.error(f"Judge timeout: {e}", exc_info=True)
            error_response = cls._build_error_response(
                request.conversation_id, f"Judge timeout: {str(e)}"
            )
            yield {
                "event": "message",
                "data": error_response.model_dump_json(by_alias=True),
            }
            yield {
                "event": "done",
                "data": "[DONE]",
            }
            return
        except Exception as e:
            # 捕获所有其他异常，记录详细错误信息
            logger.error(
                f"Unexpected error in judge method: {type(e).__name__}: {e}",
                exc_info=True,
            )
            # 记录详细的错误上下文信息
            logger.error(
                f"Error details - student_id={request.student_info.student_user_id}, "
                f"question_id={request.question_info.question_id}, "
                f"templates_count={len(cls._prompt_templates)}"
            )
            # 返回错误信息给客户端
            error_response = cls._build_error_response(
                request.conversation_id, f"Judge error: {str(e)}"
            )
            yield {
                "event": "message",
                "data": error_response.model_dump_json(by_alias=True),
            }
            yield {
                "event": "done",
                "data": "[DONE]",
            }
            return
