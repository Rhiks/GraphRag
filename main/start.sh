#!/bin/bash
# 指定分支指定目录


DIR="$(cd "$(dirname "$0")" && pwd)"
cd $DIR

# 定义服务端口（默认 5300，可通过 --port 或 -p 覆盖）
PORT=5300

# 解析命令行参数
while [[ $# -gt 0 ]]; do
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
rm -f /data/var/log/llm_ocr_app.log
if [ $? -eq 0 ]; then
    echo "日志文件清理成功。"
else
    echo "日志文件清理失败。" >&2
    exit 1
fi

if [ -f "$DIR/.env" ]; then
    echo "使用已有环境配置: $DIR/.env"
else
    # 根据 ENV 环境变量选择对应的 .env 文件；公开仓库默认只提供 .env.example。
    if [ "$ENV" = "local" ]; then
        ENV_FILE=".env.local"
        echo "使用本地环境配置: $ENV_FILE"
    else
        ENV_FILE=".env.production"
        echo "使用线上环境配置: $ENV_FILE"
    fi

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

export LD_PRELOAD=${CONDA_PREFIX}/lib/libstdc++.so.6
echo "Starting FastAPI service..."
# Using gunicorn with uvicorn workers for FastAPI (ASGI)
gunicorn app_llm:app -w 8 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT --timeout 0 > /data/var/log/llm_ocr_app.log
if [ $? -eq 0 ]; then
    echo "FastAPI 服务启动成功。"
else
    echo "FastAPI 服务启动失败。" >&2
    exit 1
fi
