"""
并发流式处理逻辑
"""

import asyncio
import json
from typing import AsyncIterator, Dict, List, Optional

from config.logger import logger
from model.subjective.judge import JudgeRequest, CommonJudgeResponse, STATUS_NORMAL
from model.chat import ChatMessage
from service.chat.chat_service import ChatService
from utils.prompt import PromptTemplate
from utils.uuid_util import generate_uuid
from config import Config
from utils.sse_handler import SSEHandler


class ConcurrentStreamHandler:
    """并发流式处理处理器"""

    @staticmethod
    async def stream_chat_with_template(
        template: PromptTemplate, request: JudgeRequest
    ) -> AsyncIterator[tuple[str, str, str]]:
        """
        使用指定模板进行流式聊天请求

        Args:
            template: Prompt 模板
            request: 判题请求

        Yields:
            tuple[str, str, str]: (template_id, content, original_chunk) 数据块
                - template_id: 模板ID
                - content: 提取的文本内容（已处理好的）
                - original_chunk: 原始 SSE 格式的 chunk（用于收集和后续处理）
        """
        # 使用模板的 model_name 作为 template_id
        template_id = template.model_name
        chat_request = await template.build_chat_completion_request(request.question_info)
        try:
            async for chunk in ChatService.stream_completions(
                model=chat_request.model,
                messages=chat_request.messages,
                temperature=chat_request.temperature,
            ):
                # 从 SSE chunk 中提取 content
                content = SSEHandler.extract_content_from_chunk(chunk)
                yield (template_id, content, chunk)
        except asyncio.CancelledError:
            # 让 CancelledError 传播，不要吞掉它
            raise
        except Exception as e:
            logger.error(
                f"Error in stream_chat_with_template for {template_id}: {e}",
                exc_info=True,
            )
            error_chunk = f"data: {json.dumps({'error': str(e)})}\n\n"
            yield (template_id, "", error_chunk)

    @staticmethod
    async def concurrent_stream_with_race(
        request: JudgeRequest, prompt_templates: List[PromptTemplate]
    ) -> tuple[AsyncIterator[Dict[str, str]], List[asyncio.Task], Dict[str, List[str]]]:
        """
        并发请求所有模板，第一个返回的抢占输出机会

        流程：
        1. 并发启动所有模板的流式请求
        2. 第一个开始返回的模板抢占输出机会
        3. 流式返回抢占模板的输出（临时输出）
        4. 收集所有结果

        Args:
            request: 判题请求
            prompt_templates: Prompt模板列表

        Returns:
            tuple: (临时输出流, 任务列表, 结果收集器)
                - 临时输出流: AsyncIterator[Dict[str, str]]，流式返回抢占模板的输出事件
                  事件结构为 {"event": "message", "data": <CommonJudgeResponse JSON 字符串>}
                - 任务列表: List[asyncio.Task]，用于等待所有任务完成
                - 结果收集器: Dict[str, List[str]]，template_id -> chunks 的映射
        """
        # 生成第一部分的随机 conversationId（所有第一部分响应保持一致）
        temp_conversation_id = generate_uuid()

        # 用于抢占机制的标志
        output_lock = asyncio.Lock()
        first_output_claimed = asyncio.Event()
        first_output_template_id: Optional[str] = None

        # 用于收集所有结果的容器
        result_collectors: Dict[str, List[str]] = {
            template.model_name: [] for template in prompt_templates
        }

        # 用于流式输出的队列（临时输出阶段）
        # 队列中存储的是 CommonJudgeResponse 的 JSON 字符串
        output_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        # 用于跟踪 index 的计数器（需要锁保护）
        index_counter = 0
        index_lock = asyncio.Lock()

        async def _process_template_stream(template: PromptTemplate):
            """处理单个模板的流式返回并收集结果"""
            nonlocal first_output_template_id, index_counter
            is_first = False

            try:
                async for (
                    template_id,
                    content,
                    original_chunk,
                ) in ConcurrentStreamHandler.stream_chat_with_template(
                    template, request
                ):
                    # 收集原始 SSE 数据块（用于后续解析完整响应）
                    result_collectors[template_id].append(original_chunk)

                    # 抢占机制：第一个开始返回的抢占输出机会
                    if not first_output_claimed.is_set():
                        async with output_lock:
                            if not first_output_claimed.is_set():
                                first_output_template_id = template_id
                                first_output_claimed.set()
                                is_first = True
                                logger.info(
                                    f"Template {template_id} claimed first output"
                                )

                    # 如果是抢占成功的模板，将处理好的 content 格式化为 CommonJudgeResponse 并放入输出队列
                    if is_first and content:
                        # 创建 CommonJudgeResponse 对象（使用锁保护 index_counter 递增）
                        async with index_lock:
                            index_counter += 1
                            current_index = index_counter
                        response = CommonJudgeResponse(
                            conversation_id=temp_conversation_id,  # 第一部分使用随机 UUID
                            is_finished=False,
                            index=current_index,
                            message=ChatMessage(role="assistant", content=content),
                            code=STATUS_NORMAL,
                            error_message=None,
                        )
                        # 转换为 JSON 字符串
                        response_json = response.model_dump_json(by_alias=True)
                        await output_queue.put(response_json)

            except asyncio.CancelledError:
                # 处理任务取消（可能是超时导致的）
                logger.warning(
                    f"Task for template {template.model_name} was cancelled (possibly due to timeout)"
                )
                # 如果这个任务正在输出，需要标记结束
                if is_first:
                    try:
                        await output_queue.put(None)  # 使用 None 作为结束标记
                    except Exception as e:
                        logger.error(
                            f"Error putting end marker for cancelled task {template.model_name}: {e}"
                        )
                raise  # 重新抛出 CancelledError，让 asyncio 正确处理
            except Exception as e:
                logger.error(
                    f"Error processing template {template.model_name}: {e}",
                    exc_info=True,
                )
            finally:
                # 标记该模板处理完成
                if is_first:
                    try:
                        await output_queue.put(None)  # 使用 None 作为结束标记
                    except Exception as e:
                        logger.error(
                            f"Error putting end marker in finally for {template.model_name}: {e}"
                        )

        # 获取超时配置（默认 120 秒）
        task_timeout = Config.get_float("JUDGE_TASK_TIMEOUT", 11.0)

        # 启动所有并发任务，每个任务都有超时限制
        async def _create_task_with_timeout(template: PromptTemplate):
            """创建带超时的任务"""
            try:
                await asyncio.wait_for(
                    _process_template_stream(template),
                    timeout=task_timeout,
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Task for template {template.model_name} timed out after {task_timeout}s"
                )
                # 超时后，确保结果收集器中记录超时信息
                template_id = template.model_name
                if template_id not in result_collectors:
                    result_collectors[template_id] = []
                result_collectors[template_id].append(
                    f"data: {json.dumps({'error': f'Task timeout after {task_timeout}s'})}\n\n"
                )
            # 注意：asyncio.wait_for 超时时会抛出 TimeoutError，不会抛出 CancelledError
            # 如果 _create_task_with_timeout 本身被外部取消，CancelledError 会自然传播，不需要特殊处理

        tasks = [
            asyncio.create_task(_create_task_with_timeout(template))
            for template in prompt_templates
        ]

        # 等待第一个输出被抢占，但需要设置超时防止所有任务都超时导致卡死
        # 使用 task_timeout + 缓冲时间作为等待超时
        wait_timeout = task_timeout + 2.0  # 给任务超时后一些缓冲时间
        try:
            await asyncio.wait_for(first_output_claimed.wait(), timeout=wait_timeout)
            logger.debug(f"First output claimed by {first_output_template_id}")
        except asyncio.TimeoutError:
            # 如果等待超时，说明没有任何任务在超时时间内抢占到输出机会，直接抛出异常
            logger.warning(
                f"No task claimed first output within {wait_timeout}s, all tasks likely timed out"
            )
            raise asyncio.TimeoutError(
                f"All judge tasks timed out after {task_timeout}s, no valid output available"
            )

        # 流式返回抢占模板的输出（临时输出阶段）
        async def _temp_output_generator():
            """
            临时输出生成器，返回 SSE 事件字典：
            {
                "event": "message",
                "data": <CommonJudgeResponse JSON 字符串>,
            }
            """
            temp_output_finished = False
            while not temp_output_finished:
                chunk = await output_queue.get()
                if chunk is None:
                    temp_output_finished = True
                else:
                    # 封装为标准 SSE 事件字典
                    yield {
                        "event": "message",
                        "data": chunk,
                    }

        return _temp_output_generator(), tasks, result_collectors
