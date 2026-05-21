import cv2
import json
import pdb
import glob
import os, sys

#json_folder = '_2025年2月_baiduyun_json/'
#updated_json_folder = "_2025年2月_baiduyun_json1/"
json_folder = 'huawei_images_baiduyun_json/'
updated_json_folder = "huawei_images_baiduyun_json1/"
if not os.path.exists(updated_json_folder):
    os.mkdir(updated_json_folder)

imgs_folder = '_2025年2月/'
def read_json(fn):
    with open(fn, "rb") as f:
        data = json.load(f)
    return data

def write_json(data, fn):
    with open(fn, 'w') as f:
        f.write(data)
    return

def read_str_json(fn):
    with open(fn, "rb") as f:
        content = f.read()
    data = json.loads(content)
    return data
    
#fns = glob.glob(json_folder+"*.json")

fns = ['mathres.json']
for fn in fns:
    bn = os.path.basename(fn)
    #new_jsonp = os.path.join(updated_json_folder, bn)
    new_jsonp = "mathres1.json"
    #imgp = os.path.join(imgs_folder, bn.replace(".json", ".txt"))
    content = read_json(fn)
    #pdb.set_trace()
    _data = json.dumps(content, ensure_ascii=False)
    write_json(_data, new_jsonp)



    

