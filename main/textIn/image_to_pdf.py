import requests
import json
from fpdf import FPDF
import pdb
import sys, os
import glob

def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()

class CommonOcr(object):
    def __init__(self, img_path=None, is_url=False):
        # 图片转PDF
        self._url = 'https://api.textin.com/ai/service/v1/file-convert/image-to-pdf'
        # 请登录后前往 “工作台-账号设置-开发者信息” 查看 x-ti-app-id
        # 示例代码中 x-ti-app-id 非真实数据
        self._app_id = 'bda63d908f8c95aef5a8f7a9e6b8c0ac'
        # 请登录后前往 “工作台-账号设置-开发者信息” 查看 x-ti-secret-code
        # 示例代码中 x-ti-secret-code 非真实数据
        self._secret_code = 'SECRET_CODE_REPLACE_ME'
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

    def recognize_and_save(self, base_name):
        save_path = os.path.join(base_name, ".pdf")
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
                    # 保存为PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font("NotoSans", style="", fname="NotoSansSC-Regular.ttf", uni=True)  # 使用支持中文的字体
            pdf.set_font("NotoSans", size=12)
            pdf.multi_cell(0, 10, result.text.encode('latin-1', errors='replace').decode('latin-1'))  # 临时
            #pdf.set_font("Arial", size=12)
            #pdf.multi_cell(0, 10, result.text)  # 将文本写入PDF
            pdf.output(save_path)  # 保存文件
            return result.text
        except Exception as e:
            return e

if __name__ == "__main__":
    # 示例 1：传输文件
    #response = CommonOcr(img_path=r'example.jpg')
    #print(response.recognize())
    # 示例 2：传输 URL
    #response = CommonOcr(img_path='http://example.com/example.jpg', is_url=True)
    #print(response.recognize())
    image_folder = "/data/ocr_dataset/page_parse/math/"
    fns=glob.glob(image_folder+"*.jpg")
    for fn in fns:
        bn = os.path.basename(fn).rstrip(".jpg")
        response = CommonOcr(img_path=fn)
        print(response.recognize_and_save(bn))
     
    

     
    


