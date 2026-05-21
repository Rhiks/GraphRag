# LLM Blanks Recognition Service

基于 FastAPI、OCR/CV 和大模型能力的填空题识别与判题服务。服务接收题目图片、题干、标准答案等信息，完成图片下载、传统视觉预处理、OCR/版面识别、LLM 答案抽取与结果整理，并通过 HTTP API 返回结构化识别结果。

> 注意：公开仓库中不包含真实 API Key、数据库密码、OSS 密钥或线上环境配置。请从示例配置复制后在本地或部署环境中填入自己的凭据。

## 功能概览

- 填空题图片识别：`POST /blanks_recog`
- 客观题判题：`POST /api/v1/judge/objective`
- 主观题流式判题：`POST /api/v1/judge/streaming/subjective`
- 健康检查：`GET /health`
- 传统 CV、OCR、大模型多阶段处理链路
- MySQL 结果记录、OSS 图片上传、日志轮转等工程化能力

## 项目结构

```text
.
├── dockerStart.sh                  # Docker/容器启动辅助脚本
├── evals/                          # 客观题判题评测脚本与示例配置
├── main/
│   ├── app_llm.py                  # FastAPI 应用入口
│   ├── inference_main1.py          # 填空题识别主流程
│   ├── router/                     # HTTP 路由
│   ├── service/                    # 判题、聊天等服务层
│   ├── _traCV/                     # 传统 CV / OCR 处理
│   ├── _openai/                    # LLM/OCR 调用封装
│   ├── db_utils/                   # MySQL / OSS 工具
│   ├── config/                     # 配置与日志
│   └── requirements.txt            # Python 依赖
└── README.md
```

## 环境要求

- Python 3.11+
- MySQL，按需启用
- 可访问的 OCR/LLM 服务
- 可选：阿里云 OSS，用于图片上传或中间结果保存

## 快速开始

1. 创建虚拟环境并安装依赖：

```bash
cd main
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 准备配置：

```bash
cp .env.example .env
```

然后编辑 `main/.env`，填入自己的 `CN_API_KEY`、`GLOBAL_API_KEY`、数据库和 OSS 配置。不要把真实 `.env` 提交到 Git。

3. 启动服务：

```bash
ENV=local bash start.sh
```

或手动启动：

```bash
cd main
gunicorn app_llm:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5300
```

4. 验证服务：

```bash
curl http://localhost:5300/health
```

预期返回类似：

```json
{"Msg":"success"}
```

## API 示例

### 填空题识别

```bash
curl -X POST http://localhost:5300/blanks_recog \
  -H "Content-Type: application/json" \
  -d '{
    "img_url": "https://example.com/image.jpg",
    "question_info": {
      "stem": "题干内容",
      "es_answers": ["标准答案1", "标准答案2"]
    },
    "question_params": {
      "student_user_id": "12345",
      "topic_id": "67890",
      "topic_type": "blank"
    }
  }'
```

### 客观题判题

```bash
curl -X POST http://localhost:5300/api/v1/judge/objective \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "demo-request",
    "img_url": "https://example.com/image.jpg",
    "question_info": {
      "stem": "题干内容",
      "es_answers": ["A"]
    },
    "question_params": {
      "student_user_id": "12345",
      "topic_id": "67890",
      "topic_type": "objective"
    }
  }'
```

## 配置说明

主要配置来自 `main/.env`：

- `ENV`：运行环境，常用 `local` / `production`
- `DEBUG`：是否启用调试模式
- `LOG_LEVEL`、`LOG_PATH`：日志级别和日志路径
- `CN_API_KEY`、`CN_BASE_URL`：国内模型服务配置
- `GLOBAL_API_KEY`、`GLOBAL_BASE_URL`：海外或备用模型服务配置
- `MYSQL_HOST`、`MYSQL_USER`、`MYSQL_PASSWORD`：数据库配置
- `ALIYUN_ACCESS_KEY_ID`、`ALIYUN_ACCESS_KEY_SECRET`：OSS 配置
- `IMG_URL_REPLACE`：是否把公网 OSS 图片地址替换为内网地址

`main/config/configure.ini` 也保留了历史模块需要的 INI 配置，但其中只应放占位符或本地开发值。生产凭据建议通过环境变量或部署系统注入。

## 评测

`evals/` 目录提供客观题评测脚本。典型流程：

```bash
cd evals
cp config_example.yaml config.yaml
python infer.py --config config.yaml
python evals.py --input results/test_infer_results.jsonl
```

说明：评测脚本主要覆盖 `/api/v1/judge/objective`，不能替代 `/blanks_recog` 的端到端接口验证。

## 安全说明

- 真实 `.env`、API Key、数据库密码、OSS 密钥、JWT、请求头输出和临时日志都不应提交。
- 本仓库中的密钥字段均为占位符，部署前需要由环境变量或私有配置系统提供。
- 如果曾经把真实密钥提交到任何公开仓库，应立即在对应平台轮换密钥。

## 常用命令

```bash
# 语法检查
python -m py_compile main/app_llm.py main/inference_main1.py main/router/judge.py

# 启动本地服务
cd main && ENV=local bash start.sh

# 健康检查
curl http://localhost:5300/health
```
