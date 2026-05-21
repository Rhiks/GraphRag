import os, sys
import cv2

def textIn_judge(textin_result, answers):
    with_process = True
    if not textin_result['success']:
        return with_process
    result = textin_result.get('result')
    raw_ocr = result['pages'][0]['raw_ocr']
    raw_ocr_hd = []
    for e in raw_ocr:
        if e.get("handwritten", -1) == 1:
            text = e.get('text',"")
            if text not in answers:
                raw_ocr_hd.append(e)
    if len(raw_ocr_hd)>=2:
        with_process = True
    else:
        with_process = False
    return with_process
    
  
