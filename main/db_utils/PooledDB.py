from dbutils.pooled_db import PooledDB
import mysql.connector
import os

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
# 创建数据库连接池
pool = PooledDB(
    creator=mysql.connector,         # 使用 mysql.connector 作为连接库
    maxconnections=5,                # 连接池最大连接数
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

# 从连接池取出连接
conn = pool.connection()
cursor = conn.cursor()

import pdb
pdb.set_trace()
# 执行查询
cursor.execute("SELECT * FROM ocr_blanks_record LIMIT 100")
result = cursor.fetchall()
print(result)
# 回收连接（而不是关闭物理连接）
cursor.close()
conn.close()
table = "ocr_blanks_record"
check_sql = f"SELECT * FROM {table} WHERE request_id = %s"
request_id = "2025_10_27_6855f1f7-9372-4a25-9d94-0bc950cfb529"

conn = pool.connection()
cursor = conn.cursor()
cursor.execute(check_sql, (request_id,))    
intable = cursor.fetchall()

print(intable)

# 回收连接（而不是关闭物理连接）
cursor.close()
conn.close()
 
