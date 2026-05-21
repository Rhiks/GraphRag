import concurrent.futures
import base64
import requests
import pdb
import pandas as pd
import ast
import json
import numpy as np
import time

def make_request(json_data):
    url = "http://0.0.0.0:5400/blanks_recog"
    #url = "http://0.0.0.0:5301/blanks_recog"
    #url = "http://0.0.0.0:5100/"
    #url = "https://cv.aixuexi.com/llm_recog/blanks_recog"
    response = requests.post(url, json=json_data)
    return response.status_code, response.text


    

if __name__ == "__main__":
    #from es_utils.topic_util import query_topic

    ##excel = "/data/weima1/daily_check/面授_plus_的答题数据_2025_11_18_addes.xlsx"
    #excel = "/data/weima1/daily_check/面授_测试筛选_addes1.xlsx"
    ##df = pd.read_excel(excel, sheet_name='11-17')
    #df = pd.read_excel(excel, sheet_name='Sheet1')
    #df = df.head(50)
    ##pdb.set_trace()
    ##results = []
    ##
    ##for i in range(len(df)):
    #for i in range(len(df)):
    #    #stem = query_topic(df['topic_id'][i])
    #    image_url = df['answer_content'][i]
    #    topic_id = df['topic_id'][i]
    #    topic_type = df['state'][i]
    #    try:
    #        es_answers = ast.literal_eval(df['es_answers'][i][2:-3])
    #        
    #        topic_data = query_topic(topic_id)
    #        if "question" in topic_data:
    #            stem = topic_data["question"]
    #        else:
    #            stem = ""
    #        question_params = {"student_user_id":i,
    #          "topic_id": topic_id, 
    #          "question_id": 11,
    #          "topic_type": topic_type}
    #         
    #
    #        question_info = {"stem":stem, "es_answers":es_answers}
    #        inference_params = {"img_url":image_url,
    #        "question_info":question_info,
    #        "question_params":question_params}
    #        
    #        #pdb.set_trace()
    #         
    #        t0 = time.time()
    #        json_data_fixed = json.loads(json.dumps(inference_params, default=lambda x: int(x) if isinstance(x, np.integer) else float(x) if isinstance(x, np.floating) else str(x)))
    #        json_data_fixed['img_url']=json_data_fixed['img_url'][2:-2]
    #        code, text = make_request(json_data_fixed)
    #        
    #        #pdb.set_trace()
    #        if code == 200:
    #            is_process = json.loads(text)['recog_results'].get("is_with_process",-1)
    #            stu_answers = json.loads(text)['recog_results'].get("stu_answers",[])
    #            raw_result = json.loads(text)['recog_results'].get("raw_result", 'error')

    #        else: 
    #            is_process = -1
    #            stu_answers = []
    #            raw_result = 'error'
    #        t1 = time.time()
    #        tt = np.round(t1-t0, 4)
    #        print (f"time cost{tt}s")
    #        df.at[i, 'time_cost'] = tt
    #        df.at[i, 'stu_answers'] = str(stu_answers)
    #        df.at[i, 'with_process'] = is_process
    #        df.at[i, 'raw_result'] = raw_result
    #    except Exception as e:
    #        print (f"{image_url} error")
    #        print (f"error {e}")
    #        df.at[i, 'time_cost'] = -1
    #        df.at[i, 'stu_answers'] = 'error'
    #        df.at[i, 'raw_result'] = raw_result
    #    #pass
 
    ##excel_out = excel.replace(".xlsx","_withporcess_gemini-2.5-flash-preview0.xlsx")  
    ##excel_out = excel.replace(".xlsx","_withporcess_gemini0.xlsx")  
    #excel_out = excel.replace(".xlsx","_withporcess_qwen-ocr.xlsx")  
    #df.to_excel(excel_out, index=False)
 
    question_params = {"student_user_id":11,
      "topic_id": 6887617, 
      "question_id": 11,
      "topic_type": 2}
    #
    #topic_data = query_topic(question_params['topic_id'])
    #if "question" in topic_data:
    #    stem = topic_data["question"]
    #else:
    #    stem = ""
    #stem = '判断下列说法是否正确\(∶\)'
    stem = '（1）某台电脑以5000元购进，按照15%的利润率定价，这台电脑的售价是&nbsp;元；（2）一束玫瑰花按照80%的利润率定价，利润为40元，这束玫瑰花的进价是&nbsp;元，售价是&nbsp;元；（3）一台冰箱，如果按照25%的利润率定价，定价为1500元，那么这台冰箱的成本是&nbsp;元．'
    stem = '下列图形中阴影部分的面积是\(\mathrm{c}\mathrm{m}^2\)．（π取3.14）'
    #stem = "数一数，图中共有&nbsp;个三角形．&nbsp;"
    #es_answers = ['$\\left(-3,4\\right)$']
    #es_answers =['（1）A （2）相等；虚 （3）物体通过平面镜所成像的大小与物体到平面镜的距离有关吗'] 
    #es_answers = ['（1）×；（2）×；（3）×；（4）×．']
    es_answers = ['5750', '50', '90', '1200']
    es_answers = ['314']
    question_info = {"stem":stem, "es_answers":es_answers}
   
    #inference_params = {"img_url":"http://aixuexi-sjyy.oss-cn-beijing.aliyuncs.com/tt_oss/blanks_imgs/10286436_4506420.jpg",
    #img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1763547452247_0_8149124.1763547452229.jpg"
    #img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1763882679282_117_9800979.1763882679259.jpg"
    #img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1764235520142_21_11231704.1764235520129.jpg"
    #img_url = 'https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1763981339355_0_7274503.1763981339347.jpg'
    img_url = 'https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1763980288538_1_4332815.1763980288532.jpg'
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1770121853057_135_8670463.1770121853046.jpg"
    inference_params = {"img_url":img_url,
    "question_info":question_info,
    "question_params":question_params}
    pdb.set_trace()
    code, text = make_request(inference_params)
    #main()
    print("finished")
     
    
