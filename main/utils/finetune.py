import json
import cv2
import pdb
import re
import time
from sklearn.cluster import DBSCAN
import numpy as np
import os, sys
import glob


input_json = 'huawei_images_baiduyun_json1/158992_8791240_9954344.json'
output_json = input_json.replace('.json','_ft.json')


def convert_latex_formulas(content):
    """
    将 LaTeX 公式环境替换为行内公式格式 $...$
    支持的公式环境:
        \[...\], equation, equation*, displaymath
    """
    # 替换 \[...\] 环境 (行间公式)
    content = re.sub(r'\\\[\s*(.*?)\s*\\\]', r'$\1$', content, flags=re.DOTALL)
    
    # 替换 \begin{equation}...\end{equation} 环境（带编号和不带编号）
    content = re.sub(
        r'\\begin{(equation\*?)}[\s\S]*?(?=\\end{\1})([\s\S]*?)\\end{\1}',
        lambda m: f'${m.group(2).strip()}$',  # 提取内容并包裹 $
        content
    )
    
    # 替换 displaymath 环境
    content = re.sub(
        r'\\begin{displaymath}(.*?)\\end{displaymath}',
        r'$\1$', 
        content, 
        flags=re.DOTALL
    )
    
    # 清理公式内部多余的空格和换行（可选）
    content = re.sub(r'\$\s+', '$', content)
    content = re.sub(r'\s+\$', '$', content)
    
    return content

def is_latex_formula(s):
    """
    判断字符串是否为完整的 LaTeX 公式
    :param s: 输入字符串
    :return: True（是公式） / False（不是公式）
    """
    # 预处理：去除首尾空白
    s = s.strip()
    
    # 匹配行内公式：$...$（排除转义字符 \$）
    inline_pattern = r'^\$(?!\$)(?:[^$\\]|\\.)*\$$'
    if re.fullmatch(inline_pattern, s, flags=re.DOTALL):
        return True
    
    # 匹配行间公式：\[...\]（排除转义字符 \]）
    display_pattern = r'^\\\[(?:[^\]\\]|\\.)*\\\]$'
    if re.fullmatch(display_pattern, s, flags=re.DOTALL):
        return True
    
    # 匹配数学环境：\begin{env}...\end{env}（如 equation, align 等）
    math_env_pattern = r'''
        ^
        \\begin\{([a-z]+?)\}  # 匹配 \begin{env}
        .*?                   # 中间内容（非贪婪）
        \\end\{\1\}           # 匹配 \end{env}（必须同名）
        $
    '''
    math_envs = {'equation', 'align', 'gather', 'multline', 'eqnarray', 'displaymath'}
    match = re.fullmatch(math_env_pattern, s, flags=re.DOTALL | re.VERBOSE)
    if match and match.group(1) in math_envs:
        return True
    
    # 匹配简单公式（无包裹符号但包含 LaTeX 数学命令）
    if re.search(r'\\[a-zA-Z]+\{', s):  # 检测是否有 LaTeX 命令如 \frac{...}
        return True
    
    return False

def merge_boxes(boxes):
    x_min = min(box[0] for box in boxes)
    y_min = min(box[1] for box in boxes)
    x_max = max(box[2] for box in boxes)
    y_max = max(box[3] for box in boxes)
    return [x_min, y_min, x_max, y_max]



def is_inside(inner, outer):
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def intersection_area(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    return max(0, x2 - x1) * max(0, y2 - y1)

def filter_small_boxes(boxes):
    res_contours = [e for e in boxes if not ((e[2]-e[0])<=40 and (e[3]-e[1])<=40)]
    return res_contours

def filter_contained_boxes(merged_boxes):
    merged = []
    while merged_boxes:
        box = merged_boxes.pop(0)
        i = 0
        while i < len(merged_boxes):
            other = merged_boxes[i]
            small_area = (box[2] - box[0]) * (box[3] - box[1])
            inter_area = intersection_area(box, other)
            if is_inside(box, other) or is_inside(other, box) or (inter_area / (small_area * 0.7)) > 1:
                box = merge_boxes([box, other])
                merged_boxes.pop(i)
            else:
                i += 1
        merged.append(box)
    return merged

def cluster_and_merge(rectangles, eps=50, min_samples=1):
    y_centers = np.array([(box[1] + box[3]) / 2 for box in rectangles]).reshape(-1, 1)
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(y_centers)
    
    clusters = {}
    for i, label in enumerate(clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(rectangles[i])
    
    merged_boxes = [merge_boxes(boxes) for boxes in clusters.values()]
	
    #return merged_boxes
    return filter_contained_boxes(merged_boxes)

def merge_y_boxes(boxes, threshold=40):
    
    # 按 y1 排序，便于处理
    boxes.sort(key=lambda b: b[1])
    merged = []
    
    for box in boxes:
        x1, y1, x2, y2 = box
        
        if not merged:
            merged.append([x1, y1, x2, y2])
            continue
        
        last_x1, last_y1, last_x2, last_y2 = merged[-1]
        
        # 判断是否有足够的 y 方向重叠
        if y1 - last_y2 <= threshold:
            merged[-1] = [
                min(last_x1, x1),  # x1 取最小
                min(last_y1, y1),  # y1 取最小
                max(last_x2, x2),  # x2 取最大
                max(last_y2, y2)   # y2 取最大
            ]
        else:
            merged.append([x1, y1, x2, y2])
    
    return merged

def draw_rects(im, rects):
    for rect in rects:
    #pdb.set_trace() 
        cv2.rectangle(im, (rect[0], rect[1]), (rect[2], rect[3]), (255, 0, 0), 2)
    return im

	
def find_contour(image):
    hw_rects = []
    # 1. 预处理
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 2. 自适应阈值二值化
    thresh = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # 3. 形态学闭运算
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # 4. 查找轮廓
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 5. 筛选并绘制边界框
    #min_area = 100
    min_area = 30
    max_aspect_ratio = 25
    for cnt in contours:
        area = cv2.contourArea(cnt)
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
        if area > min_area and aspect_ratio < max_aspect_ratio:
            #cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            hw_rects.append([x,y,x+w, y+h])
    return hw_rects, image

def open_txt(fn):
    with open(fn, 'rb') as f:
        content = f.read()
    data = json.loads(content)
    return data

def grab_info_baidu(data):
    for key in data.keys():
        print (key)
    return 

def finetune_info(data):
    output = {}
    return output    

def contours_pipeline(im):
    t0 = time.time()
    contours, out_image = find_contour(im)
    if contours==[]:
        return contours, im
    t1 = time.time()
    #res_contours = [e for e in contours if not ((e[2]-e[0])<=2 and (e[3]-e[1])<=2)]
    res_contours = [e for e in contours if not ((e[2]-e[0])<=15 and (e[3]-e[1])<=15)]
    #res_contours = contours
    if res_contours==[]:
        return res_contours, im
    merged_boxes = cluster_and_merge(res_contours)
    merged = merge_y_boxes(merged_boxes) 
    t2 = time.time()
    #merged_im = draw_rects(im, merged)
    print (f"countour time cost: {t1-t0}s")
    print (f"merge boxes time cost: {t2-t1}s")
    #return merged, merged_im
    return merged, None
   
def contours_pipeline1(im):
    is_empty = False
    better2crop = False
    contours, out_image = find_contour(im)
    if contours==[]:
        return im, True, better2crop
    res_contours = [e for e in contours if not ((e[2]-e[0])<=15 and (e[3]-e[1])<=15)]
    if res_contours==[]:
        return im, True, better2crop
    
    merged_boxes = cluster_and_merge(res_contours)
    merged = merge_y_boxes(merged_boxes)
    h, w, _ = im.shape
    cropped_img = im
    if len(merged)==1:
        box = merged[0]
        if (box[2]-box[0])/w < 0.66 or (box[3]-box[1])/h < 0.6:
            cropped_img = im[max(0, box[1]-10):min(box[3]+10, h), max(box[0]-10, 0):min(box[2]+10, w), :]
            better2crop = True
    #else:
    #    cropped_img = im
    return cropped_img, is_empty, better2crop

def contours_pipeline2(im):
    is_empty = False
    contours, out_image = find_contour(im)
    if contours==[]:
        return im, True
    res_contours = [e for e in contours if not ((e[2]-e[0])<=15 and (e[3]-e[1])<=15)]
    if res_contours==[]:
        return im, True
    
    merged_boxes = cluster_and_merge(res_contours)
    merged = merge_y_boxes(merged_boxes)
    h, w, _ = im.shape
    cropped_img = im
    if len(merged)==1:
        box = merged[0]
        exp_h = int(.5*.1*h)
        exp_w = int(.5*.5*w)

        cropped_img = im[max(0, box[1]-exp_h):min(box[3]+exp_h, h), max(box[0]-exp_w, 0):min(box[2]+exp_w, w), :]
    return cropped_img, is_empty


def test_folder(imgs_folder, draw_folder):
    if not os.path.exists(draw_folder):
        os.mkdir(draw_folder)
    imgs = glob.glob(imgs_folder+"/*.jpg")
    for img in imgs:
        print('img: ', img)
        ##if img=='huawei_images/46619_8527722_10357789.jpg':
        ##    pdb.set_trace()
        bn = os.path.basename(img)
        #if not bn.startswith('238'):
        #    continue
        #pdb.set_trace()
        savep = os.path.join(draw_folder, os.path.basename(img))
        im = cv2.imread(img)
        merged, merged_im = contours_pipeline(im)
        cv2.imwrite(savep, merged_im)
    return

def rect2poly(rects):
    polys = []
    for rect in rects:
        poly = [[rect[0], rect[1]], 
                [rect[2], rect[1]],
                [rect[2], rect[3]],
                [rect[0], rect[3]]]
        polys.append(poly)
    return polys

#data = open_txt(input_json)
#pdb.set_trace()
#grab_info(data)
if __name__=="__main__":
    #fn = 'huawei_images/158992_8791240_9954344.jpg'
    #pdb.set_trace()
    #image = cv2.imread(fn)

    #cv2.imwrite("merged_image.jpg", merged_im)
    imgs_folder = '5750585_2025_03_26'
    save_folder = imgs_folder+'_drawres'
   
    test_folder(imgs_folder, save_folder)




