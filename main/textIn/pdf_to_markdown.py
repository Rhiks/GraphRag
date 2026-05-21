import requests
import json
import pdb
import sys, os
import glob

import base64

def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()

class TextinOcr(object):
    def __init__(self, app_id, app_secret):
        self._app_id = app_id
        self._app_secret = app_secret
        self.host = 'https://api.textin.com'

    def recognize_pdf2md(self, image_path, options, is_url=False):
        """
        pdf to markdown
        :param options: request params
        :param image_path: string
        :param is_url: bool
        :return: response
        options = {
             'pdf_pwd': None,
             'dpi': 144,  # 设置dpi为144
             'page_start': 0,
             'page_count': 1000,  # 设置解析的页数为1000页
             'apply_document_tree': 0,
             'markdown_details': 1,
             'page_details': 0,  # 不包含页面细节信息
             'table_flavor': 'md',
             'get_image': 'none',
             'parse_mode': 'scan',  # 解析模式设为scan
         }

        """
        url = self.host + '/ai/service/v1/pdf_to_markdown'
        headers = {
            'x-ti-app-id': self._app_id,
            'x-ti-secret-code': self._app_secret
        }
        if is_url:
            image = image_path
            headers['Content-Type'] = 'text/plain'
        else:
            image = get_file_content(image_path)
            headers['Content-Type'] = 'application/octet-stream'
        #try:
        #    
        #    response = requests.post(url, data=image, headers=headers, params=options, timeout=5)
        #    return response, 200
        #except Exception as e:
        #    return str(e), 403
        # timeout=(连接超时, 读取超时)，确保5秒内必须完成
        return requests.post(url, data=image, headers=headers, params=options, timeout=(3, 5))
    
    def recognize_pdf2md_base64(self, image_data, options):
        url = self.host + '/ai/service/v1/pdf_to_markdown'
        headers = {
            'x-ti-app-id': self._app_id,
            'x-ti-secret-code': self._app_secret
        }
        image = base64.b64decode(image_data.encode("utf-8"))
           
        headers['Content-Type'] = 'application/octet-stream'

        return requests.post(url, data=image, headers=headers, params=options)

def save_to_json(data, filename="output.json", indent=4, ensure_ascii=False):
    #pdb.set_trace()
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
    return 


def inferecne_textin(pdf_url, options=None, is_url=True):
    # 设置转换选项
    options2 = dict(
        apply_document_tree=1,
        apply_merge=1,
        catalog_details=1,
        dpi=144,
        formula_level=0,
        get_excel=0,
        get_image='page',
        markdown_details=1,
        page_count=1000,
        page_details=1,
        char_details=1,
        paratext_mode="annotation",
        parse_mode="scan",
        raw_ocr=1,
        image_output_type='base64str',
        crop_dewarp=0,
        
    )
    try:
        textIn_response = textin.recognize_pdf2md(pdf_url, options2, is_url=True)
        if textIn_response.status_code!=200:
            return output, 403 
    except Exception as e:
        return output, 403 
        
        #logger.info(f"调用TextIn API进行PDF识别: {request_id}")
    try:
        response_data = textIn_response.json()
        if "result" not in response_data:
            #logger.error(f"TextIn API响应中缺少result字段, request_id: {request_id}")
            return output, 403
        result = textIn_response.json()["result"]
        #tiresp = os.path.join(textInres_folder, f"{params['request_id']}.json")

        #with open(tiresp, "w") as f:
        #    json.dump(result, f)
    
    except Exception as e:
        #logger.error(f"解析TextIn API响应失败: {str(e)}, request_id: {request_id}")
        return output, 403

if __name__ == "__main__":
    # 请登录后前往 “工作台-账号设置-开发者信息” 查看 app-id/app-secret
    #_app_id = 'bda63d908f8c95aef5a8f7a9e6b8c0ac'
    #_secret_code = 'SECRET_CODE_REPLACE_ME'
    _app_id = 'bda63d908f8c95aef5a8f7a9e6b8c0ac'
    _secret_code = 'SECRET_CODE_REPLACE_ME'
    textin = TextinOcr(_app_id, _secret_code)
    default_options = {
            'pdf_pwd': None,
            'dpi': 144,  # 设置dpi为144
            'page_start': 0,
            'page_count': 1000,  # 设置解析的页数为1000页
            'apply_document_tree': 0,
            'markdown_details': 1,
            'page_details': 0,  # 不包含页面细节信息
            'table_flavor': 'md',
            'get_image': 'none',
            'parse_mode': 'scan',  # 解析模式设为scan
        }
    custom_options = {
            'pdf_pwd': None,
            'char_details':1,
            #'dpi': 144,  # 设置dpi为144
            'page_start': 0,
            'page_count': 1000,  # 设置解析的页数为1000页
            'apply_document_tree': 1,
            'markdown_details': 1,
            'page_details': 1,  # 不包含页面细节信息
            'catalog_details': 1,  # 不包含页面细节信息
            'table_flavor': 'md',
            'get_image': 'page',
            'image_output_type': 'base64str',
            'parse_mode': 'scan',  # 解析模式设为scan
            'crop_dewarp': 1,  # 解析模式设为scan
            #'apply_chart': 1,  # 解析模式设为scan
            #'recognize_question':"non_llm",
            #'subject':"math",
            #'recognize_question':'non_llm_1',
            #'subject':'JHighSchool_Math',
        }

    
    # 设置转换选项
    options1 = dict(
        apply_document_tree=1,
        apply_merge=1,
        catalog_details=1,
        dpi=144,
        formula_level=0,
        get_excel=0,
        get_image='page',
        markdown_details=1,
        page_count=1000,
        page_details=1,
        char_details=1,
        paratext_mode="annotation",
        parse_mode="scan",
        raw_ocr=1,
        image_output_type='base64str',
        recognize_question="non_llm_1",
        subject="JHighSchool_Math",
        table_flavor="html",
        crop_dewarp=1,
        
    )

    #json_res = "catalogdetails1_getimagepage_jpg"
    #json_res = "pagetype1_addquestionparam"
    json_res = "pagetype0_erase_jpgs_json"
    if not os.path.exists(json_res):
        os.mkdir(json_res)
    #image_folder = "/data/ocr_dataset/page_parse/pagetype0_1"
    image_folder = "./pagetype0_erase_jpgs"
    #image_folder = "/data/ocr_dataset/page_parse/math"
    #fns=glob.glob(image_folder+"*.pdf")
    fns=glob.glob(image_folder+"/*.jpg")
    
    #pdb.set_trace()
    for fn in fns:
        #bn = os.path.basename(fn).rstrip(".pdf")

        bn = os.path.basename(fn).rstrip(".jpg")
        #if bn != "math1":
        #    continue
        save_json = os.path.join(json_res, bn+".json")
        resp = textin.recognize_pdf2md(fn, 
            #custom_options
            options1
        )
        data = resp.json()
        save_to_json(data, filename=save_json, indent=4, ensure_ascii=False)
        print("request time: ", resp.elapsed.total_seconds())
        
           
       
    # 示例 1：传输文件
    #image = 'file/example.pdf'
    #resp = textin.recognize_pdf2md(image, {
    #    'page_start': 0,
    #    'page_count': 1000,  # 设置解析页数为1000页
    #    'table_flavor': 'md',
    #    'parse_mode': 'scan',  # 设置解析模式为scan模式
    #    'page_details': 0,  # 不包含页面细节
    #    'markdown_details': 1,
    #    'apply_document_tree': 1,
    #    'dpi': 144  # 分辨率设置为144 dpi
    #})
    #print("request time: ", resp.elapsed.total_seconds())

    #result = json.loads(resp.text)
    #with open('result_1.json', 'w', encoding='utf-8') as fw:
    #    json.dump(result, fw, indent=4, ensure_ascii=False)

    # 示例 2：传输 URL
    #image = 'https://example.com/example.pdf'
    #resp = textin.recognize_pdf2md(image, {
    #    'page_start': 0,
    #    'page_count': 1000,  # 设置解析页数为1000页
    #    'table_flavor': 'md',
    #    'parse_mode': 'scan',  # 设置解析模式为scan模式
    #    'page_details': 0,  # 不包含页面细节
    #    'markdown_details': 1,
    #    'apply_document_tree': 1,
    #    'dpi': 144  # 分辨率设置为144 dpi
    #}, True)
     #print("request time: ", resp.elapsed.total_seconds())

    #result = json.loads(resp.text)
    #with open('result_2.json', 'w', encoding='utf-8') as fw:
    #    json.dump(result, fw, indent=4, ensure_ascii=False)

