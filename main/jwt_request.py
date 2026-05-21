import requests

BASE_URL = "http://127.0.0.1:5300"

# 1. 获取 QWT token
token_resp = requests.post(
    f"{BASE_URL}/auth/qwt/token",
    json={"username": "gaosi_qwt_user", "password": "REPLACE_ME"},
    timeout=5,
)
token_resp.raise_for_status()
token = token_resp.json()["token"]

# 2. 携带 token 调用 blanks_recog
headers = {"X-QWT-Token": token}
payload = {
    "img_url": "http://aixuexi-sjyy.oss-cn-beijing.aliyuncs.com/tt_oss/blanks_imgs/9147879_2930172.jpg",
    "question_params": {
        "student_user_id": 21,
        "topic_id": 2930172,
        "question_id": 21,
        "topic_type": 2,
    },
    "question_info": {
        "es_answers": [],
        "stem": "题干示例",
    },
}
from es_utils.topic_util import query_topic
topic_data = query_topic(payload["question_params"]['topic_id'])
if "question" in topic_data:
    stem = topic_data["question"]
else:
    stem = ""

question_info = {"stem":stem, "es_answers":["720"]}
payload['question_info']=question_info

resp = requests.post(
    f"{BASE_URL}/blanks_recog",
    json=payload,
    headers=headers,
    timeout=30,
)
print(resp.status_code, resp.json())



