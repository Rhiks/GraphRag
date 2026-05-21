# -*- coding: utf-8 -*-
"""
FastAPI version of the LLM blanks recognition service
"""
import os
import uuid
import datetime
import time
import numpy as np

from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

from config.logger import logger
from config import Config
from router import judge, xishuashua
from utils.pinpoint import setup_pinpoint
from robot_warning import send_wechat_message
from inference_main1 import inference_main
from models import HealthResponse


# Setup middleware
middleware_list = []
middleware_list.extend(setup_pinpoint())


# Create FastAPI app with middleware
app = FastAPI(
    title="LLM Blanks Recognition Service",
    version="2.0.0",
    middleware=middleware_list,
)
print("service pid: ", os.getpid())

# 按业务挂载路由
biz_routers = [
    judge.router,
    xishuashua.router,
]

for id, router in enumerate(biz_routers):
    if id == 0:
        app.include_router(router, prefix=Config.API_PREFIX)
    else:        
        app.include_router(router)


def check_params(data):
    """Check parameters matching Flask version logic"""
    params_correct = True
    info_correct = True
    params_check_info = ""
    info_check_info = ""

    question_info = data.get("question_info", {})
    question_params = data.get("question_params", {})
    if question_info == {}:
        info_check_info = "miss question info"
        info_correct = False
        return params_correct, params_check_info, info_correct, info_check_info
    elif question_params == {}:
        params_check_info = "miss question_params"
        params_correct = False
        return params_correct, params_check_info, info_correct, info_check_info
    question_params_keys = ["student_user_id", "topic_id", "topic_type"]
    question_info_keys = ["es_answers", "stem"]
    for key in question_params_keys:
        if question_params.get(key, None) is None:
            params_check_info = f"params miss {key}"
            params_correct = False
            break
    for key in question_info_keys:
        if question_info.get(key, None) is None:
            info_check_info = f"info miss {key}"
            info_correct = False
            break
    return params_correct, params_check_info, info_correct, info_check_info


def inference(request: dict, pipe: str = "blanks_recog"):
    """
    Run inference on the image
    """
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
    except Exception as e:
        code = 500
        message = str(e)
        send_wechat_message(f"blanks_ocr error {request['request_id']}_{str(e)}")
        logger.error(f"error_{request['request_id']}_{str(e)}")

    output_params = {
        "status_code": code,
        "message": message,
        "request_id": request["request_id"],
        "recog_results": recog_results,
    }
    t1 = time.time()
    process_cv_time = np.round(t1 - t0, 4)
    logger.info(f"whole_process_time cost: {request['request_id']}_{process_cv_time}s")
    logger.info(f"completed_{request['request_id']}_{output_params}")
    return output_params, code


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(Msg="success")


@app.post("/blanks_recog")
def blanks_recog(data: dict = Body(...)):
    """
    Blanks recognition endpoint (sync).
    Compatible with Flask version - accepts JSON body and validates manually.
    """

    task_id = str(uuid.uuid4())
    dt = datetime.datetime.now()
    request_id = f"{dt.year}_{dt.month}_{dt.day}_{task_id}"
    logger.info(f"request_id received {request_id} data: {data}")
    output_params = {
        "status_code": 0,
        "message": "",
        "request_id": request_id,
        "recog_results": [],
    }

    img_url = data.get("img_url", None)
    if img_url is None:
        output_params["status_code"] = 301
        output_params["message"] = "miss img_url"
        return JSONResponse(content=output_params, status_code=301)

    params_correct, params_check_info, info_correct, info_check_info = check_params(
        data
    )
    if (not params_correct) or (not info_correct):
        if not params_correct:
            message = params_check_info
        elif not info_correct:
            message = info_check_info
        output_params["status_code"] = 301
        output_params["message"] = message
        return JSONResponse(content=output_params, status_code=301)

    inference_params = {**data, **{"request_id": request_id}}

    output_params, code = inference(inference_params)
    return JSONResponse(content=output_params, status_code=code)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5400)
