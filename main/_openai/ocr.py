import pandas as pd
import os
import time
from datetime import datetime
from open_ai import completions, create_image_message  # 导入您的模块
from topic_util import query_topic

def process_fill_blank_questions(input_file: str, output_file: str):
    """
    处理填空题图片识别任务
    """
    # 读取Excel文件
    df = pd.read_excel(input_file)
    # 添加新列
    df['识别结果'] = ''
    df['请求时间'] = ''
    df['识别状态'] = ''
    df['处理时长(秒)'] = ''  # 添加处理时长列
    
    # 使用OCR模型
    model = 'doubao-seed-1-6-flash'
    total_count = len(df)
    correct_count = 0
    
    print(f"开始处理 {total_count} 个填空题...")
    
    for index, row in df.iterrows():
        # 记录开始时间
        start_time = time.time()
        
        try:
            print(f"处理第 {index + 1}/{total_count} 个题目...")
            
            # 获取图片路径和相关信息
            topic_id = row['topic_id']
            image_path = row['question_url']
            correct_answer = str(row['answer']).strip()
            
            # 检查图片文件是否存在
            if not os.path.exists(image_path):
                df.at[index, '识别结果'] = '图片文件不存在'
                df.at[index, '识别状态'] = '错误'
                df.at[index, '请求时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # 计算处理时长
                end_time = time.time()
                processing_time = round(end_time - start_time, 2)
                df.at[index, '处理时长(秒)'] = processing_time
                continue
            
            # 获取题目题干
            topic_data = query_topic(topic_id)
            
            # 处理题目数据 - 提取题目内容
            if isinstance(topic_data, dict):
                # 如果返回的是字典，尝试提取题目内容
                if 'question' in topic_data:
                    topic_tigan = topic_data['question']
                elif 'content' in topic_data:
                    topic_tigan = topic_data['content']
                else:
                    # 如果没有预期的键，转换整个字典为字符串
                    topic_tigan = str(topic_data)
            else:
                # 如果不是字典，直接转换为字符串
                topic_tigan = str(topic_data)
            
            # 清理HTML标签（如果存在）
            import re
            topic_tigan = re.sub(r'<[^>]+>', '', topic_tigan)  # 移除HTML标签
            topic_tigan = topic_tigan.replace('&nbsp;', '____')   # 替换HTML空格
            topic_tigan = topic_tigan.strip()
            
            print(f"题目内容: {topic_tigan}")
            
            # 创建识别消息
            prompt_text = """任务：识别指定题目的手写答案
输入：
题干：具体题目内容
图片：包含1道或多道题的学生手写答案
要求：
精确匹配：仅识别与给定题干对应的那道题的答案
定位填空：找到该题的空白处（横线上/下方）的手写数字
忽略干扰：
- 忽略题干中的已知数字
- 忽略图片中其他题目的答案
- 忽略计算草稿或无关数字
输出格式：
单空：直接输出数字（如：20）
多空：按顺序用逗号分隔（如：19,3,6）
无法识别：输出?
示例：
题干：孙悟空吃了____个包子，猪八戒吃了____个
图片显示答案：12，8
输出：12,8
请根据题干内容，在图片中找到对应题目并识别其手写答案。
题目信息：""" + topic_tigan

            messages = [
                create_image_message(
                    text=prompt_text,
                    images=[image_path]
                )
            ]
            
            # 记录请求时间
            request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 记录API请求开始时间
            api_start_time = time.time()
            
            # 调用大模型进行识别
            response = completions(messages, model=model)
            
            # 记录API请求结束时间
            api_end_time = time.time()
            
            # 提取响应内容
            if isinstance(response, dict) and 'choices' in response:
                raw_result = response['choices'][0]['message']['content']
            else:
                raw_result = str(response)
            
            print(f"原始识别结果: {raw_result}")
            print(f"API请求耗时: {round(api_end_time - api_start_time, 2)} 秒")
            
            # 处理识别结果
            recognized_answer = clean_recognition_result(raw_result)
            
            # 记录结果
            df.at[index, '识别结果'] = recognized_answer
            df.at[index, '请求时间'] = request_time
            
            # 比较答案
            if compare_answers(recognized_answer, correct_answer):
                df.at[index, '识别状态'] = '正确'
                correct_count += 1
            else:
                df.at[index, '识别状态'] = '错误'
            
            print(f"题目 {index + 1}: 正确答案={correct_answer}, 识别结果={recognized_answer}, 状态={df.at[index, '识别状态']}")
            
            # 添加延时避免请求过快
            time.sleep(1)
            
        except Exception as e:
            print(f"处理第 {index + 1} 个题目时出错: {str(e)}")
            # 打印更详细的错误信息用于调试
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            
            df.at[index, '识别结果'] = f'处理错误: {str(e)}'
            df.at[index, '识别状态'] = '错误'
            df.at[index, '请求时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        finally:
            # 无论成功还是失败，都记录处理时长
            end_time = time.time()
            processing_time = round(end_time - start_time, 2)
            df.at[index, '处理时长(秒)'] = processing_time
            print(f"第 {index + 1} 个题目处理时长: {processing_time} 秒")
    
    # 计算识别正确率
    accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0
    
    # 保存结果
    save_results(df, output_file, total_count, correct_count, accuracy)
    
    return accuracy

def clean_recognition_result(raw_result: str) -> str:
    """
    清理和处理识别结果
    """
    import re
    
    # 如果返回无法识别标识
    if '?' in raw_result or '无法识别' in raw_result:
        return '?'
    
    # 提取所有数字
    numbers = re.findall(r'\d+', raw_result)
    
    if not numbers:
        return '?'
    elif len(numbers) == 1:
        # 单空题
        return numbers[0]
    else:
        # 多空题，用逗号连接
        return ','.join(numbers)

def compare_answers(recognized: str, correct: str) -> bool:
    """
    比较识别结果和正确答案
    """
    # 标准化格式：去除空格，统一使用逗号分隔
    recognized_clean = recognized.replace(' ', '').replace('，', ',')
    correct_clean = correct.replace(' ', '').replace('，', ',')
    
    return recognized_clean == correct_clean

def save_results(df: pd.DataFrame, output_file: str, total_count: int, correct_count: int, accuracy: float):
    """
    保存结果到Excel文件
    """
    try:
        # 计算处理时长统计
        processing_times = df['处理时长(秒)'].apply(lambda x: float(x) if str(x).replace('.', '').isdigit() else 0)
        avg_processing_time = processing_times.mean()
        total_processing_time = processing_times.sum()
        
        # 创建ExcelWriter对象
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # 保存主要数据
            df.to_excel(writer, sheet_name='识别结果', index=False)
            
            # 创建统计数据
            stats_df = pd.DataFrame({
                '统计项': [
                    '总题目数', 
                    '识别正确数', 
                    '识别错误数', 
                    '识别正确率(%)', 
                    '总处理时长(秒)', 
                    '平均处理时长(秒)'
                ],
                '数值': [
                    total_count, 
                    correct_count, 
                    total_count - correct_count, 
                    f"{accuracy:.2f}",
                    f"{total_processing_time:.2f}",
                    f"{avg_processing_time:.2f}"
                ]
            })
            
            # 保存统计数据
            stats_df.to_excel(writer, sheet_name='统计结果', index=False)
        
        print(f"结果已保存到: {output_file}")
        print(f"总处理时长: {total_processing_time:.2f} 秒")
        print(f"平均处理时长: {avg_processing_time:.2f} 秒")
        
    except Exception as e:
        print(f"保存文件时出错: {str(e)}")
        # 尝试保存基础版本
        try:
            df.to_excel(output_file.replace('.xlsx', '_basic.xlsx'), index=False)
            print(f"基础结果已保存到: {output_file.replace('.xlsx', '_basic.xlsx')}")
        except Exception as e2:
            print(f"保存基础文件也失败: {str(e2)}")

def print_final_statistics(total_count: int, correct_count: int, accuracy: float, output_file: str):
    """
    输出最终统计结果
    """
    print(f"\n=== 识别完成 ===")
    print(f"总题目数: {total_count}")
    print(f"识别正确数: {correct_count}")
    print(f"识别错误数: {total_count - correct_count}")
    print(f"识别正确率: {accuracy:.2f}%")
    print(f"结果已保存到: {output_file}")

# 使用示例
if __name__ == "__main__":
    input_file = "填空题样本-2-答案.xlsx"
    output_file = "填空题样本-2-答案-识别-doubao_flash.xlsx"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 {input_file} 不存在")
        exit(1)
    
    try:
        # 执行识别任务
        accuracy = process_fill_blank_questions(input_file, output_file)
        print(f"\n最终识别正确率: {accuracy:.2f}%")
    except KeyboardInterrupt:
        print("\n用户中断了程序执行")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")