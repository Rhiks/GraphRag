import requests
import json
import glob
import cv2
import pdb
import base64
import numpy as np

def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()

class CommonOcr(object):
    def __init__(self, img_path=None, is_url=False):
        # 自动擦除手写文字
        self._url = 'https://api.textin.com/ai/service/v1/handwritten_erase'
        # 请登录后前往 “工作台-账号设置-开发者信息” 查看 x-ti-app-id
        # 示例代码中 x-ti-app-id 非真实数据
        self._app_id = 'bda63d908f8c95aef5a8f7a9e6b8c0ac'
        self._secret_code = 'SECRET_CODE_REPLACE_ME'
        # 请登录后前往 “工作台-账号设置-开发者信息” 查看 x-ti-secret-code
        # 示例代码中 x-ti-secret-code 非真实数据
        self._img_path = img_path
        self._is_url = is_url

    def recognize(self):
        head = {}
        try:
            head['x-ti-app-id'] = self._app_id
            head['x-ti-secret-code'] = self._secret_code
            if self._is_url:
                head['Content-Type'] = 'text/plain'
                body = self._img_path
            else:
                image = get_file_content(self._img_path)
                head['Content-Type'] = 'application/octet-stream'
                body = image
            result = requests.post(self._url, data=body, headers=head)
            return result.text
        except Exception as e:
            return e
    def recognize_and_save(self, img_path):
        head = {}
        try:
            head['x-ti-app-id'] = self._app_id
            head['x-ti-secret-code'] = self._secret_code
            if self._is_url:
                head['Content-Type'] = 'text/plain'
                body = self._img_path
            else:
                self._img_path = img_path
                bn = os.path.basename(fn)
                save_bn = os.path.join(save_folder, bn)
                image = get_file_content(self._img_path)
                head['Content-Type'] = 'application/octet-stream'
                body = image
            result = requests.post(self._url, data=body, headers=head)
            return result
        except Exception as e:
            return e

def base64_to_cv2_bgr(base64_string):
    """
    将Base64编码的图片数据转换为OpenCV BGR格式的numpy数组
    
    参数:
        base64_string: Base64编码的图片字符串
        
    返回:
        cv2_bgr_array: OpenCV BGR格式的numpy数组
    """
    try:
        # 1. 解码Base64字符串为字节数据
        img_data = base64.b64decode(base64_string)
        
        # 2. 将字节数据转换为numpy数组
        nparr = np.frombuffer(img_data, np.uint8)
        
        # 3. 使用cv2.imdecode解码图像数据
        # flags=1 表示以BGR格式加载彩色图像
        cv2_bgr_array = cv2.imdecode(nparr, flags=cv2.IMREAD_COLOR)
        
        if cv2_bgr_array is None:
            raise ValueError("无法解码图像数据，请检查Base64字符串是否有效")
            
        return cv2_bgr_array
        
    except Exception as e:
        print(f"转换过程中发生错误: {str(e)}")
        return None

if __name__ == "__main__":
    ## 示例 1：传输文件
    #response = CommonOcr(img_path=r'example.jpg')
    #print(response.recognize())
    ## 示例 2：传输 URL
    #response = CommonOcr(img_path='http://example.com/example.jpg', is_url=True)
    #print(response.recognize())

    save_folder = "pagetype0_erase_jpgs"
    import os, sys
    if not os.path.exists(save_folder):
        os.mkdir(save_folder)
    CommonOcr = CommonOcr()
    #image_folder = "/data/ocr_dataset/shijuan_analysis/math/"
    #mage_folder = "./catalogdetails1_getimagepage_jpg_imgsdraw/"
    image_folder = "/data/ocr_dataset/page_parse/pagetype0"
    #fns=glob.glob(image_folder+"*_refine.jpg")
    fns=glob.glob(image_folder+"/*.jpg")
    for fn in fns:
        bn = os.path.basename(fn)
        save_bn = os.path.join(save_folder, bn)
        response = CommonOcr.recognize_and_save(fn)
        data = response.json()
        string = data['result']["image"]
        #pdb.set_trace() 
        im = base64_to_cv2_bgr(string)
        cv2.imwrite(save_bn, im)
        print(f"{save_bn} saved!")
