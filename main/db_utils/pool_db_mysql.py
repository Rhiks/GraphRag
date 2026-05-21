#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 1 20:37:46 2024
@author: jc
"""
import os

from dbutils.pooled_db import PooledDB
from config import Config
import mysql.connector
import os
import datetime
import pdb
import sys
from config.logger import logger
# 数据库连接参数
config = {
    "host": "MYSQL_HOST",
    "database": "data_analysis",
    "user": "ss_user",
    "password": "REPLACE_ME",
}

if Config.DEBUG:
    config = {
        "host": Config.get("MYSQL_HOST"),
        "database": "data_analysis",
        "user": Config.get("MYSQL_USER"),
        "password": Config.get("MYSQL_PASSWORD"),
    }
 #创建数据库连接池
pool = PooledDB(
    creator=mysql.connector,         # 使用 mysql.connector 作为连接库
    maxconnections=30,                # 连接池最大连接数
    mincached=2,                     # 初始化时创建的连接数量
    maxcached=3,                     # 最大缓存连接数
    blocking=True,                   # 连接数达到最大时是否阻塞等待
    #host='localhost',
    host = config['host'],
    port=3306,
    #user='your_user',
    user = config['user'],
    #password='your_password',
    password = config['password'],
    database=config['database'],
    charset='utf8mb4'
)

def select(sql):
    try:
        # 从连接池取出连接
        conn = pool.connection()
        cursor = conn.cursor()
        
        # 执行查询
        cursor.execute(sql)
        result = cursor.fetchall()
        
        # 回收连接（而不是关闭物理连接）
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        return


 
def select_by_values(sql, values):
    try:
        # 从连接池取出连接
        conn = pool.connection()
        cursor = conn.cursor()
        
        # 执行查询
        cursor.execute(sql, values)
        result = cursor.fetchall()
        
        # 回收连接（而不是关闭物理连接）
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        return


def execute_values(sql, values):
    try:
        # 从连接池取出连接
        conn = pool.connection()
        cursor = conn.cursor()
        
        batch_size = 100
        for i in range(0, len(values), batch_size):
            cursor.executemany(sql, values[i:i + batch_size])
            conn.commit()
        
        # 回收连接（而不是关闭物理连接）
        cursor.close()
        conn.close()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()



def execute(sql):
    try:
        # 从连接池取出连接
        conn = pool.connection()
        cursor = conn.cursor()
        
        # 执行SQL
        cursor.execute(sql)
        conn.commit()
        
        # 回收连接（而不是关闭物理连接）
        cursor.close()
        conn.close()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()


# 参数化查询, 防止sql注入
def executemany(sql, values):
    try:
        # 从连接池取出连接
        conn = pool.connection()
        cursor = conn.cursor()
        
        # 执行批量SQL
        cursor.executemany(sql, values)
        conn.commit()
        
        # 回收连接（而不是关闭物理连接）
        cursor.close()
        conn.close()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()

def execute_single_insert(sql, values):
    try:
        # 从连接池取出连接
        conn = pool.connection()
        cursor = conn.cursor()
        
        # 执行SQL
        cursor.execute(sql, values)
        conn.commit()
        #logger.info(f'{sql}_{values}_数据插入成功！')
        
        # 回收连接（而不是关闭物理连接）
        cursor.close()
        conn.close()
    except Exception as e:
        # 回滚事务
        conn.rollback()
        #logger.info(f'{sql}_{values}_数据插入失败: {e}！')
        cursor.close()
        conn.close()

def insert_or_update_ocr_res(params, mode="ocr", table="msplus_blanks_record", primary_key='request_id'):
    # 基本字段，去除 image_url

    
    question_params_keys = ["student_user_id", "topic_id", "question_id", "topic_type", "page_source", "conversation_id"]
    question_info_keys = ["es_answers","stem"]
    if mode == "ocr":
        #base_fields = question_info_keys + question_params_keys + ["image_url","request_id", "request_code", "stu_answers","raw_result", "raw_result_ocr", "with_process"]
        base_fields = question_info_keys + question_params_keys + ["image_url","request_id", "request_code", "stu_answers","raw_result", "raw_result_ocr", "main_prompt", "ocr_prompt", "with_process","choose_cv"]
   
    else:
        base_fields = question_params_keys + question_info_keys + ["image_url","request_id"]
 
    fields = base_fields
    if ("choose_cv" not in params) and ("choose_cv" in fields):
        fields.pop(fields.index("choose_cv"))
    
    if ("conversation_id" not in params) and ("conversation_id" in fields):
        fields.pop(fields.index("conversation_id"))
        
    if ("main_prompt" not in params) and ("main_prompt" in fields):
        fields.pop(fields.index("main_prompt"))
    if ("ocr_prompt" not in params) and ("ocr_prompt" in fields):
        fields.pop(fields.index("ocr_prompt"))

    if ("with_process" not in params) and ("with_process" in fields):
        fields.pop(fields.index("with_process"))
     
    if ("stu_answers" not in params) and ("stu_answers" in fields):
        fields.pop(fields.index("stu_answers"))
    else:
        params['stu_answers'] = str(params.get("stu_answers",""))
    if ('raw_result_ocr' not in params) and ('raw_result_ocr' in fields):
        fields.pop(fields.index('raw_result_ocr'))
    params["es_answers"] = str(params.get('es_answers',""))
    
    # 插入操作
    try:
        update_fields = [field for field in fields if field != primary_key]   
        values = tuple(params[field] for field in fields)
        placeholders = ", ".join(["%s"] * len(fields))
        update_clause = ", ".join([f'{field} = VALUES({field})' for field in update_fields])

        insert_sql = f'''INSERT INTO {table} ({", ".join(fields)}) 
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
            ''' 
        execute_single_insert(insert_sql, values)
        return True
    except Exception as e:
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


if __name__ == '__main__':
    insert_params = {"user_id": "111", "topic_id": "222", "question_id": "333", "answer_handwriting": "444", "question":"555"}
    insert_or_update_handwriting_and_question_url(insert_params)
    # print ("res is: ", res)

    
