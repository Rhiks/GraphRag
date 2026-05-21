"""
示例：如何构建 JudgeRequest 并调用 SubjectiveJudgeService.judge()

这个文件展示了如何正确构建 student_info 和 question_info 并传入服务
"""

from model.subjective.judge import JudgeRequest
from model.student import StudentRequest
from model.question import QuestionRequest, TopicRequest, QuestionPart
from service.judge.subjective_judge_service import SubjectiveJudgeService


def example_1_basic_usage():
    """示例1：基础用法 - 构建完整的 JudgeRequest"""
    
    # 1. 构建 student_info
    student_info = StudentRequest(
        student_user_id=12345,           # 必填：学生用户ID
        student_name="张三",              # 可选：学生姓名
        phone="13800138000"              # 可选：电话号码
    )
    
    # 2. 构建 question_info
    # 2.1 先构建 TopicRequest（题目信息）
    topic_info = TopicRequest(
        topic_id=67890,                  # 必填：题目ID
        topic_type=4,                    # 必填：题目类型 (1:选择题,2:填空题,3:判断题,4:解答题,5:综合题)
        sub_index=0,                      # 可选：子题下标（综合题必传，0-based）
        subject_product_id=214,          # 可选：学科ID
        
        # 题干内容
        stem=QuestionPart(
            text="计算 2 + 3 等于多少？",  # 文本内容
            html="<p>计算 2 + 3 等于多少？</p>",  # HTML内容（可选）
            fragment_id="stem_001"        # 片段ID（可选）
        ),
        
        # 答案内容（列表）
        answers=[
            QuestionPart(
                text="5",
                html="<p>5</p>",
                fragment_id="answer_001"
            )
        ],
        
        # 解析内容（可选）
        jiexis=[
            QuestionPart(
                text="2 + 3 = 5",
                html="<p>2 + 3 = 5</p>"
            )
        ],
        
        # 选项（仅选择题需要）
        options=None  # 解答题不需要选项
    )
    
    # 2.2 构建 QuestionRequest
    question_info = QuestionRequest(
        topic_info=topic_info,           # 必填：题目信息
        question_id=11111,               # 可选：学生作答ID
        img_url="https://example.com/student_answer.jpg"  # 必填：学生作答图片URL
    )
    
    # 3. 构建完整的 JudgeRequest
    judge_request = JudgeRequest(
        student_info=student_info,        # 学生信息
        question_info=question_info,      # 题目信息
        conversation_id="conv_123456",    # 必填：会话ID
        page_source=0                     # 可选：页面来源，默认0
    )
    
    # 4. 调用服务（异步）
    # 注意：这是异步函数，需要在异步环境中调用
    # async def call_service():
    #     async for event in SubjectiveJudgeService.judge(judge_request):
    #         print(event)
    
    return judge_request


def example_2_minimal_usage():
    """示例2：最小化用法 - 只传必填字段"""
    
    # 最小化的 student_info（只传必填字段）
    student_info = StudentRequest(
        student_user_id=12345
    )
    
    # 最小化的 question_info
    question_info = QuestionRequest(
        topic_info=TopicRequest(
            topic_id=67890,
            topic_type=4,  # 解答题
        ),
        img_url="https://example.com/student_answer.jpg"
    )
    
    judge_request = JudgeRequest(
        student_info=student_info,
        question_info=question_info,
        conversation_id="conv_123456"
    )
    
    return judge_request


def example_3_comprehensive_question():
    """示例3：综合题（需要 sub_index）"""
    
    student_info = StudentRequest(
        student_user_id=12345,
        student_name="李四"
    )
    
    # 综合题需要指定 sub_index（第几小问，0-based）
    topic_info = TopicRequest(
        topic_id=67890,
        topic_type=5,                    # 5: 综合题
        sub_index=1,                     # 必填：第2小问（0-based，所以1表示第2问）
        subject_product_id=214,
        stem=QuestionPart(
            text="综合题：请回答以下问题...",
            html="<p>综合题：请回答以下问题...</p>"
        ),
        answers=[
            QuestionPart(text="第一问答案"),
            QuestionPart(text="第二问答案")
        ]
    )
    
    question_info = QuestionRequest(
        topic_info=topic_info,
        img_url="https://example.com/comprehensive_answer.jpg"
    )
    
    judge_request = JudgeRequest(
        student_info=student_info,
        question_info=question_info,
        conversation_id="conv_123456"
    )
    
    return judge_request


def example_4_from_dict():
    """示例4：从字典构建（常见于API请求）"""
    
    # 模拟从HTTP请求接收到的JSON数据
    request_data = {
        "student_info": {
            "student_user_id": 12345,
            "student_name": "王五",
            "phone": "13900139000"
        },
        "question_info": {
            "topic_info": {
                "topic_id": 67890,
                "topic_type": 4,
                "sub_index": None,
                "subject_product_id": 214,
                "stem": {
                    "text": "解方程 x + 5 = 10",
                    "html": "<p>解方程 x + 5 = 10</p>"
                },
                "answers": [
                    {
                        "text": "x = 5",
                        "html": "<p>x = 5</p>"
                    }
                ],
                "jiexis": [
                    {
                        "text": "移项得 x = 10 - 5 = 5"
                    }
                ],
                "options": None
            },
            "question_id": 11111,
            "img_url": "https://example.com/answer.jpg"
        },
        "conversation_id": "conv_123456",
        "page_source": 1
    }
    
    # 使用 Pydantic 自动解析
    judge_request = JudgeRequest(**request_data)
    
    return judge_request


def example_5_async_call():
    """示例5：如何异步调用服务"""
    import asyncio
    
    async def call_judge_service():
        # 构建请求
        judge_request = example_1_basic_usage()
        
        # 调用服务（返回异步迭代器）
        async for event in SubjectiveJudgeService.judge(judge_request):
            event_type = event.get("event")
            event_data = event.get("data")
            
            if event_type == "message":
                print(f"收到消息: {event_data}")
            elif event_type == "flush":
                print("第一阶段完成，等待选举结果...")
            elif event_type == "done":
                print("判题流程完成")
                break
    
    # 运行异步函数
    # asyncio.run(call_judge_service())


if __name__ == "__main__":
    # 测试构建
    print("=== 示例1：基础用法 ===")
    req1 = example_1_basic_usage()
    print(f"构建成功: student_id={req1.student_info.student_user_id}, "
          f"topic_id={req1.question_info.topic_info.topic_id}")
    
    print("\n=== 示例2：最小化用法 ===")
    req2 = example_2_minimal_usage()
    print(f"构建成功: student_id={req2.student_info.student_user_id}")
    
    print("\n=== 示例3：综合题 ===")
    req3 = example_3_comprehensive_question()
    print(f"构建成功: sub_index={req3.question_info.topic_info.sub_index}")
    
    print("\n=== 示例4：从字典构建 ===")
    req4 = example_4_from_dict()
    print(f"构建成功: conversation_id={req4.conversation_id}")
