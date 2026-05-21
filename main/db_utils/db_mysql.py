#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 1 20:37:46 2024
@author: jc
"""
import os

import pymysql
import datetime
import pdb
import sys
#sys.path.append('/data2/weima/ocr_blanks_recog')
sys.path.append('/data/source/ocr_blanks_recog')
from config.test_log import info_logger
from config.test_log_ans import info_logger_ans
# 数据库连接参数
config = {
    "host": "MYSQL_HOST",
    "user": "ss_user",
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": "data_analysis"
}

if not os.environ.get('MY_ENV'):
 config = {
     "host": "MYSQL_HOST",
     "user": "test",
     "password": os.environ.get("MYSQL_PASSWORD", ""),
     "database": "data_analysis"
 }

def select(sql):
    # 连接到数据库
    db = pymysql.connect(**config)
    # 创建一个cursor对象
    cursor = db.cursor()
    cursor.execute(sql)
    data_list = cursor.fetchall()
    # 关闭数据库连接
    cursor.close()
    db.close()
    return data_list


def select_by_values(sql, values):
    # 连接到数据库
    db = pymysql.connect(**config)
    # 创建一个cursor对象
    cursor = db.cursor()
    cursor.execute(sql, values)    
    data_list = cursor.fetchall()
    # 关闭数据库连接
    cursor.close()
    # 提交事务
    db.commit()
    db.close()
    return data_list


def execute_values(sql, values):
    db = pymysql.connect(**config)
    cursor = db.cursor()
    batch_size = 100
    try:
        for i in range(0, len(values), batch_size):
            cursor.executemany(sql, values[i:i + batch_size])
            db.commit()
    except pymysql.MySQLError as ex:
        db.rollback()
    finally:
        cursor.close()
        db.close()



def execute(sql):
    # 连接到数据库
    db = pymysql.connect(**config)
    # 创建一个cursor对象
    cursor = db.cursor()
    cursor.execute(sql)
    db.commit()
    # 关闭数据库连接
    cursor.close()
    db.close()


# 参数化查询, 防止sql注入
def executemany(sql, values):
    db = pymysql.connect(**config)
    cursor = db.cursor()
    cursor.executemany(sql, values)
    db.commit()
    cursor.close()
    db.close()

def execute_single_insert(sql, values):
    connection = pymysql.connect(**config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
        connection.commit()
        #print(f"{sql}_{values}_数据插入成功！")
        info_logger.info(f'{sql}_{values}_数据插入成功！')
    except Exception as e:
        # 回滚事务
        connection.rollback()
        #print(f"{sql}_{values}_数据插入失败: {e}")
        info_logger.info(f'{sql}_{values}_数据插入失败: {e}！')
    finally:
        # 关闭数据库连接
        connection.close()

def execute_single_insert_ans(sql, values):
    connection = pymysql.connect(**config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
        connection.commit()
        info_logger_ans.info(f'{sql}_{values}_数据插入成功！')
    except Exception as e:
        # 回滚事务
        connection.rollback()
        info_logger_ans.info(f'{sql}_{values}_数据插入失败: {e}！')
    finally:
        # 关闭数据库连接
        connection.close()

def insert_ocr_res(params):

    if "ocr_result" not in params:
        sql = '''INSERT INTO ocr_blanks_record (student_user_id, question_id, topic_id, institution_id, lesson_id, child_index, request_id, image_url, content, request_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        execute_single_insert(sql, (params["student_user_id"], params["question_id"],params["topic_id"], params["institution_id"], params["lesson_id"], params["child_index"], params["request_id"], params["image_url"], params["content"], params["request_code"]))
    else:
        sql = '''INSERT INTO ocr_blanks_record (student_user_id, question_id, topic_id, institution_id, lesson_id, child_index, request_id, image_url, content, ocr_result, request_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        execute_single_insert(sql, (params["student_user_id"], params["question_id"],params["topic_id"], params["institution_id"], params["lesson_id"], params["child_index"], params["request_id"], params["image_url"], params["content"], params["ocr_result"], params["request_code"]))

def insert_or_update_ocr_res(params, mode="ocr", table="ocr_blanks_record"):
    # 基本字段，去除 image_url

    if mode=="oss":
        fields = ["request_id", "image_url"]
    elif mode=='ocr' and table=="ocr_blanks_record":
        base_fields = ["request_id", "student_user_id", "question_id", "topic_id", "institution_id", "lesson_id", "child_index", "content", "request_code", "request_type"]
        # 检查是否包含 "ocr_result"
        if "ocr_result" in params:
            fields = base_fields + ["ocr_result"]
        else:
            fields = base_fields
    
    elif mode=='ocr' and table=="formula_recog_record":
        base_fields = ["request_id", "request_code"]
        # 检查是否包含 "ocr_result"
        if "ocr_result" in params:
            fields = base_fields + ["ocr_result"]
        else:
            fields = base_fields
    
    # 检查 request_id 是否存在
    request_id = params.get("request_id")
    
    # SQL 查询检查 request_id 是否已经存在
    #check_sql = "SELECT * FROM ocr_blanks_record WHERE request_id = %s"
    check_sql = f"SELECT * FROM {table} WHERE request_id = %s"
    intable = select_by_values(check_sql, (request_id,))
    #pdb.set_trace()
    
    # 如果已经存在，进行更新操作
    if len(intable)== 1:
        # 更新操作
        #set_clause = ", ".join([f"{field} = %s" for field in fields[1:]])  # 排除 request_id
        set_clause = ", ".join([f"{field} = %s" for field in fields[1:]])  # 排除 request_id
        #print("set_cluase: ", set_clause)
        #update_sql = f'''UPDATE ocr_blanks_record SET {set_clause} WHERE request_id = %s'''
        update_sql = f'''UPDATE {table} SET {set_clause} WHERE request_id = %s'''
        values = tuple(params[field] for field in fields[1:]) + (request_id,)
        execute_single_insert(update_sql, values)
        return True
    elif len(intable)== 0:
        # 插入操作
        values = tuple(params[field] for field in fields)
        placeholders = ", ".join(["%s"] * len(fields))
        #insert_sql = f'''INSERT INTO ocr_blanks_record ({", ".join(fields)}) VALUES ({placeholders})'''
        #insert_sql = f'''
        #    INSERT INTO ocr_blanks_record ({", ".join(fields)}) 
        #    VALUES ({placeholders})
        #    ON DUPLICATE KEY UPDATE {', '.join([f'{field} = VALUES({field})' for field in fields])}
        #    ''' 
        insert_sql = f'''
            INSERT INTO {table} ({", ".join(fields)}) 
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {', '.join([f'{field} = VALUES({field})' for field in fields])}
            ''' 
        execute_single_insert(insert_sql, values)
        return True
    else:
        return False


def select_imgurl(tid):
    img_url = ''
    check_sql = "SELECT image_url FROM ocr_blanks_record WHERE request_id = %s"
    res = select_by_values(check_sql, (tid))
    return res
    
     

def milliseconds_to_time(ms):
    seconds = ms / 1000
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:06.3f}"

def millis2abs(dt_str, millis):
    dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    new_dt = dt + datetime.timedelta(milliseconds=millis)
    return new_dt

def query_ans_img_url(question_id):

    
    sql = '''select answer_handwriting from image_handwriting_pad WHERE question_id = %s;'''
    
    query_res = select_by_values(sql,(question_id))
    if(len(query_res) > 0 and len(query_res[0]) > 0):
        query_res = query_res[0][0]
    return query_res

def insert_or_update_ocr_res_ans(params, mode="ocr", table="ocr_jieda_rs"):
    # 基本字段，去除 image_url

    if mode=="oss":
        fields = ["request_id", "image_url"]
    elif mode=='ocr'and table=="ocr_jieda_rs":
        base_fields = ["request_id", "student_user_id", "question_id", "topic_id", "request_code"]
        # 检查是否包含 "ocr_result"
        if "ocr_result" in params:
            fields = base_fields + ["ocr_result"]
        else:
            fields = base_fields
    # 检查 request_id 是否存在
    request_id = params.get("request_id")
    
    # SQL 查询检查 request_id 是否已经存在
    check_sql = f"SELECT * FROM {table} WHERE request_id = %s"
    intable = select_by_values(check_sql, (request_id,))
    #pdb.set_trace()
    # 如果已经存在，进行更新操作
    if len(intable)== 1:
        # 更新操作
        set_clause = ", ".join([f"{field} = %s" for field in fields[1:]])  # 排除 request_id
        update_sql = f'''UPDATE {table} SET {set_clause} WHERE request_id = %s'''
        values = tuple(params[field] for field in fields[1:]) + (request_id,)
        execute_single_insert_ans(update_sql, values)
        return True
    elif len(intable)== 0:
        # 插入操作
        values = tuple(params[field] for field in fields)
        placeholders = ", ".join(["%s"] * len(fields))
        #insert_sql = f'''INSERT INTO ocr_blanks_record ({", ".join(fields)}) VALUES ({placeholders})'''
        #insert_sql = f'''
        #    INSERT INTO ocr_blanks_record ({", ".join(fields)}) 
        #    VALUES ({placeholders})
        #    ON DUPLICATE KEY UPDATE {', '.join([f'{field} = VALUES({field})' for field in fields])}
        #    ''' 
        insert_sql = f'''
            INSERT INTO {table} ({", ".join(fields)}) 
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {', '.join([f'{field} = VALUES({field})' for field in fields])}
            ''' 
        execute_single_insert_ans(insert_sql, values)
        return True
    else:
        return False

def insert_or_update_handwriting_and_question_url(params, table="image_handwriting_pad"):
    # 基本字段，去除 image_url

    fields = ["user_id", "topic_id", "question_id", "answer_handwriting", "question"]
    # 检查是否存在
    question_id = params.get("question_id")
    topic_id = params.get("topic_id")
    user_id = params.get("user_id")
    
    # SQL 查询检查 request_id 是否已经存在
    check_sql = f"SELECT * FROM {table} WHERE question_id = %s AND topic_id = %s AND user_id = %s"
    intable = select_by_values(check_sql, (question_id, topic_id, user_id))
    #pdb.set_trace()
    # 如果已经存在，进行更新操作
    if len(intable)== 1:
        # 更新操作
        set_clause = ", ".join([f"{field} = %s" for field in fields[1:]])
        update_sql = f'''UPDATE {table} SET {set_clause} WHERE question_id = %s AND topic_id = %s AND user_id = %s'''
        values = tuple(params[field] for field in fields[1:]) + (question_id, topic_id, user_id)
        execute_single_insert_ans(update_sql, values)
        return True
    elif len(intable)== 0:
        # 插入操作
        values = tuple(params[field] for field in fields)
        placeholders = ", ".join(["%s"] * len(fields))
        #insert_sql = f'''INSERT INTO ocr_blanks_record ({", ".join(fields)}) VALUES ({placeholders})'''
        #insert_sql = f'''
        #    INSERT INTO ocr_blanks_record ({", ".join(fields)}) 
        #    VALUES ({placeholders})
        #    ON DUPLICATE KEY UPDATE {', '.join([f'{field} = VALUES({field})' for field in fields])}
        #    ''' 
        insert_sql = f'''
            INSERT INTO {table} ({", ".join(fields)}) 
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {', '.join([f'{field} = VALUES({field})' for field in fields])}
            ''' 
        execute_single_insert_ans(insert_sql, values)
        return True
    else:
        return False

if __name__ == '__main__':
    #user_id = 111
    #room_id = 111
    #img_set = {"img_begin": 380, "img_end": 983, "img_set": "1,2,3,4,5"}
    #insert_imgs_oss(user_id, room_id, img_set)
    #pdb.set_trace()
    #upsert_stu_video0(user_id, room_id, task_status=4, start_time='2025-02-01 00:00:77', online=7, host_ip="192.168.9.0")
    #delete_from_alaysis_task('192.168.1.101')
    #upsert_stu_video_offline(user_id, room_id, host_ip='292.168.111.111:5000')

    #insert_params = {"student_user_id":1,  "question_id":1, "top_id":1,  "institution_id":1, "lesson_id":1, \
    #        "child_index":0, "request_id":1, "image_url":"0.jpg", "content":"1", "request_code":444}
    #insert_params = {"student_user_id":345,  "question_id":1, "topic_id":1,  "institution_id":1, "lesson_id":1, \
    #        "child_index":0, "request_id":1, "image_url":"0.jpg", "content":">3", "ocr_result":"test1", "request_code":200}
    #insert_ocr_res(insert_params)
    #insert_params = {"student_user_id":345,  "question_id":1, "topic_id":1,  "institution_id":1, "lesson_id":1, \
    #        "child_index":0, "request_id":"2025_3_14_8f78c602-826d-4eb3-a7be-735e2fcaa0f2", "content":">3", "ocr_result":"test1", "request_code":900}
    #insert_params = {"student_user_id":345,  "question_id":1, "topic_id":1,  "institution_id":1, "lesson_id":1, \
    #        "child_index":0, "request_id":"duibuqi", "content":">3", "ocr_result":"test1", "request_code":900}
    insert_params = {"user_id": "111", "topic_id": "222", "question_id": "333", "answer_handwriting": "444", "question":"555"}
    insert_or_update_handwriting_and_question_url(insert_params)
    #res = select_imgurl("090")
    # pdb.set_trace()
    # print ("res is: ", res)

    
