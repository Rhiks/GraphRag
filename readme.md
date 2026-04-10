<div align="center">
  <a href="https://github.com/gusye1234/nano-graphrag">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://assets.memodb.io/nano-graphrag-dark.png">
      <img alt="Shows the MemoDB logo" src="https://assets.memodb.io/nano-graphrag.png" width="512">
    </picture>
  </a>
  <p><strong>A simple, easy-to-hack GraphRAG implementation</strong></p>
  <p>
    <img src="https://img.shields.io/badge/python->=3.9.11-blue">
    <a href="https://pypi.org/project/nano-graphrag/">
      <img src="https://img.shields.io/pypi/v/nano-graphrag.svg">
    </a>
    <a href="https://codecov.io/github/gusye1234/nano-graphrag" > 
     <img src="https://codecov.io/github/gusye1234/nano-graphrag/graph/badge.svg?token=YFPMj9uQo7"/> 
 		</a>
    <a href="https://pepy.tech/project/nano-graphrag">
      <img src="https://static.pepy.tech/badge/nano-graphrag/month">
    </a>
  </p>
  <p>
  	<a href="https://discord.gg/sqCVzAhUY6">
      <img src="https://dcbadge.limes.pink/api/server/sqCVzAhUY6?style=flat">
    </a>
    <a href="https://github.com/gusye1234/nano-graphrag/issues/8">
       <img src="https://img.shields.io/badge/群聊-wechat-green">
    </a>
  </p>
</div>









😭 [GraphRAG](https://arxiv.org/pdf/2404.16130) is good and powerful, but the official [implementation](https://github.com/microsoft/graphrag/tree/main) is difficult/painful to **read or hack**.

😊 This project provides a **smaller, faster, cleaner GraphRAG**, while remaining the core functionality(see [benchmark](#benchmark) and [issues](#Issues) ).

🎁 Excluding `tests` and prompts,  `nano-graphrag` is about **1100 lines of code**.

👌 Small yet [**portable**](#Components)(faiss, neo4j, ollama...), [**asynchronous**](#Async) and fully typed.



> If you're looking for a multi-user RAG solution for long-term user memory, have a look at this project: [memobase](https://github.com/memodb-io/memobase) :)

## Install

**Install from source** (recommend)

```shell
# clone this repo first
cd nano-graphrag
pip install -e .
```

**Install from PyPi**

```shell
pip install nano-graphrag
```



## Quick Start

> [!TIP]
>
> **Please set OpenAI API key in environment: `export OPENAI_API_KEY="sk-..."`.** 

> [!TIP]
> If you're using Azure OpenAI API, refer to the [.env.example](./.env.example.azure) to set your azure openai. Then pass `GraphRAG(...,using_azure_openai=True,...)` to enable.

> [!TIP]
> If you're using Amazon Bedrock API, please ensure your credentials are properly set through commands like `aws configure`. Then enable it by configuring like this: `GraphRAG(...,using_amazon_bedrock=True, best_model_id="us.anthropic.claude-3-sonnet-20240229-v1:0", cheap_model_id="us.anthropic.claude-3-haiku-20240307-v1:0",...)`. Refer to an [example script](./examples/using_amazon_bedrock.py).

> [!TIP]
>
> If you don't have any key, check out this [example](./examples/no_openai_key_at_all.py) that using `transformers` and `ollama` . If you like to use another LLM or Embedding Model, check [Advances](#Advances).

download a copy of A Christmas Carol by Charles Dickens:

```shell
curl https://raw.githubusercontent.com/gusye1234/nano-graphrag/main/tests/mock_data.txt > ./book.txt
```

Use the below python snippet:

```python
from nano_graphrag import GraphRAG, QueryParam

graph_func = GraphRAG(working_dir="./dickens")

with open("./book.txt") as f:
    graph_func.insert(f.read())

# Perform global graphrag search
print(graph_func.query("What are the top themes in this story?"))

# Perform local graphrag search (I think is better and more scalable one)
print(graph_func.query("What are the top themes in this story?", param=QueryParam(mode="local")))
```

Next time you initialize a `GraphRAG` from the same `working_dir`, it will reload all the contexts automatically.

#### Batch Insert

```python
graph_func.insert(["TEXT1", "TEXT2",...])
```

<details>
<summary> Incremental Insert</summary>

`nano-graphrag` supports incremental insert, no duplicated computation or data will be added:

```python
with open("./book.txt") as f:
    book = f.read()
    half_len = len(book) // 2
    graph_func.insert(book[:half_len])
    graph_func.insert(book[half_len:])
```

> `nano-graphrag` use md5-hash of the content as the key, so there is no duplicated chunk.
>
> However, each time you insert, the communities of graph will be re-computed and the community reports will be re-generated

</details>

<details>
<summary> Naive RAG</summary>

`nano-graphrag` supports naive RAG insert and query as well:

```python
graph_func = GraphRAG(working_dir="./dickens", enable_naive_rag=True)
...
# Query
print(rag.query(
      "What are the top themes in this story?",
      param=QueryParam(mode="naive")
)
```
</details>


### Async

For each method `NAME(...)` , there is a corresponding async method `aNAME(...)`

```python
await graph_func.ainsert(...)
await graph_func.aquery(...)
...
```

### Available Parameters

`GraphRAG` and `QueryParam` are `dataclass` in Python. Use `help(GraphRAG)` and `help(QueryParam)` to see all available parameters!  Or check out the [Advances](#Advances) section to see some options.



