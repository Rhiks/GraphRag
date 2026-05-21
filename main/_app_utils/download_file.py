import csv
import os
import requests
from urllib.parse import urlparse
from pathlib import Path
import pdb

def download_from_url(image_url, save_path):
    try:
        print(f"Downloading {image_url} to {save_path}")
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(save_path, 'wb') as img_file:
                for chunk in response.iter_content(1024):
                    img_file.write(chunk)
            print(f"Saved {save_path} successfully.")
            
        else:
            print(f"Failed to download {image_url}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading {image_url}: {e}")
    return

def remove_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"已删除文件: {file_path}")
    else:
        print("文件不存在")
    return  

if __name__=="__main__":
    #pdb.set_trace()
    url = "http://aixuexi-sjyy.oss-cn-beijing.aliyuncs.com/pdf_test/d1a.pdf"
    save_path = "/data/ocr_dataset/paper_cut_es/test_dataset_calculate/d1a_1.pdf"
    download_from_url(url, save_path)
   
     

    
