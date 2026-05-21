#!/bin/bash
apt update && apt install -y libgl1-mesa-glx libglib2.0-0

cd /usr/opt/main 

pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

ENV_FILE="${ENV_FILE:-.env.local}"
# 定义服务端口（默认 5300 --port 或 -p 覆盖）
PORT=5300
DIR=/usr/opt/main

if [ ! -d "/usr/opt/logs" ]; then
    mkdir -p /usr/opt/logs
    echo "Directory /usr/opt/logs created."
fi
APP_LOG_FILE=/usr/opt/logs/`date +'%Y-%m-%d_%H-%M-%S'`.log


# 解析命令行参数
while [ $# -gt 0 ]; do
  case "$1" in
    --port|-p)
      if [[ -n "$2" && "$2" != -* ]]; then
        PORT="$2"
        shift 2
      else
        echo "错误: --port 需要一个端口号参数" >&2
        exit 1
      fi
      ;;
    *)
      echo "未知参数: $1" >&2
      echo "用法: $0 [--port|-p <port>]" >&2
      exit 1
      ;;
  esac
done

# 查找占用端口的进程 PID
pids=$(lsof -ti :$PORT 2>/dev/null)

if [ -n "$pids" ]; then
    echo "发现占用端口 $PORT 的进程，PIDs: $pids"
    echo "正在杀死这些进程..."

    # 逐个杀掉所有占用端口的进程
    for pid in $pids; do
        kill -9 $pid 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "成功杀死进程 PID: $pid"
        else
            echo "无法杀死进程 PID: $pid" >&2
        fi
    done

    echo "所有占用端口 $PORT 的进程已停止。"
else
    echo "未发现占用端口 $PORT 的进程。"
fi

echo "Cleaning log file..."
rm -f /usr/opt/logs/*.log
if [ $? -eq 0 ]; then
    echo "日志文件清理成功。"
else
    echo "日志文件清理失败。" >&2
    exit 1
fi

if [ -f "$DIR/.env" ]; then
    echo "使用已有环境配置: $DIR/.env"
else
    # 公开仓库默认只提供 .env.example，真实环境请通过镜像、挂载或部署系统注入。
    if [ -f "$DIR/$ENV_FILE" ]; then
        echo "复制环境配置文件 $ENV_FILE 到 ${DIR}/.env"
        cp "$DIR/$ENV_FILE" "$DIR/.env"
    elif [ -f "$DIR/.env.example" ]; then
        echo "未找到 $ENV_FILE，复制 .env.example 到 ${DIR}/.env；请填入真实私有配置后再部署。"
        cp "$DIR/.env.example" "$DIR/.env"
    else
        echo "错误: 找不到环境配置文件 $DIR/$ENV_FILE 或 $DIR/.env.example" >&2
        exit 1
    fi

    if [ $? -eq 0 ]; then
        echo "环境配置文件复制成功。"
    else
        echo "环境配置文件复制失败。" >&2
        exit 1
    fi
fi

export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6
echo "Starting FastAPI service..."
# Using gunicorn with uvicorn workers for FastAPI (ASGI)
nohup gunicorn app_llm:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT --timeout 0 > $APP_LOG_FILE 2>&1 &
if [ $? -eq 0 ]; then
    echo "FastAPI 服务启动成功。"
else
    echo "FastAPI 服务启动失败。" >&2
    exit 1
fi


# 保持进程存在，否则容器会退出
tail -f /dev/null
