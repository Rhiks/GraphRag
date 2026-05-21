"""
判题相关路由
"""

import uuid
import datetime
import time
import numpy as np

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from service.judge.subjective_judge_service import SubjectiveJudgeService
from model.subjective.judge import JudgeRequest
from config.logger import logger
from inference_main1 import inference_main
from robot_warning import send_wechat_message

router = APIRouter(
    prefix="/judge",
    tags=["judge"],
)


def _normalize_subjective_img_url(request: JudgeRequest) -> None:
    """主观题：img_url 统一为 list[str]（单 URL 则包成单元素列表）。"""
    raw = request.question_info.img_url
    if isinstance(raw, list):
        return
    request.question_info.img_url = [raw]


def _normalize_objective_img_url(request: JudgeRequest) -> None:
    """客观题：img_url 统一为 str（若为列表则取第一张）。"""
    raw = request.question_info.img_url
    if isinstance(raw, list):
        request.question_info.img_url = raw[0] if raw else ""


@router.post("/streaming/subjective")
async def subjective_judge_streaming(request: JudgeRequest) -> EventSourceResponse:
    """
    流式返回的主观题判题接口（SSE）

    事件类型由服务层决定，通常包括：
    - message: 普通内容
    - flush: 第一阶段结束标记
    - done: 整个流程结束标记
    
    """
    _normalize_subjective_img_url(request)

    img_urls = request.question_info.img_url
    logger.info(
        f"Subjective judge request: student_user_id={request.student_info.student_user_id}, "
        f"question_id={request.question_info.question_id}, "
        f"topic_id={request.question_info.topic_info.topic_id}, "
        f"img_url_count={len(img_urls)}, img_urls={img_urls}"
    )

    # 直接使用服务层返回的异步迭代器作为 SSE 事件源
    return EventSourceResponse(SubjectiveJudgeService.judge(request))


@router.post("/objective")
def objective_judge(request: JudgeRequest):
    """
    客观题（填空题）识别接口

    使用 JudgeRequest 作为传入参数，返回格式与 /blanks_recog 一致
    """
    # 生成 request_id
    task_id = str(uuid.uuid4())
    dt = datetime.datetime.now()
    request_id = f"{dt.year}_{dt.month}_{dt.day}_{task_id}"
    current_sub_index = request.question_info.topic_info.sub_index
    if current_sub_index is None:
        current_sub_index = -1

    _normalize_objective_img_url(request)

    logger.info(
        f"Objective judge request: student_user_id={request.student_info.student_user_id}, "
        f"question_id={request.question_info.question_id}, "
        f"topic_id={request.question_info.topic_info.topic_id}, "
        f"sub_index={current_sub_index},"
        f"request_id={request_id}, "
        f"img_url={request.question_info.img_url!r}"
    )

    # 初始化返回参数
    output_params = {
        "status_code": 0,
        "message": "",
        "request_id": request_id,
        "recog_results": [],
    }

    request.request_id = request_id

    # 调用推理函数
    t0 = time.time()
    code = 0
    message = ""
    recog_results = {}

    try:
        res, cc, res_message = inference_main(request, debug=False)
        if cc != 200:
            message = "timed out or failed"
        else:
            message = "Success"
        recog_results = res
        code = cc
    except ValueError as e:
        code = 301
        message = str(e)
    except Exception as e:
        code = 500
        message = str(e)
        send_wechat_message(f"blanks_ocr error {request_id}_{str(e)}")
        logger.error(f"error_{request_id}_{str(e)}")

    output_params = {
        "status_code": code,
        "message": message,
        "request_id": request_id,
        "recog_results": recog_results,
    }

    t1 = time.time()
    process_cv_time = np.round(t1 - t0, 4)
    logger.info(f"whole_process_time cost: {request_id}_{process_cv_time}s")
    logger.info(f"completed_{request_id}_{output_params}")

    return JSONResponse(content=output_params, status_code=code)
