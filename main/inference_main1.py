from re import L
import requests
import base64
import pdb
import json
import time
import cv2
import os, sys
import uuid
import numpy as np
import threading
import pandas as pd
import datetime
import db_utils.pool_db_mysql as db_mysql
from constants.model_names import GEMINI_3_FLASH, QWEN3_VL_PLUS
from utils.encodecode import filter_white_backgrounds_update
from utils.line_processing import extract_main_model_result
from utils.finetune import contours_pipeline1
from utils.encodecode import (
    tidy_es_content,
    tidy_es_stem,
    clean_recognition_result,
    match_answers,
    match_answers0,
    smart_split_answers_v2,
    join_answers,
    mark2numbers,
    reedit_by_multi_results,
    reedit_by_multi_results1,
)
from _app_utils.download_file import download_from_url, remove_file
from _flip.flip_client import send_request_bgrim
from config.logger import logger

sys.path.append("./openai")
# from _openai.open_ai import completions, create_image_message, fetch_two_apis_concurrent
from _openai.open_ai import create_image_message, completions

# from _openai.prompt_engineering_ import prompt_engineering
# from _openai.prompt_engineering import prompt_engineering
from _openai.prompt_engineering_compre import general_prompt_engineering
import pdb
from pathlib import Path
from robot_warning import send_wechat_message
from datetime import datetime
from robot_warning import send_wechat_message
import concurrent.futures
from textIn.pdf_to_markdown import TextinOcr
from judge_process.textIn_judge import textIn_judge
from typing import NamedTuple, Optional, Tuple
from dataclasses import dataclass
from typing import Dict, Any, Optional
from _traCV.traditional_cv import TraditionalCV as TraCV
from _traCV.judge_api import call_judge_api
from config.config import Config

# 创建线程池用于异步数据库操作和文件删除
_db_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=5, thread_name_prefix="db_async"
)

# TextIn OCR 配置
_app_id = "bda63d908f8c95aef5a8f7a9e6b8c0ac"
_secret_code = "SECRET_CODE_REPLACE_ME"
textin = TextinOcr(_app_id, _secret_code)

textInres_folder = "/data/shell/msplus_textinres"
os.makedirs(textInres_folder, exist_ok=True)

# TextIn OCR 开关：默认关闭，设置为 True 时才会调用 TextIn OCR
ENABLE_TEXTIN_OCR = False


# 推理上下文：统一管理所有状态，避免参数传递
class InferenceContext:
    """推理上下文，管理整个推理流程中的所有状态"""

    def __init__(self, img_url: str, inference_params: dict):
        # 输入参数
        self.img_url = img_url
        self.inference_params = inference_params
        self.request_id = inference_params.get("request_id", "")
        self.question_info = inference_params.get("question_info", {})
        self.question_params = inference_params.get("question_params", {})

        # 图片相关
        self.save_path: Optional[str] = None
        self.flip_res: bool = False
        self.bgr_im: Optional[np.ndarray] = None
        self.image_valid: bool = False
        self.image_error_code: int = 200
        self.image_error_message: str = "Success!"

        # 题目数据
        self.es_answers: list = self.question_info.get("es_answers", [])
        self.page_source: int = self.question_params.get("page_source", 0)
        self.stem: str = self.question_info.get("stem", "")
        self.question_type: int = self.question_params.get("topic_type", 2)
        self.options: list[dict] = self.question_info.get("options", [])
        self.sub_index: int = self.question_params.get("sub_index", 0)

        # 预处理后的题目数据
        self.tidy_stem: str = ""
        self.tidy_es_answers: list = []
        self.need_split: bool = False
        self.models: list = [GEMINI_3_FLASH, "qwen-vl-ocr-latest"]

        # 数据库参数
        self.db_params: dict = {}

        # API调用结果
        self.main_model_success: bool = False
        self.main_model_answers: list = []
        self.main_model_raw_result: str = ""
        self.main_model_code: int = 200
        self.main_model_message: str = "Success!"

        self.ocr_model_success: bool = False
        self.ocr_model_answers: list = []
        self.ocr_model_raw_result: str = ""

        self.textin_result: dict = {}

        # 最终结果
        self.final_answers: list = []
        self.final_raw_result: str = ""
        self.final_ocr_raw_result: str = ""
        self.is_with_process: Optional[bool] = None

        # CV处理中间结果
        self.cv_middle_results: dict = {}

        # 取消标志：用于强制终止正在执行的LLM任务
        self.llm_cancel_flag = threading.Event()

        # 返回结果
        self.recog_results: dict = {"stu_answers": []}
        self.return_code: int = 200
        self.return_message: str = "Success!"

    def is_success(self) -> bool:
        """检查整个流程是否成功"""
        return self.image_valid and self.main_model_success

    def get_error_info(self) -> Tuple[int, str]:
        """获取错误信息"""
        if not self.image_valid:
            return self.image_error_code, self.image_error_message
        if not self.main_model_success:
            return self.main_model_code, self.main_model_message
        return 200, "Success!"


# TextIn OCR 选项
textin_options = dict(
    apply_document_tree=1,
    apply_merge=1,
    catalog_details=1,
    dpi=144,
    formula_level=0,
    get_excel=0,
    get_image="page",
    markdown_details=1,
    page_count=1000,
    page_details=1,
    char_details=1,
    paratext_mode="annotation",
    parse_mode="scan",
    raw_ocr=1,
    image_output_type="base64str",
    crop_dewarp=0,
)


def build_inference_params(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 question_data.json 构建 inference_params

    Args:
        question_data: question_data.json 的内容

    Returns:
        inference_params 字典
    """
    question_info = question_data.get("question_info", {})
    topic_info = question_info.get("topic_info", {})
    user_info = question_data.get("user_info", {})

    # 提取标准答案
    answers = topic_info.get("answers", [])
    es_answers = []
    for ans in answers:
        if isinstance(ans, dict):
            text = ans.get("text", "")
            if text:
                es_answers.append(text)
        elif isinstance(ans, str):
            es_answers.append(ans)

    # 提取题目文本
    stem_obj = topic_info.get("stem", {})
    if isinstance(stem_obj, dict):
        stem = stem_obj.get("text", "")
    else:
        stem = str(stem_obj)

    # 构建 question_info
    question_info_dict = {"es_answers": es_answers, "stem": stem}

    # 构建 question_params
    student_user_id = user_info.get("student_user_id")
    topic_id = topic_info.get("topic_id")
    topic_type = topic_info.get("topic_type")
    question_id = question_info.get("question_id")
    sub_index = topic_info.get("sub_index", 0)

    question_params = {
        "student_user_id": student_user_id,
        "topic_id": topic_id,
        "topic_type": topic_type,
        "sub_index": sub_index,
    }

    if question_id is not None:
        question_params["question_id"] = question_id
    else:
        question_params["question_id"] = -1

    # 默认 page_source
    question_params["page_source"] = 0

    # 构建 inference_params
    inference_params = {
        "question_info": question_info_dict,
        "question_params": question_params,
    }

    return inference_params


def call_cv_processor(
    ctx: InferenceContext, debug: bool = False, debug_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    调用 TraditionalCV 处理器进行图像处理和OCR识别

    Args:
        ctx: 推理上下文对象
        debug: 是否启用调试模式，默认 False
        debug_dir: 调试文件保存目录，如果为 None 则使用默认目录

    Returns:
        处理结果字典，包含：
        - boxes: 检测框列表
        - texts: 识别文本列表
        - num_detections: 检测框数量
    """
    try:
        # 初始化 cv_middle_results
        ctx.cv_middle_results = {}

        # 检查图像是否有效
        if ctx.bgr_im is None or ctx.save_path is None:
            logger.error(f"{ctx.request_id}_TraditionalCV处理失败: 图像无效或路径为空")
            ctx.cv_middle_results["boxes"] = []
            ctx.cv_middle_results["ocr_answers"] = []
            return {
                "boxes": [],
                "texts": [],
                "num_detections": 0,
                "error": "图像无效或路径为空",
            }

        # 初始化 TraditionalCV 处理器
        # 从配置中读取 API URL
        layout_api_url = Config.LAYOUT_API_URL
        local_paddle_ocr_url = Config.LOCAL_PADDLE_OCR_URL
        ocr_blanks_recog_url = Config.OCR_BLANKS_RECOG_URL
        layout_choice_api_url = Config.LAYOUT_CHOICE_API_URL
        print(f"layout_choice_api_url: {layout_choice_api_url}")

        cv_processor = TraCV(
            layout_api_url=layout_api_url,
            local_paddle_ocr_url=local_paddle_ocr_url,
            ocr_blanks_recog_url=ocr_blanks_recog_url,
            Layout_choice_api_url=layout_choice_api_url,
            debug=debug,
            debug_dir=debug_dir,
        )

        # 读取图像
        image = cv2.imread(ctx.save_path)
        if image is None:
            logger.error(
                f"{ctx.request_id}_TraditionalCV处理失败: 无法读取图像文件 {ctx.save_path}"
            )
            ctx.cv_middle_results["boxes"] = []
            ctx.cv_middle_results["ocr_answers"] = []
            return {
                "boxes": [],
                "texts": [],
                "num_detections": 0,
                "error": f"无法读取图像文件 {ctx.save_path}",
            }

        # 1. 图像预处理
        processed_image = cv_processor.preprocess(image)
        if processed_image is None:
            processed_image = image

        # 2. 根据题目类型选择不同的处理方式
        topic_type = ctx.question_params.get("topic_type", 2)
        
        if topic_type == 1:
            # 选择题：调用 recognize_choice，使用 bgr_im 并传递 request_id 用于日志
            #pdb.set_trace()
            ocr_answers = cv_processor.recognize_choice(ctx.bgr_im, request_id=ctx.request_id)
            ctx.cv_middle_results["boxes"] = []  # 选择题不需要检测框
            ctx.cv_middle_results["ocr_answers"] = ocr_answers
            
            logger.info(
                f"{ctx.request_id}_TraditionalCV选择题识别完成: {ocr_answers}"
            )
            
            # 构建返回结果
            result = {
                "boxes": [],
                "texts": ocr_answers,
                "num_detections": len(ocr_answers),
            }
        else:
            # 非选择题：原有的填空识别流程
            # 2.1 获取检测框
            detected_boxes = cv_processor.get_detection_boxes(processed_image)
            ctx.cv_middle_results["boxes"] = detected_boxes

            logger.info(
                f"{ctx.request_id}_TraditionalCV检测到 {len(detected_boxes)} 个填空区域"
            )

            # 2.2 OCR识别
            inference_params = {
                "question_info": ctx.question_info,
                "question_params": ctx.question_params,
            }
            ocr_answers = cv_processor.recognize(
                processed_image, detected_boxes, inference_params
            )
            ctx.cv_middle_results["ocr_answers"] = ocr_answers

            logger.info(f"{ctx.request_id}_TraditionalCV识别完成: {ocr_answers}")

            # 构建返回结果
            result = {
                "boxes": detected_boxes,
                "texts": ocr_answers,
                "num_detections": len(detected_boxes),
            }

        return result
    except Exception as e:
        logger.error(f"{ctx.request_id}_TraditionalCV处理失败: {str(e)}")
        # 初始化空结果
        ctx.cv_middle_results = {"boxes": [], "ocr_answers": []}
        # 返回空结果
        return {"boxes": [], "texts": [], "num_detections": 0, "error": str(e)}


def call_textin_ocr(img_url):
    """
    调用 TextIn OCR 服务
    """
    try:
        textin_response = textin.recognize_pdf2md(img_url, textin_options, is_url=True)

        if textin_response.status_code == 200:
            response_data = textin_response.json()
            if "result" in response_data:
                return {
                    "success": True,
                    "status_code": 200,
                    "result": response_data.get("result"),
                    "response": response_data,
                }
            else:
                return {
                    "success": False,
                    "status_code": 403,
                    "result": None,
                    "response": None,
                    "error": "TextIn API响应中缺少result字段",
                }
        else:
            return {
                "success": False,
                "status_code": textin_response.status_code,
                "result": None,
                "response": None,
                "error": f"TextIn API请求失败，状态码: {textin_response.status_code}",
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status_code": 408,
            "result": None,
            "response": None,
            "error": "TextIn API调用超时(超过5秒)",
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "result": None,
            "response": None,
            "error": f"TextIn API调用异常: {str(e)}",
        }


def _download_and_validate_image(
    ctx: InferenceContext, save_folder: str = "/data/shell/llm_blanks_imgs"
):
    """
    下载图片并验证，结果直接写入 context

    Args:
        ctx: 推理上下文
        save_folder: 图片保存文件夹路径
    """
    # 创建保存文件夹
    os.makedirs(save_folder, exist_ok=True)

    # 构建保存路径
    ctx.save_path = os.path.join(save_folder, f"{ctx.request_id}.jpg")

    # 下载图片
    try:
        # 判断下载时的 img_url 是否需要替换为 internal 域名，仅下载时变更，不影响 ctx.img_url
        def _is_local():
            from config import Config
            # 如果 .env 配置 IMG_URL_REPLACE 为 False，则不开启 img_url 替换，否则替换（默认 True）
            return not Config.get_bool("IMG_URL_REPLACE", True)

        img_url_for_download = ctx.img_url
        if not _is_local() and img_url_for_download.startswith("https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/"):
            img_url_for_download = img_url_for_download.replace(
                "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/",
                "https://aixuexi-jzx-file.oss-cn-beijing-internal.aliyuncs.com/",
                1,
            )
        download_from_url(img_url_for_download, ctx.save_path)
        ctx.bgr_im = cv2.imread(ctx.save_path)

        if ctx.bgr_im is None:
            # 图片读取失败
            ctx.image_valid = False
            ctx.image_error_code = 500
            ctx.image_error_message = "Failed to read image file"
            return
    except Exception as e:
        # 下载或读取异常
        logger.error(f"{ctx.request_id}_图片下载失败: {str(e)}")
        ctx.image_valid = False
        ctx.image_error_code = 500
        ctx.image_error_message = f"Image download failed: {str(e)}"
        return

    # 准备数据库参数（主/OCR prompt 在并发 LLM 线程内写入，先占位便于最终入库）
    ctx.db_params = {
        **ctx.question_params,
        **ctx.question_info,
        **{
            "request_id": ctx.request_id,
            "image_url": ctx.img_url,
            "main_prompt": "",
            "ocr_prompt": "",
        },
    }

    # 异步保存请求输入记录（不阻塞主流程）
    def _async_save_request_input():
        try:
            db_mysql.insert_or_update_ocr_res(ctx.db_params, mode="request_input")
        except Exception as e:
            logger.error(f"{ctx.request_id}_异步保存请求输入失败: {str(e)}")

    _db_executor.submit(_async_save_request_input)

    # 验证1: 白背景检测
    if filter_white_backgrounds_update(ctx.bgr_im):
        # 白背景图片，返回错误
        ctx.db_params["request_code"] = 302
        ctx.db_params["stu_answers"] = []
        ctx.db_params["raw_result"] = ""

        # 异步保存错误结果和删除文件（不阻塞返回）
        def _async_save_error():
            try:
                mysql_res = db_mysql.insert_or_update_ocr_res(ctx.db_params)
                if not mysql_res:
                    logger.info(f"{ctx.request_id} insert failed {ctx.db_params}")
                else:
                    logger.info(f"{ctx.request_id} insert success {ctx.db_params}")
                remove_file(ctx.save_path)
            except Exception as e:
                logger.error(f"{ctx.request_id}_异步保存白背景错误失败: {str(e)}")

        _db_executor.submit(_async_save_error)

        ctx.image_valid = False
        ctx.image_error_code = 302
        ctx.image_error_message = "empty image"
        return

    # 验证2: 轮廓裁剪检测
    bgr_im_cropped, is_empty, better2crop = contours_pipeline1(ctx.bgr_im.copy())
    if is_empty:
        # 轮廓裁剪后为空，返回错误
        ctx.db_params["request_code"] = 302
        ctx.db_params["stu_answers"] = []
        ctx.db_params["raw_result"] = ""

        # 异步保存错误结果和删除文件（不阻塞返回）
        def _async_save_error():
            try:
                mysql_res = db_mysql.insert_or_update_ocr_res(ctx.db_params)
                if not mysql_res:
                    logger.info(f"{ctx.request_id} insert failed {ctx.db_params}")
                else:
                    logger.info(f"{ctx.request_id} insert success {ctx.db_params}")
                remove_file(ctx.save_path)
            except Exception as e:
                logger.error(f"{ctx.request_id}_异步保存轮廓裁剪错误失败: {str(e)}")

        _db_executor.submit(_async_save_error)

        ctx.image_valid = False
        ctx.image_error_code = 302
        ctx.image_error_message = "empty image"
        return

    # 验证通过
    ctx.image_valid = True


def _prepare_question_data(ctx: InferenceContext):
    """
    题目数据预处理：题干处理、答案处理、prompt生成、消息创建，结果直接写入 context

    Args:
        ctx: 推理上下文
    """
    # 题干处理：标准化题干，判断是否需要分割
    ctx.tidy_stem, ctx.need_split = tidy_es_stem(
        ctx.stem, len(ctx.es_answers), ctx.es_answers, ctx.question_type, ctx.options
    )

    # 标准答案处理：标准化答案格式
    ctx.tidy_es_answers = tidy_es_content(
        ctx.es_answers, need_split=ctx.need_split, question_type=ctx.question_type
    )


def _call_single_main_model(
    model: str, messages: list, ctx: InferenceContext
) -> Tuple[bool, str, list, int, str]:
    """
    调用单个主模型 API 并解析结果，不修改 context。
    用于双模型并发调用时的单路结果。

    Returns:
        (success, raw_result, answers, code, message)
    """
    try:
        response_text, res_code = completions(messages, model)
        if res_code != 200:
            logger.info(
                f"{ctx.request_id}_主模型({model})请求失败: {str(response_text)}, status_code: {res_code}"
            )
            return False, response_text, [], res_code, response_text

        logger.info(f"{ctx.request_id}_主模型({model})_成功_res: {response_text}")

        try:
            response = json.loads(response_text)
        except Exception as e:
            logger.info(
                f"{ctx.request_id}_主模型({model})不是dict: {str(response_text)}"
            )
            return False, response_text, [], 444, response_text

        if isinstance(response, dict) and "choices" in response:
            raw_result = response["choices"][0]["message"]["content"]
        else:
            logger.info(
                f"{ctx.request_id}_主模型({model}) choices not in dict: {response}"
            )
            raw_result = str(response)

        logger.info(f"{ctx.request_id}_主模型({model})_原始识别结果: {raw_result}")

        main_model_result = extract_main_model_result(raw_result)
        answers = clean_recognition_result(main_model_result)
        answers = smart_split_answers_v2(
            answers, 0, len(ctx.tidy_es_answers), page_source=ctx.page_source
        )
        answers = match_answers0(ctx.tidy_es_answers, answers)
        answers = match_answers(ctx.tidy_es_answers, answers)

        return True, raw_result, answers, 200, "Success!"
    except Exception as e:
        logger.error(f"{ctx.request_id}_主模型({model})处理异常: {str(e)}")
        return False, "", [], 500, f"Exception: {str(e)}"


def _call_and_process_main_model(ctx: InferenceContext):
    """
    线程1：同时调用 GEMINI_3_FLASH 与 QWEN3_VL_PLUS，优先使用 GEMINI 结果；
    当 GEMINI 超时或失败时使用 QWEN3_VL_PLUS 兜底，结果写入 context。
    """
    if ctx.llm_cancel_flag.is_set():
        logger.info(f"{ctx.request_id}_主模型任务已被取消，提前退出")
        return

    try:
        prompt_text = general_prompt_engineering(
            ctx.question_type,
            ctx.tidy_stem,
            len(ctx.tidy_es_answers),
            mode="plus",
            sub_index=ctx.sub_index,
        )
        ctx.db_params["main_prompt"] = prompt_text
        messages = [create_image_message(text=prompt_text, images=[ctx.save_path])]

        logger.debug(f"[DEBUG] ---- Main Model Debug Info ----")
        logger.debug(f"[DEBUG] prompt_text: {prompt_text}")

        if ctx.llm_cancel_flag.is_set():
            logger.info(f"{ctx.request_id}_主模型任务在API调用前已被取消，提前退出")
            return

        # 并发调用 GEMINI_3_FLASH 与 QWEN3_VL_PLUS
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_gemini = executor.submit(
                _call_single_main_model, GEMINI_3_FLASH, messages, ctx
            )
            future_qwen = executor.submit(
                _call_single_main_model, QWEN3_VL_PLUS, messages, ctx
            )

            try:
                result_gemini = future_gemini.result()
            except Exception as e:
                logger.warning(
                    f"{ctx.request_id}_主模型({GEMINI_3_FLASH})等待异常(如超时): {e}"
                )
                result_gemini = (False, "", [], 500, str(e))

            try:
                result_qwen = future_qwen.result()
            except Exception as e:
                logger.warning(f"{ctx.request_id}_主模型({QWEN3_VL_PLUS})等待异常: {e}")
                result_qwen = (False, "", [], 500, str(e))

        if ctx.llm_cancel_flag.is_set():
            logger.info(f"{ctx.request_id}_主模型任务在API调用后已被取消，提前退出")
            return

        # 优先使用 GEMINI；失败或超时时用 QWEN3_VL_PLUS 兜底
        success_gemini, raw_gemini, answers_gemini, code_gemini, msg_gemini = (
            result_gemini
        )
        success_qwen, raw_qwen, answers_qwen, code_qwen, msg_qwen = result_qwen

        if success_gemini:
            ctx.main_model_success = True
            ctx.main_model_raw_result = raw_gemini
            ctx.main_model_answers = answers_gemini
            ctx.main_model_code = 200
            ctx.main_model_message = "Success!"
            logger.info(f"{ctx.request_id}_主模型使用 {GEMINI_3_FLASH} 结果")
        elif success_qwen:
            ctx.main_model_success = True
            ctx.main_model_raw_result = raw_qwen
            ctx.main_model_answers = answers_qwen
            ctx.main_model_code = 200
            ctx.main_model_message = "Success!"
            logger.info(
                f"{ctx.request_id}_主模型 {GEMINI_3_FLASH} 失败/超时，使用 {QWEN3_VL_PLUS} 兜底"
            )
        else:
            ctx.main_model_success = False
            ctx.main_model_raw_result = raw_gemini or raw_qwen
            ctx.main_model_answers = []
            ctx.main_model_code = code_gemini
            ctx.main_model_message = msg_gemini
            logger.info(
                f"{ctx.request_id}_主模型双路均失败: gemini({code_gemini}) qwen({code_qwen})"
            )
    except Exception as e:
        logger.error(f"{ctx.request_id}_主模型处理异常: {str(e)}")
        ctx.main_model_success = False
        ctx.main_model_code = 500
        ctx.main_model_message = f"Exception: {str(e)}"


def _call_and_process_ocr_model(ctx: InferenceContext):
    """
    线程2：调用OCR模型API并处理结果，结果直接写入 context

    Args:
        ctx: 推理上下文
    """
    # 检查是否已被取消
    if ctx.llm_cancel_flag.is_set():
        logger.info(f"{ctx.request_id}_OCR模型任务已被取消，提前退出")
        return

    model = ctx.models[1]  # OCR模型
    try:
        # 调用API
        prompt_text = general_prompt_engineering(
            ctx.question_type,
            ctx.tidy_stem,
            len(ctx.tidy_es_answers),
            mode="ocr",
            sub_index=ctx.sub_index,
        )
        ctx.db_params["ocr_prompt"] = prompt_text
        messages = [create_image_message(text=prompt_text, images=[ctx.save_path])]

        # 调用API前再次检查取消标志
        if ctx.llm_cancel_flag.is_set():
            logger.info(f"{ctx.request_id}_OCR模型任务在API调用前已被取消，提前退出")
            return

        response_text, res_code = completions(messages, model)

        # API调用完成后立即检查取消标志
        if ctx.llm_cancel_flag.is_set():
            logger.info(f"{ctx.request_id}_OCR模型任务在API调用后已被取消，提前退出")
            return

        # 检查状态码
        if res_code != 200:
            logger.info(
                f"{ctx.request_id}_OCR模型({model})请求失败: {str(response_text)}, status_code: {res_code}"
            )
            ctx.ocr_model_success = False
            ctx.ocr_model_raw_result = ""
            ctx.ocr_model_answers = [""] * len(ctx.tidy_es_answers)
            return

        # JSON解析
        try:
            ocr_response_json = json.loads(response_text)
        except Exception as e:
            logger.info(
                f"{ctx.request_id}_OCR模型({model})不是dict: {str(response_text)}"
            )
            ctx.ocr_model_success = False
            ctx.ocr_model_raw_result = ""
            ctx.ocr_model_answers = [""] * len(ctx.tidy_es_answers)
            return

        # 提取响应内容
        if isinstance(ocr_response_json, dict) and "choices" in ocr_response_json:
            ctx.ocr_model_raw_result = ocr_response_json["choices"][0]["message"][
                "content"
            ]
        else:
            ctx.ocr_model_raw_result = str(ocr_response_json)

        # 答案处理流程
        ocr_answers = clean_recognition_result(ctx.ocr_model_raw_result)
        ocr_answers = smart_split_answers_v2(ocr_answers, 1, len(ctx.tidy_es_answers))
        ocr_answers = match_answers0(ctx.tidy_es_answers, ocr_answers, mode="ocr")
        ocr_answers = match_answers(ctx.tidy_es_answers, ocr_answers)

        ctx.ocr_model_success = True
        ctx.ocr_model_answers = ocr_answers
    except Exception as e:
        logger.error(f"{ctx.request_id}_OCR模型({model})处理异常: {str(e)}")
        ctx.ocr_model_success = False
        ctx.ocr_model_raw_result = ""
        ctx.ocr_model_answers = [""] * len(ctx.tidy_es_answers)


def _call_and_process_textin(
    ctx: InferenceContext, textin_result_folder: str = "/data/shell/msplus_textinres"
):
    """
    线程3：调用TextIn OCR API并保存结果，结果直接写入 context

    Args:
        ctx: 推理上下文
        textin_result_folder: 结果保存文件夹
    """
    textin_start_time = time.time()

    try:
        # 调用TextIn OCR API（带5秒超时）
        ctx.textin_result = call_textin_ocr(ctx.img_url)

        textin_elapsed = time.time() - textin_start_time
        logger.info(
            f"{ctx.request_id}_textIn_OCR_完成，耗时: {round(textin_elapsed, 2)}秒"
        )

        # 保存结果到文件
        tiresp = os.path.join(textin_result_folder, f"{ctx.request_id}.json")
        with open(tiresp, "w") as f:
            json.dump(ctx.textin_result, f)

        # 记录日志
        if ctx.textin_result.get("success"):
            logger.info(f"{ctx.request_id}_textIn_OCR_成功")
        else:
            logger.info(
                f"{ctx.request_id}_textIn_OCR_失败: {ctx.textin_result.get('error', '未知错误')}"
            )
    except Exception as e:
        textin_elapsed = time.time() - textin_start_time
        logger.error(
            f"{ctx.request_id}_textIn_OCR_异常: {str(e)}, 耗时: {round(textin_elapsed, 2)}秒"
        )
        ctx.textin_result = {
            "success": False,
            "status_code": 500,
            "result": None,
            "response": None,
            "error": f"TextIn API调用异常: {str(e)}",
        }


def _process_traditional_cv(ctx: InferenceContext):
    """
    传统CV处理：调用CV处理器和判题API，结果直接写入 context

    Args:
        ctx: 推理上下文
    """
    cv_t0 = time.time()
    try:
        call_cv_processor(ctx)
        call_judge_api(ctx)
        judge_result = ctx.cv_middle_results.get("judge_result", {})
        is_correct = judge_result.get("is_correct", None)

        cv_t1 = time.time()
        time_cost = f"{np.round(cv_t1-cv_t0, 4)}s"
        if is_correct == 1:
            ctx.cv_middle_results["cv_recall"] = 1
            logger.info(
                f"{ctx.request_id}_call_cv_prossor success: and RECALLLLL!!!!!, time_cost:{time_cost}"
            )
        else:
            ctx.cv_middle_results["cv_recall"] = 0
            logger.info(
                f"{ctx.request_id}_call_cv_prossor success: and not RECALL!!!!!, time_cost:{time_cost}"
            )
    except Exception as e:
        logger.info(f"{ctx.request_id}_call_cv_prossor error: {e}")
        ctx.cv_middle_results["cv_recall"] = -1
    logger.info(f"{ctx.request_id}_middle_results: {ctx.cv_middle_results}")


def _process_concurrent(ctx: InferenceContext):
    """
    并发处理：三个线程分别调用API并处理结果，结果直接写入 context

    Args:
        ctx: 推理上下文
    """
    # 检查是否已被取消
    if ctx.llm_cancel_flag.is_set():
        logger.info(f"{ctx.request_id}_LLM任务已被取消，提前退出")
        return

    # 记录API请求开始时间
    api_start_time = time.time()

    # 并发调用三个API并处理结果
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # 提交主模型和OCR模型任务（这两个必须执行）
        future_main = executor.submit(_call_and_process_main_model, ctx)
        future_ocr = executor.submit(_call_and_process_ocr_model, ctx)

        # 根据开关决定是否调用 TextIn OCR
        future_textin = None
        if ENABLE_TEXTIN_OCR:
            future_textin = executor.submit(_call_and_process_textin, ctx)
        else:
            # 开关关闭时，设置默认的 textin_result
            ctx.textin_result = {
                "success": False,
                "status_code": 200,
                "result": None,
                "response": None,
                "error": "TextIn OCR开关已关闭",
            }
            logger.info(f"{ctx.request_id}_TextIn_OCR开关已关闭，跳过调用")

        # 等待主模型和OCR模型完成（这两个必须等待）
        # 检查取消标志，如果已取消则提前退出
        if ctx.llm_cancel_flag.is_set():
            logger.info(f"{ctx.request_id}_LLM任务已被取消，停止等待API结果")
            return

        try:
            future_main.result()
        except Exception as e:
            if ctx.llm_cancel_flag.is_set():
                logger.info(f"{ctx.request_id}_LLM任务已被取消，主模型任务中断")
                return
            raise

        if ctx.llm_cancel_flag.is_set():
            logger.info(f"{ctx.request_id}_LLM任务已被取消，停止等待OCR结果")
            return

        try:
            future_ocr.result()
        except Exception as e:
            if ctx.llm_cancel_flag.is_set():
                logger.info(f"{ctx.request_id}_LLM任务已被取消，OCR任务中断")
                return
            raise

        # 如果 TextIn OCR 开关打开，等待其完成（设置5秒超时）
        if ENABLE_TEXTIN_OCR and future_textin is not None:
            textin_start_time = time.time()
            try:
                for future in concurrent.futures.as_completed(
                    [future_textin], timeout=5
                ):
                    future.result()
                    textin_elapsed = time.time() - textin_start_time
                    logger.info(
                        f"{ctx.request_id}_textIn_OCR_完成，耗时: {round(textin_elapsed, 2)}秒"
                    )
                    break
            except concurrent.futures.TimeoutError:
                # 超时后尝试取消任务
                textin_elapsed = time.time() - textin_start_time
                future_textin.cancel()
                logger.info(
                    f"{ctx.request_id}_textIn_OCR_超时(超过5秒)，实际耗时: {round(textin_elapsed, 2)}秒，已取消任务"
                )
                ctx.textin_result = {
                    "success": False,
                    "status_code": 403,
                    "result": None,
                    "response": None,
                    "error": "TextIn API调用超时(超过5秒)",
                }

    # 记录API请求结束时间
    api_end_time = time.time()
    logger.info(
        f"{ctx.request_id}_API请求总耗时: {round(api_end_time - api_start_time, 2)} 秒"
    )


def _merge_results(ctx: InferenceContext):
    """
    多结果融合：融合主模型、OCR模型和TextIn的结果，结果直接写入 context

    Args:
        ctx: 推理上下文
    """
    # 提取基础结果
    answers = ctx.main_model_answers
    ocr_answers = ctx.ocr_model_answers

    # 结果融合策略1：单答案场景 - 答案匹配
    # if len(answers) == 1 and len(ctx.tidy_es_answers) == 1 and ctx.ocr_model_success and ctx.tidy_es_answers[0] == answers[0] and (ctx.question_type != 3):
    #     answers = reedit_by_multi_results(answers, ctx.tidy_es_answers, ocr_answers)

    # 结果融合策略2：单答案场景 - 答案不匹配
    if (
        len(answers) == 1
        and len(ctx.tidy_es_answers) == 1
        and ctx.ocr_model_success
        and ctx.tidy_es_answers[0] != answers[0]
        and (ctx.question_type != 3)
    ):
        answers = reedit_by_multi_results1(answers, ctx.tidy_es_answers, ocr_answers)

    # 结果融合策略3：多答案场景 - 如果主结果不匹配但OCR结果匹配，使用OCR结果
    if len(ctx.es_answers) > 1:
        if ctx.es_answers != answers and ctx.es_answers == ocr_answers:
            answers = ocr_answers

    # 判断是否有手写解答过程
    ctx.is_with_process = textIn_judge(ctx.textin_result, answers)

    # 答案合并：如果需要分割，则合并答案
    if ctx.need_split:
        answers = join_answers(answers, question_type=ctx.question_type)

    # 题目类型转换：如果是判断题（type=3），将标记转换为数字
    if ctx.question_type == 3:
        answers = mark2numbers(answers, ctx.tidy_es_answers)

    # 写入最终结果
    ctx.final_answers = answers
    ctx.final_raw_result = ctx.main_model_raw_result
    ctx.final_ocr_raw_result = ctx.ocr_model_raw_result


def _call_flip_and_save_image(
    ctx: InferenceContext, server_url: str = "https://cv.dev.aixuexi.com/flip-images"
):
    """
    调用flip服务并保存final_res_image

    Args:
        ctx: 推理上下文
        server_url: flip服务URL
    """
    try:
        # 检查是否有有效的图像
        if ctx.bgr_im is None:
            logger.info(f"{ctx.request_id}_flip调用跳过: 无有效图像")
            return False
        if ctx.page_source == 1:
            return False
        h, w, _ = ctx.bgr_im.shape
        if h * w > 930000:
            return False
        if ctx.question_params.get("topic_id", "") in ["6576421", 6576421]:
            return False

        # 调用flip服务
        result, final_res_image, duration = send_request_bgrim(server_url, ctx.bgr_im)

        if result is None or final_res_image is None:
            logger.info(f"{ctx.request_id}_flip调用失败或无final_res_image")
            return False
        if result.get("final_choice", "raw") != "raw":

            # 构建新的保存路径
            new_save_path = ctx.save_path.replace(".jpg", "_flip.jpg")

            # 保存final_res_image
            success = cv2.imwrite(new_save_path, final_res_image)
            if not success:
                logger.error(
                    f"{ctx.request_id}_flip保存final_res_image失败: {new_save_path}"
                )

                return False
            ctx.save_path = new_save_path
            ctx.flip_res = True
            logger.info(
                f"{ctx.request_id}_flip调用成功，最终取舍: {result.get('final_choice', 'empty')}, 保存图像到: {new_save_path}, 耗时: {duration:.4f}s"
            )
            return True

        logger.info(f"{ctx.request_id}_flip调用成功,没有旋转, 耗时: {duration:.4f}s")

        return True

    except Exception as e:
        logger.error(f"{ctx.request_id}_flip调用异常: {str(e)}")
        return False


def _save_final_results_sync(ctx: InferenceContext):
    """
    同步保存最终结果到数据库并清理临时文件（阻塞执行）

    Args:
        ctx: 推理上下文
    """
    # 更新数据库参数
    ctx.db_params["raw_result"] = ctx.final_raw_result
    ctx.db_params["raw_result_ocr"] = ctx.final_ocr_raw_result
    ctx.db_params["request_code"] = 200
    ctx.db_params["stu_answers"] = ctx.final_answers
    ctx.db_params["with_process"] = ctx.is_with_process
    ctx.db_params['choose_cv'] = ctx.cv_middle_results.get("cv_recall",0)
    logger.info(f"db_params: {ctx.db_params}")

    # 保存到数据库
    mysql_res = db_mysql.insert_or_update_ocr_res(ctx.db_params)
    if not mysql_res:
        logger.info(f"{ctx.request_id} insert failed {ctx.db_params}")
    else:
        logger.info(f"{ctx.request_id} insert success {ctx.db_params}")

    # 清理临时文件
    if ctx.save_path:
        remove_file(ctx.save_path)
    if ctx.flip_res:
        raw_save_path = ctx.save_path.replace("_flip.jpg", ".jpg")
        remove_file(raw_save_path)


def _save_final_results(ctx: InferenceContext, async_mode: bool = False):
    """
    保存最终结果到数据库并清理临时文件

    Args:
        ctx: 推理上下文
        async_mode: 是否异步执行（不阻塞返回），默认False
    """
    if async_mode:
        # 异步执行：提交到线程池，不阻塞主流程
        def _async_save():
            try:
                _save_final_results_sync(ctx)
            except Exception as e:
                logger.error(f"{ctx.request_id}_异步保存结果失败: {str(e)}")

        _db_executor.submit(_async_save)
        logger.info(f"{ctx.request_id}_已提交异步保存任务，立即返回")
    else:
        # 同步执行：阻塞等待完成
        _save_final_results_sync(ctx)


def _handle_error_and_save(ctx: InferenceContext, async_mode: bool = True):
    """
    统一处理错误并保存到数据库，结果直接写入 context

    Args:
        ctx: 推理上下文
        async_mode: 是否异步执行（不阻塞返回），默认True
    """
    # 更新数据库参数
    ctx.db_params["request_code"] = ctx.return_code
    ctx.db_params["stu_answers"] = []
    ctx.db_params["raw_result"] = ""

    # 设置返回结果
    ctx.recog_results = {"stu_answers": [""] * len(ctx.es_answers)}

    if async_mode:
        # 异步执行：提交到线程池，不阻塞主流程
        def _async_error_save():
            try:
                # 保存到数据库
                mysql_res = db_mysql.insert_or_update_ocr_res(ctx.db_params)
                if not mysql_res:
                    logger.info(f"{ctx.request_id} insert failed {ctx.db_params}")
                else:
                    logger.info(f"{ctx.request_id} insert success {ctx.db_params}")

                # 清理临时文件
                if ctx.save_path:
                    remove_file(ctx.save_path)
            except Exception as e:
                logger.error(f"{ctx.request_id}_异步保存错误结果失败: {str(e)}")

        _db_executor.submit(_async_error_save)
        logger.info(f"{ctx.request_id}_已提交异步错误保存任务，立即返回")
    else:
        # 同步执行：阻塞等待完成
        mysql_res = db_mysql.insert_or_update_ocr_res(ctx.db_params)
        if not mysql_res:
            logger.info(f"{ctx.request_id} insert failed {ctx.db_params}")
        else:
            logger.info(f"{ctx.request_id} insert success {ctx.db_params}")

        # 清理临时文件
        if ctx.save_path:
            remove_file(ctx.save_path)


def _create_request_id() -> str:
    task_id = str(uuid.uuid4())
    dt = datetime.now()
    return f"{dt.year}_{dt.month}_{dt.day}_{task_id}"


def _part_content(part) -> str:
    if part is None:
        return ""
    return part.text or part.html or ""


def _normalize_blanks_recog_request(request: dict) -> Tuple[str, dict]:
    inference_params = dict(request)
    img_url = inference_params.get("img_url")
    if not img_url:
        raise ValueError("miss img_url")

    inference_params.setdefault("request_id", _create_request_id())
    question_params = inference_params.setdefault("question_params", {})
    if question_params.get("question_id", None) is None:
        question_params["question_id"] = -1
    if question_params.get("from", None) is None:
        question_params["page_source"] = 0
    else:
        question_params["page_source"] = question_params.get("from", None)

    return img_url, inference_params


def _normalize_judge_request(request) -> Tuple[str, dict]:
    topic_info = request.question_info.topic_info
    raw_img_url = request.question_info.img_url
    img_url = raw_img_url[0] if isinstance(raw_img_url, list) else raw_img_url
    if not img_url:
        raise ValueError("miss img_url")

    question_info = {
        "es_answers": [],
        "stem": _part_content(topic_info.stem),
        "options": [],
    }
    if topic_info.answers:
        question_info["es_answers"] = [_part_content(ans) for ans in topic_info.answers]
    if topic_info.options:
        question_info["options"] = [
            {
                "text": opt.text or "",
                "html": opt.html or "",
            }
            for opt in topic_info.options
        ]

    if not question_info["stem"]:
        raise ValueError("info miss stem")
    if not question_info["es_answers"]:
        raise ValueError("info miss es_answers")

    question_params = {
        "student_user_id": request.student_info.student_user_id,
        "topic_id": topic_info.topic_id,
        "topic_type": topic_info.topic_type,
        "sub_index": topic_info.sub_index if topic_info.sub_index is not None else -1,
        "question_id": (
            request.question_info.question_id
            if request.question_info.question_id is not None
            else -1
        ),
        "page_source": request.page_source if request.page_source is not None else 0,
    }

    request_id = request.request_id or _create_request_id()
    request.request_id = request_id
    inference_params = {
        "request_id": request_id,
        "question_info": question_info,
        "question_params": question_params,
    }

    return img_url, inference_params


def _normalize_inference_request(request) -> Tuple[str, dict]:
    if isinstance(request, dict):
        return _normalize_blanks_recog_request(request)
    if hasattr(request, "student_info") and hasattr(request, "question_info"):
        return _normalize_judge_request(request)
    raise TypeError(f"unsupported inference request type: {type(request).__name__}")


def inference_main(request, debug=False):
    """
    主推理函数：使用上下文对象管理所有状态，避免参数传递

    Args:
        request: 推理请求，支持 /blanks_recog 的 dict 和 JudgeRequest
        debug: 调试模式

    Returns:
        Tuple[dict, int, str]: (recog_results, code, message)
    """
    img_url, inference_params = _normalize_inference_request(request)

    # 创建上下文对象，统一管理所有状态
    ctx = InferenceContext(img_url, inference_params)

    # 1. 下载并验证图片
    _download_and_validate_image(ctx)

    # 如果验证失败，直接返回错误结果
    if not ctx.image_valid:
        ctx.return_code, ctx.return_message = ctx.get_error_info()
        _handle_error_and_save(ctx)
        return ctx.recog_results, ctx.return_code, ctx.return_message

    # 2. 调用flip服务并保存final_res_image
    # _call_flip_and_save_image(ctx)

    # 3. 题目数据预处理
    _prepare_question_data(ctx)

    # 4. 并发处理：传统CV和LLM模型并发执行
    ctx.cv_middle_results["user_Tra"] = 0
    use_traditional_cv = (ctx.question_type == 2 or ctx.question_type == 1)
    if ctx.page_source == 1:
        use_traditional_cv = False
    # use_traditional_cv=False

    if use_traditional_cv:
        ctx.cv_middle_results["useTra"] = 1
        # 初始化传统CV结果
        ctx.cv_middle_results["cv_recall"] = -1

    # 并发执行传统CV和LLM模型处理
    # 注意：不使用with语句，以便在CV快速返回时能够立即返回，不等待线程池退出
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    try:
        futures = {}

        # 提交LLM模型处理任务（必须执行）
        future_llm = executor.submit(_process_concurrent, ctx)
        futures["llm"] = future_llm

        # 如果启用传统CV，提交传统CV任务
        if use_traditional_cv:
            future_cv = executor.submit(_process_traditional_cv, ctx)
            futures["cv"] = future_cv

        # 如果启用了传统CV，需要检查哪个先完成
        if use_traditional_cv:
            # CV超时时间：3秒
            CV_TIMEOUT = 3.0
            cv_start_time = time.time()
            cv_completed = False

            # 使用 as_completed 同时监控CV和LLM
            for future in concurrent.futures.as_completed([future_cv, future_llm]):
                try:
                    future.result()
                    if future == future_cv:
                        cv_completed = True
                        cv_elapsed = time.time() - cv_start_time

                        # 检查CV是否在3秒内完成
                        if cv_elapsed <= CV_TIMEOUT:
                            # 检查传统CV判题结果
                            judge_result = ctx.cv_middle_results.get("judge_result", {})
                            is_correct = judge_result.get("is_correct", None)

                            if is_correct == 1:
                                # 传统CV在3秒内完成且判题正确，直接返回传统CV结果
                                ctx.recog_results["stu_answers"] = (
                                    ctx.cv_middle_results["ocr_answers"]
                                )
                                ctx.recog_results["cv_middle_results"] = (
                                    ctx.cv_middle_results
                                )
                                logger.info(
                                    f"{ctx.request_id}_传统CV在3秒内完成({cv_elapsed:.2f}s)且判题正确，使用传统CV结果，立即返回"
                                )
                                # 设置取消标志，强制终止LLM任务
                                ctx.llm_cancel_flag.set()
                                logger.info(
                                    f"{ctx.request_id}_已设置LLM取消标志，强制终止LLM任务"
                                )
                                # 尝试取消LLM任务（如果还未开始执行）
                                cancel_result = future_llm.cancel()
                                if cancel_result:
                                    logger.info(
                                        f"{ctx.request_id}_LLM任务取消成功（任务还未开始执行）"
                                    )
                                else:
                                    logger.info(
                                        f"{ctx.request_id}_LLM任务已开始执行，将通过取消标志强制终止（后台继续执行但不等待）"
                                    )
                                # 设置最终结果字段，用于入库
                                ctx.final_answers = ctx.cv_middle_results["ocr_answers"]
                                # CV返回时，主模型和OCR模型可能还未运行，设为空字符串
                                ctx.final_raw_result = (
                                    ctx.main_model_raw_result
                                    if ctx.main_model_raw_result
                                    else ""
                                )
                                ctx.final_ocr_raw_result = (
                                    ctx.ocr_model_raw_result
                                    if ctx.ocr_model_raw_result
                                    else ""
                                )
                                # CV返回时，可能没有调用textIn，设为False
                                ctx.is_with_process = False
                                # 异步保存结果到数据库（不阻塞返回）
                                _save_final_results(ctx, async_mode=True)
                                # 立即返回，不等待LLM任务完成
                                # 关闭线程池（不等待任务完成），让LLM任务在后台继续执行
                                executor.shutdown(wait=False)
                                return ctx.recog_results, 200, "Success"
                            else:
                                # 传统CV在3秒内完成但判题不正确，等待LLM结果
                                logger.info(
                                    f"{ctx.request_id}_传统CV在3秒内完成({cv_elapsed:.2f}s)但判题不正确(is_correct={is_correct})，等待LLM结果"
                                )
                        else:
                            # CV超过3秒才完成，忽略CV结果，关闭CV进程，继续只等待LLM
                            logger.info(
                                f"{ctx.request_id}_传统CV超过3秒才完成({cv_elapsed:.2f}s)，忽略CV结果，关闭CV进程，继续只等待LLM"
                            )
                            # 尝试取消CV任务（虽然可能已经完成，但尝试取消）
                            try:
                                cancel_result = future_cv.cancel()
                                if cancel_result:
                                    logger.info(
                                        f"{ctx.request_id}_CV任务取消成功（任务还未开始执行）"
                                    )
                                else:
                                    logger.warning(
                                        f"{ctx.request_id}_CV任务取消失败（任务可能已经开始执行，将继续运行）"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"{ctx.request_id}_取消CV任务异常: {str(e)}"
                                )
                            # 跳出循环前，确保等待LLM完成
                            try:
                                future_llm.result()
                                logger.info(f"{ctx.request_id}_LLM完成，使用LLM结果")
                            except Exception as e:
                                logger.error(
                                    f"{ctx.request_id}_LLM任务执行异常: {str(e)}"
                                )
                                raise
                            # 跳出循环，不再等待CV
                            break
                    elif future == future_llm:
                        # LLM先完成，直接使用LLM结果，不等待CV，立即返回
                        logger.info(
                            f"{ctx.request_id}_LLM先完成，直接使用LLM结果，不等待CV，立即返回"
                        )
                        # 尝试取消CV任务（如果还在运行）
                        if not cv_completed:
                            cancel_result = future_cv.cancel()
                            if cancel_result:
                                logger.info(
                                    f"{ctx.request_id}_CV任务取消成功（任务还未开始执行）"
                                )
                            else:
                                logger.warning(
                                    f"{ctx.request_id}_CV任务取消失败（任务可能已经开始执行，将继续在后台运行但不等待）"
                                )
                        # 跳出循环，继续后续的LLM结果处理流程（结果融合和保存）
                        break
                except Exception as e:
                    logger.error(f"{ctx.request_id}_并发处理异常: {str(e)}")
                    if future == future_cv:
                        cv_completed = True
                    elif future == future_llm:
                        # LLM完成，跳出循环
                        break

            # 如果CV超时（3秒内未完成），确保等待LLM结果
            if not cv_completed:
                cv_elapsed = time.time() - cv_start_time
                if cv_elapsed > CV_TIMEOUT:
                    logger.info(
                        f"{ctx.request_id}_CV任务超时（超过3秒），忽略CV结果，关闭CV进程，继续只等待LLM"
                    )
                    # 尝试取消CV任务
                    cancel_result = future_cv.cancel()
                    if cancel_result:
                        logger.info(
                            f"{ctx.request_id}_CV任务取消成功（任务还未开始执行）"
                        )
                    else:
                        logger.warning(
                            f"{ctx.request_id}_CV任务取消失败（任务可能已经开始执行，将继续运行）"
                        )
                # 确保LLM已完成（如果还没完成则等待）
                try:
                    future_llm.result()
                    logger.info(f"{ctx.request_id}_LLM完成，使用LLM结果")
                except Exception as e:
                    logger.error(f"{ctx.request_id}_LLM任务执行异常: {str(e)}")
                    raise
        else:
            # 未启用传统CV，直接等待LLM结果
            future_llm.result()
    finally:
        # 确保线程池正常关闭（如果还没有关闭的话）
        # 注意：如果CV快速返回，线程池已经在return之前关闭了
        try:
            executor.shutdown(wait=False)  # 不等待任务完成，立即关闭
        except:
            pass  # 如果已经关闭，忽略错误

    # 设置cv_middle_results到recog_results
    ctx.recog_results["cv_middle_results"] = ctx.cv_middle_results

    # 5. 检查主模型结果
    if not ctx.main_model_success:
        send_wechat_message(
            f"qwen-vl error {ctx.main_model_message}, status_code: {ctx.main_model_code}"
        )
        ctx.return_code = ctx.main_model_code
        ctx.return_message = ctx.main_model_message
        _handle_error_and_save(ctx)
        return ctx.recog_results, ctx.return_code, ctx.return_message

    # 6. 结果融合
    _merge_results(ctx)

    # 7. 构建返回结果（在保存前构建，以便快速返回）
    ctx.recog_results = {
        "stu_answers": ctx.final_answers,
        "raw_result": ctx.final_raw_result,
        "cv_middle_results": ctx.cv_middle_results,
    }

    # 8. 异步保存最终结果（不阻塞返回）
    _save_final_results(ctx, async_mode=True)

    # 立即返回，数据库保存和文件删除在后台执行
    return ctx.recog_results, ctx.return_code, ctx.return_message


def inference_main_func(img_url, inference_params, debug=False):
    """兼容旧调用方式：新代码请直接调用 inference_main(request)。"""
    request = dict(inference_params)
    request["img_url"] = img_url
    return inference_main(request, debug=debug)


if __name__ == "__main__":
    question_params = {
        "student_user_id": 11,
        "topic_id": 6576421,
        "question_id": 11,
        "page_source": 0,
        "topic_type": 2,
    }

    # from es_utils.topic_util import query_topic
    # topic_data = query_topic(question_params['topic_id'])
    # if "question" in topic_data:
    #    stem = topic_data["question"]
    # else:
    #    stem = ""
    # stem = '（1）某台电脑以5000元购进，按照15%的利润率定价，这台电脑的售价是&nbsp;元；（2）一束玫瑰花按照80%的利润率定价，利润为40元，这束玫瑰花的进价是&nbsp;元，售价是&nbsp;元；（3）一台冰箱，如果按照25%的利润率定价，定价为1500元，那么这台冰箱的成本是&nbsp;元．'
    # stem = "计算：（1）\(\frac{1}{1\times2}+\frac{1}{2\times3}+\frac{1}{3\times4}+\frac{1}{4\times5}+\frac{1}{5\times6}+\frac{1}{6\times7}=\)&nbsp;．（2）\(\frac{1}{2\times3}+\frac{3}{3\times6}+\frac{5}{6\times11}+\frac{"
    stem = "有A、B两项工程，A工程的工作量是B工程的2倍，甲单独完成B工程需要10天，乙单独完成B工程需要24天，丙单独完成B工程需要40天．现在甲、乙、丙三个人同时开始工作，甲一直做A工程，乙一直做B工程，丙先帮甲做了一段时间，后来又帮乙做，最后两个工程同时完成，则丙帮乙做了________天．"
    # es_answers = ['\\(\\frac{6}{7}\\)', '\\(\\frac{49}{102}\\)']
    # es_answers = ['10']
    es_answers = ["\\(\\sqrt{2}\\)&nbsp;", "\\(\\sqrt{n+1}\\)&nbsp;"]
    es_answers = ["\\(5\\sqrt{5}\\)", "\\(4\\sqrt{3}\\)"]
    es_answers = ["$\\sqrt{2}$", "$\\sqrt{n+1}$"]
    es_answers = ["B"]
    es_answers = ["\\frac{3}{11}", "\\frac{8}{11}", "\\frac{8}{11}"]
    es_answers = ["17"]
    es_answers = ["12", "31", "6", "30", "一样"]
    es_answers = ["9"]
    es_answers = ["五", "三"]
    es_answers = ["7", "36"]
    es_answers = ["5750", "50", "90", "1200"]
    es_answers = ["\\(\\frac{8}{33}\\)&nbsp;"]
    question_info = {"stem": stem, "es_answers": es_answers}
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1764643438455_0_2784443.1764643438441.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1764671923169_5_8030631.1764671923161.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1764987485677_5_10026502.1764987485667.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1764986165340_1_5939887.1764986165332.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1764985998440_0_7167746.1764985998433.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1764987465227_2_8255605.1764987465220.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1765188669578_2_8746123.1765188669570.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1765188648772_1_8746123.1765188648765.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1765273559978_0_469815.1765273559964.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1765881564863_1_8771599.1765881564853.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1765883621539_3_8759888.1765883621531.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1765973731845_14_10106635.1765973731837.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1765972007849_8_10143594.1765972007843.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1765973437732_8_7914351.1765973437726.jpg"
    # img_url = "https://q-independent.aixuexi.com/B:1002:K/1766160000/f91d6524eb8e4087aec3fee50fa36c51"

    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1763980288538_1_4332815.1763980288532.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1768631517994_1_7914416.1768631517985.jpg"
    inference_params = {
        "img_url": img_url,
        "question_info": question_info,
        "question_params": question_params,
        "request_id": "mazon1",
    }

    pdb.set_trace()
    inference_main(inference_params)
