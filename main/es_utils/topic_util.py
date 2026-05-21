from elasticsearch import Elasticsearch

es = Elasticsearch(
    ['http://es-cn-st21o9qmv00059vfx.public.elasticsearch.aliyuncs.com:9200'],  # 生产环境
    http_auth=('elastic', 'n6JV5apTWIFpDL9-'),  # 替换为你的用户名和密码
    headers={"Content-Type": "application/json"}
)

def query_topic(topic_id):
    if not topic_id:
        return None
    
    # 在Elasticsearch中查询对应的详情
    es_query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"questionId": topic_id}},
                    {"term": {"lasted": 0}}
                ]
            }
        },
        "size": 1
    }

    es_result = es.search(index='tiku_question_20200612', body=es_query, 
                        headers={"Content-Type": "application/json"})  # 替换为你的索引名称
    # print(es_result)
    if es_result['hits']['hits']:
        es_data = es_result['hits']['hits'][0]['_source']
        return extract_question_data(es_data) 


def extract_question_data(response):
    tag_name = response.get("tag",{}).get("name","").strip()
    """结构化提取题目数据"""
    if (tag_name=="填空题" or tag_name=="解答题" or tag_name=="实验题"
        or tag_name=="简答题" or tag_name =="实验探究题" or tag_name=="计算题"):
        return {
            "question": response.get("tiGan", {}).get("text", "").strip(),
            # "answer_options": [ 
            #     {
            #         "text": ans.get("text", ""),
            #         "html": ans.get("html", "")
            #     } for ans in response.get("answers", [])
            # ],
            # "analysis": "\n".join(
            #     jx.get("text", "") for jx in response.get("jieXis", [])
            # ),
            # "difficulty":response.get("difficultys")[0]["value"]
        }
    elif (tag_name=="选择题" or tag_name=="单选题" or tag_name=="多选题"):
        # 提取题干和选项
        tiGan = response.get("tiGan", {})
        question_text = tiGan.get("text", "").strip()
        options = response.get("options", [])
        
        # 构建选项文本（带字母编号）
        option_items = [
            f"{chr(65+i)}. {opt.get('text', '')}" 
            for i, opt in enumerate(options)
        ]
        full_question = f"{question_text}\n" + "\n".join(option_items)
        return {
            "question": full_question,  # 包含题干+选项的纯文本
            "answer_options": [ 
                {
                    "text": ans.get("text", ""),
                    "html": ans.get("html", "")
                } for ans in response.get("answers", [])
            ],
            "analysis": "\n".join(
                jx.get("text", "") for jx in response.get("jieXis", [])
            ),
            "difficulty":response.get("difficultys")[0]["value"]
        }
    elif (tag_name=="综合题"):
        main_question = response.get("tiGan", {}).get("text", "").strip()
        child_questions = []
        all_answers = []
        all_analysis = []

        # 遍历子题
        for idx, child in enumerate(response.get("childs", []), 1):
            # 提取子题题干
            child_text = child.get("tiGan", {}).get("text", "").strip()
            if child_text:
                child_questions.append(f"({idx}) {child_text}")
            
            # 提取子题答案
            child_answers = []
            for ans in child.get("answers", []):
                answer_text = ans.get("text", "").strip()
                if answer_text:
                    child_answers.append({
                        "text": f"子题{idx}答案：{answer_text}",
                        "html": ans.get("html", "")
                    })
            all_answers.extend(child_answers)
            
            # 提取子题解析
            child_analysis = "\n".join(
                f"子题{idx}解析：{jx.get('text', '')}" 
                for jx in child.get("jieXis", [])
            )
            if child_analysis:
                all_analysis.append(child_analysis)

        # 合并主题干和子题题干
        full_question = f"{main_question}\n" + "\n".join(child_questions)
        
        # 合并父级解析（如果有）
        parent_analysis = "\n".join(jx.get("text", "") for jx in response.get("jieXis", []))
        if parent_analysis:
            all_analysis.insert(0, f"总体解析：{parent_analysis}")

        return {
            "question": full_question,
            "answer_options": all_answers,
            "analysis": "\n\n".join(all_analysis)
            # ,"difficulty": response.get("difficultys")[0]["value"] 去掉星级，因为物理的星级是瞎打的
        }

def query_topics_by_model_id(model_id):
    if not model_id:
        return None
    
    # 在Elasticsearch中查询对应的详情
    es_query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"models.primaryModelIds": model_id}}
                ]
            }
        },
        "size": 10  # 你可以调整这个值来获取更多结果
    }

    es_result = es.search(index='tiku_question_20200612', body=es_query, 
                        headers={"Content-Type": "application/json"})  # 替换为你的索引名称
    topics = []
    if es_result['hits']['hits']:
        for hit in es_result['hits']['hits']:
            es_data = hit['_source']
            topics.append(es_data)

    
    return topics

response = query_topic('4506420')
print(response)
# queston_data= extract_question_data(response)
# print(queston_data)
