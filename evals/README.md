# AI 判题实验评测工具

本工具用于评测判题服务的 AI 判题准确率。评测流程分为三个步骤：**下载数据集**、**推理**、**评估**。

## 1. 下载数据集

**数据集**
- 2025-fall (2025 秋季数据集): https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/ai-judge/objective-wide-table-sample-20260115.jsonl, 其中包含:
  - `all-sample`：1000 条（从所有样本中抽样）
  - `case-study-sample`：500+ 条（从 AI 判错的样本中抽样）
- 2026-winter (2026 寒假数据集): https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/ai-judge/wide-table-sample-winter26-1000.jsonl
  - 来源于 面授plus寒假0期课 的标注数据, 随机抽样 1000 条

**快速开始**：直接下载默认数据集
```bash
wget https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/ai-judge/wide-table-sample-winter26-1000.jsonl
```

**关键字段**：
- `gt.is_correct`：标准答案的判题结果（用于评估）
- `question_info.img_url`：题目图片 URL（用于调用判题接口）

## 2. 推理

### 配置 config.yaml

**⚠️ 首次使用**：需要从 `config_example.yaml` 复制配置文件：
```bash
cd evals
cp config_example.yaml config.yaml
```

然后编辑 `config.yaml`，设置服务地址和数据集路径：

```yaml
objective_judge:  # 客观题判题接口描述
  base_url: "http://127.0.0.1:5300"  # 修改为对应服务的 base_url
  endpoint: "/api/v1/judge/objective"
  timeout: 60

subjective_judge:  # 主观题判题接口描述
  base_url: "http://127.0.0.1:5300"  # 修改为对应服务的 base_url
  endpoint: "/api/v1/judge/streaming/subjective"
  timeout: 60

judge:
  base_url: "https://jzx.aixuexi.com/ai"
  endpoint: "/api/cms/judge"
  salt: "llm-router"
  timeout: 60

data:
  input_file: "/path/to/input_data.jsonl"
  output_file: "/path/to/result_data.jsonl"

settings:
  test_count: 1         # ⚠️ 测试模式：1=只处理1个样本，0=处理所有样本
```

### 运行推理

1. 启动服务

```bash
# 在测试机上启动 python 判题服务
cd main
ENV=local bash start.sh
```

**注意**: 需要分别启动一个 base(基准) 组服务, 和一个 exp(实验) 组服务.
- 启动前可以打开 start.sh 设置端口号, 两个服务如果部署在同一台机器上, 不可用同一个端口号


2. 开始推理

```bash
cd evals
# 首次运行或需要从头开始时，删除已有输出文件
python infer.py --config /path/to/custom_config.yaml
```

**功能说明**：
1. 读取数据集，调用判题接口获取判题结果
2. 将结果写入 `infer_results` 字段

**注意**: 做对比实验时, 应该同时启动两个推理任务, 分别对应 base 组和 exp 组

## 3. 评估

```bash
cd evals
python evals.py --input exp_name/infer_results_base.jsonl --output exp_name/eval_report_base.txt --failed-cases results/failed_cases_base.jsonl
python evals.py --input exp_name/infer_results_exp.jsonl --output exp_name/eval_report_exp.txt --failed-cases results/failed_cases_exp.jsonl
```

**功能说明**：
- 对比 `gt.is_correct`（标准答案）和 `infer_results.is_correct`（AI 判题结果）
- 计算整体准确率，并按数据源类型、题目类型、题目ID等维度统计
- **按题目ID统计**：按准确率从低到高排序，自动过滤掉准确率=100%的题目
- **失败 case 输出**：使用 `--failed-cases` 参数可导出所有失败 case 到 JSONL 文件，便于后续分析

**参数说明**：
- `--input`：输入的推理结果 JSONL 文件路径（必需）
- `--output`：输出的报告文件路径（可选，不指定则只输出到控制台）
- `--failed-cases`：输出的失败 case JSONL 文件路径（可选，不指定则不保存）

## 重要提示

1. **⚠️ test_count 配置**：默认值为 `1`（只处理1个样本），正式评测前必须设置为 `0`
2. **服务启动**：确保判题服务在推理前已正常启动
3. **结果保存**：推理结果会实时保存，中断不会丢失已处理的数据
