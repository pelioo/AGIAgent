# 智能记忆管理系统 (Intelligent Memory Management System)

## 概述

这是 AGI Agent 的**长期记忆模块**，采用两层架构设计：

| 层级 | 名称 | 说明 | 实现位置 |
|------|------|------|----------|
| **第一层** | 短期记忆 | 当前任务上下文与工具调用历史 | `src/tool_executor.py` |
| **第二层** | 长期记忆 | 跨任务知识积累、智能检索 | `src/mem/` |

### 双层记忆架构

- **短期记忆**：存储当前任务的执行历史，通过 `task_history` 管理，包含工具调用记录、错误反馈等
- **长期记忆**：跨任务持久化存储，支持语义检索+关键词混合检索，无需配置外部 Embedding 模型（内置向量化检索）

> ⚠️ 本文档主要描述**长期记忆模块**的实现。短期记忆请参见 `src/tool_executor.py`。

### 核心特性

本模块（长期记忆）支持智能去重、版本控制、层级摘要、异步处理等高级特性：

- ✅ **版本回溯**：完整保留历史版本，支持版本对比
- ✅ **层级摘要**：日→月→年自动归纳总结
- ✅ **异步处理**：后台队列不阻塞主流程
- ✅ **混合检索**：Embedding + TF-IDF 双重匹配
- ✅ **增量更新**：只处理新增记忆，效率优化
- ✅ **缓存优化**：嵌入缓存加速检索

## 目录结构

```
src/mem/
├── src/
│   ├── core/                      # 核心管理层
│   │   ├── memory_manager.py       # 统一管理接口
│   │   ├── preliminary.py          # 初级记忆管理
│   │   └── memoir.py               # 高级记忆管理
│   ├── models/                    # 数据模型
│   │   ├── memory_cell.py          # 记忆单元数据结构
│   │   └── mem.py                  # 低级存储管理
│   ├── clients/                   # 外部服务客户端
│   │   ├── llm_client.py           # LLM调用接口
│   │   └── embedding_client.py      # 向量嵌入服务
│   └── utils/                      # 工具模块
│       ├── config.py               # 配置管理
│       ├── embedding_cache.py      # 嵌入缓存
│       ├── logger.py               # 日志管理
│       ├── monitor.py              # 性能监控
│       ├── security.py             # 安全管理
│       └── exceptions.py           # 异常定义
├── demo.py                         # 演示脚本
└── README.md                       # 本文件
```

## 快速开始

### 基本使用

```python
from src.mem import MemManagerAgent

# 创建记忆管理器
agent = MemManagerAgent(
    storage_path="memory",
    config_file="config.txt"
)

# 写入记忆
agent.write_memory_auto("今天学习了Python编程")

# 检索记忆
results = agent.read_memory_auto("Python编程")

# 获取状态
status = agent.get_status_auto()
```

### 异步写入

```python
# 创建带异步支持的记忆管理器
agent = MemManagerAgent(
    enable_async=True,
    worker_threads=2,
    max_queue_size=1000
)

# 异步写入记忆
def callback(result):
    print(f"记忆写入完成: {result}")

agent.write_memory_auto(
    "完成了项目开发",
    callback=callback,
    priority=1
)
```

## 核心接口

### MemManagerAgent

统一管理接口，封装了初级记忆和高级记忆的所有功能。

| 方法 | 说明 |
|------|------|
| `write_memory_auto()` | 智能写入记忆，自动判断新增或更新 |
| `read_memory_auto()` | 智能检索记忆，支持语义搜索 |
| `get_status_auto()` | 获取系统完整状态 |
| `get_status_summary()` | 获取系统状态摘要 |

### PreliminaryMemoryManager

初级记忆管理，处理基础的记忆存储和检索。

| 方法 | 说明 |
|------|------|
| `write_memory_auto()` | 写入新记忆或更新相似记忆 |
| `search_memories_by_query()` | 按内容搜索记忆 |
| `search_memories_by_time()` | 按时间搜索记忆 |
| `get_memory_stats()` | 获取记忆统计信息 |

### MemoirManager

高级记忆管理，负责日/月/年层级摘要生成。

| 方法 | 说明 |
|------|------|
| `update_memoir_all()` | 批量更新所有可更新的摘要 |
| `search_memoir_by_query()` | 搜索高级记忆摘要 |
| `search_memoir_by_time()` | 按时间搜索摘要 |
| `get_status_summary()` | 获取摘要系统状态 |

## 配置参数

配置文件：`config/config_memory.txt`

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `memory_similarity_threshold` | 0.5 | 相似度阈值(0.0-1.0) |
| `memory_max_tokens` | 4096 | 单条记忆最大token数 |
| `memory_update_strategy` | intelligent | 更新策略 |
| `embedding_search_weight` | 0.6 | 向量搜索权重 |
| `tfidf_search_weight` | 0.4 | TF-IDF搜索权重 |
| `auto_store_task_memory` | True | 任务完成自动存储 |
| `default_recall_count` | 5 | 默认返回结果数 |

## 存储结构

### 初级记忆

```
preliminary_memory/
├── texts/                        # 记忆文本文件
│   ├── mem_xxx.md
│   └── ...
├── embedding_cache/             # 向量嵌入缓存
├── summary_tfidf_cache/         # TF-IDF模型缓存
└── preliminary_mem.json          # 记忆索引文件
```

### 高级记忆

```
memoir/
├── memoir_2025.json             # 按年存储
├── memoir_2024.json
└── memoir_tfidf_cache/           # 摘要TF-IDF缓存
```

## 检索工具

系统提供三个记忆检索工具，可供Agent调用：

### recall_memories

基于语义相似度搜索长期记忆。

```json
{
  "query": "Python编程",
  "top_k": 5
}
```

### recall_memories_by_time

基于时间范围搜索记忆。

```json
{
  "time_query": "昨天",
  "top_k": 5
}
```

### get_memory_summary

获取记忆系统状态摘要。

```json
{}
```

## 算法说明

### 混合搜索算法

采用 **Embedding + TF-IDF** 双通道加权检索：

```
combined_score = embedding_weight × embedding_similarity + tfidf_weight × tfidf_similarity
```

- 向量嵌入(Embedding)：捕捉语义相似性
- TF-IDF：捕捉词频特征

### 智能摘要生成

采用 LLM 进行智能整合：

1. 提取新记忆的摘要
2. 与现有摘要进行整合
3. 生成新的连贯摘要
4. 保留重要历史信息

### 版本控制

更新时采用 `VersionN` 格式保留历史：

```
Version2：最新的记忆内容
Version1：之前的内容
Version0：原始内容
```

## 性能优化

- **嵌入缓存**：避免重复计算向量嵌入
- **TF-IDF缓存**：模型持久化，减少重训练
- **增量更新**：只处理新增记忆
- **异步队列**：后台处理，不阻塞主流程
- **LRU缓存**：热门查询结果缓存

## 异常处理

系统内置完善的异常处理机制：

- `MemorySystemError`: 记忆系统基础异常
- `ConfigError`: 配置相关异常
- `LLMClientError`: LLM调用异常
- `EmbeddingError`: 嵌入服务异常
- `StorageError`: 存储操作异常
- `ValidationError`: 数据验证异常

## 许可证

本项目遵循 Apache License 2.0 许可证。

## 版本

当前版本：2.0.0
