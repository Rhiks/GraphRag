# -*- coding: utf-8 -*-
"""
喜刷刷 OCR 接口路由
"""

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from _openai.xishuashua_ocr import recognize_xishuashua, recognize_xishuashua_async
from config.logger import logger


router = APIRouter()


@router.post("/xishuashua_ocr_recg")
async def xishuashua_ocr_recg(
    img_url: str = Body(..., description="图片URL"),
    question_stem: str = Body(..., description="原始题干内容"),
    system_prompt: str = Body(None, description="自定义系统提示词")
):
    """
    喜刷刷短文填空 OCR 识别接口
    
    - **img_url**: 学生作答图片的URL
    - **question_stem**: 原始题干文本，包含填空编号
    - **system_prompt**: 可选的自定义系统提示词
    """
    try:
        logger.info(f"Received xishuashua OCR request: img_url={img_url}, question_stem={question_stem[:100]}...")
        
        # 调用喜刷刷识别功能（异步）
        status, result = await recognize_xishuashua_async(
            img_url=img_url,
            question_stem=question_stem,
            system_prompt=system_prompt
        )
        
        # 构建响应
        response = {
            "status_code": 200,
            "message": status,
            "result": result
        }
        
        logger.info(f"Xishuashua OCR completed: {status}")
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        logger.error(f"Xishuashua OCR error: {str(e)}")
        response = {
            "status_code": 500,
            "message": f"识别失败: {str(e)}",
            "result": []
        }
        return JSONResponse(content=response, status_code=500)
