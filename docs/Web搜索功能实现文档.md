# Web 搜索功能实现文档

> 本文档详细记录了 AGI Agent 项目中 Web 搜索功能的实现架构、核心算法和配置方法。

---

## 📑 目录

1. [架构概览](#1-架构概览)
2. [核心类实现](#2-核心类实现)
3. [搜索引擎策略](#3-搜索引擎策略)
4. [内容抓取机制](#4-内容抓取机制)
5. [LLM 智能处理](#5-llm-智能处理)
6. [URL 处理与去重](#6-url-处理与去重)
7. [特殊页面检测](#7-特殊页面检测)
8. [文件存储机制](#8-文件存储机制)
9. [配置参数](#9-配置参数)
10. [错误处理](#10-错误处理)
11. [性能优化](#11-性能优化)

---

## 1. 架构概览

### 1.1 整体架构

```
WebSearchTools (主入口类, 279KB)
    |
    +-- ZhipuWebSearchTools (智谱AI搜索)
    +-- Playwright 浏览器自动化
    +-- LLM Client (Claude/OpenAI)
    +-- URL 处理与去重模块
```

### 1.2 文件结构

| 文件 | 大小 | 说明 |
|------|------|------|
| web_search_tools.py | 272KB | 主搜索实现 |
| web_search_tools_z.py | 11KB | 智谱AI搜索封装 |

---

## 2. 核心类实现

### 2.1 WebSearchTools 主类

```python
class WebSearchTools:
    def __init__(
        self,
        llm_api_key: str = None,
        llm_model: str = None,
        llm_api_base: str = None,
        enable_llm_filtering: bool = False,
        enable_summary: bool = True,
        workspace_root: str = None,
        out_dir: str = None,
        verbose: bool = True
    ):
```

**核心属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| zhipu_search_api_key | str | 智谱AI搜索API密钥 |
| zhipu_search_engine | str | 智谱搜索引擎类型 |
| use_zhipu_search | bool | 是否启用智谱搜索 |
| failed_engines | set | 失败的搜索引擎集合 |
| downloaded_urls | set | 已下载URL集合(去重) |
| enable_llm_filtering | bool | 启用LLM内容过滤 |
| enable_summary | bool | 启用搜索结果摘要 |

### 2.2 ZhipuWebSearchTools

```python
class ZhipuWebSearchTools:
    API_URL = "https://open.bigmodel.cn/api/paas/v4/web_search"
```

**可用搜索引擎**: search_std, search_pro, search_pro_sogou, search_pro_quark

---

## 3. 搜索引擎策略

### 3.1 多引擎优先级（语言自适应）

| 引擎 | 条件 | 超时 |
|------|------|------|
| Baidu | 中文模式（zh） | 30秒 |
| DuckDuckGo | 始终（主/备选） | 15秒 |
| Google | 回退选项 | 15秒 |

**语言检测逻辑**：
```python
current_lang = get_language()  # 读取配置文件中的 language 设置
if current_lang == 'zh':
    # 搜索顺序: Baidu → DuckDuckGo → Google
else:
    # 搜索顺序: DuckDuckGo → Google
```

### 3.2 失败引擎缓存

```python
self.failed_engines = set()

# 失败时
self.failed_engines.add(engine['name'])

# 跳过已失败的引擎
if engine['name'] in self.failed_engines:
    continue
```

---

## 4. 内容抓取机制

### 4.1 Playwright 配置

```python
browser = p.chromium.launch(
    headless=True,
    args=[
        '--no-sandbox', '--disable-setuid-sandbox',
        '--disable-dev-shm-usage', '--disable-web-security',
        '--disable-features=VizDisplayCompositor,TranslateUI,AudioServiceOutOfProcess',
        '--disable-gpu', '--disable-gpu-sandbox', '--disable-software-rasterizer',
        '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
        '--disable-backgrounding-occluded-windows', '--disable-extensions',
        '--disable-default-apps', '--disable-sync', '--disable-background-networking',
        '--disable-component-update', '--disable-client-side-phishing-detection',
        '--disable-hang-monitor', '--disable-popup-blocking', '--disable-prompt-on-repost',
        '--disable-domain-reliability', '--no-first-run', '--no-default-browser-check',
        '--no-pings', '--disable-remote-debugging', '--disable-http2', '--disable-quic',
        '--ignore-ssl-errors', '--ignore-certificate-errors', '--disable-background-mode',
        '--force-color-profile=srgb', '--disable-ipc-flooding-protection',
        '--disable-blink-features=AutomationControlled', '--exclude-switches=enable-automation',
        '--disable-plugins-discovery', '--allow-running-insecure-content'
    ]
)

# Browser Context 配置
context = browser.new_context(
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    viewport={'width': 1024, 'height': 768},
    ignore_https_errors=True,
    java_script_enabled=True,
    bypass_csp=True,
    locale='en-US',
    timezone_id='America/New_York'
)
```

### 4.2 内容选择器优先级

1. Medium特定选择器
2. 通用文章选择器 (.article_content, .content-detail)
3. 中文内容选择器 (.zhengwen, .neirong)
4. 通用选择器 (article, main)
5. 最后手段 (body)

### 4.3 并行下载策略

```python
batch_size = max_content_results  # 默认5
max_attempts = min(len(results), max_content_results * 3)
```

---

## 5. LLM 智能处理

### 5.1 内容过滤

使用 LLM 提取与搜索词相关的内容，移除导航、广告、页脚等无关内容。

### 5.2 搜索结果摘要

- 逐个分析每个网页结果
- 提取关键信息、事实、数据
- 提供跨来源综合
- 包含保存文件的引用

---

## 6. URL 处理与去重

### 6.1 DuckDuckGo 重定向解码

```python
def _decode_duckduckgo_redirect_url(self, ddg_url):
    # 格式: https://duckduckgo.com/l/?uddg=encoded_url
    if 'duckduckgo.com/l/' in ddg_url and 'uddg=' in ddg_url:
        # 解析并解码 uddg 参数
```

### 6.2 URL 规范化去重

移除追踪参数: utm_*, fbclid, gclid 等

---

## 7. 特殊页面检测

| 页面类型 | 检测方式 | 处理 |
|----------|----------|------|
| 验证页面 | 内容检测 | 跳过 |
| 百度文库 | URL | 跳过 |
| 百度移动端 | URL | 跳过 |
| 百度学术 | 内容 | 跳过 |
| DuckDuckGo广告 | URL | 跳过 |

---

## 8. 文件存储机制

### 8.1 目录结构

```
workspace/
└── web_search_result/
    ├── {search_term}_{title}_{timestamp}.html
    └── {search_term}_{title}_{timestamp}.txt
```

---

## 9. 配置参数

### config.txt 配置项

```ini
# 智谱AI Web 搜索配置
zhipu_search_api_key=your key
zhipu_search_engine=search_std

# 内容截断长度（默认50000）
web_content_truncation_length=50000

# 简化输出
simplified_search_output=True

# Web 搜索摘要
web_search_summary=True

# 语言设置（影响搜索引擎选择：zh=中文模式, en=英文模式）
language=zh
```

---

## 10. 错误处理

| 异常类型 | 处理方式 |
|----------|----------|
| Timeout | 返回超时错误，尝试下一引擎 |
| RequestException | 标记引擎失败，跳过后续 |
| JSONDecodeError | 返回解析错误信息 |

---

## 11. 性能优化

1. 全局90秒超时控制
2. 选择器查询3秒超时
3. 内容清理10秒超时
4. URL去重避免重复下载
5. 内容长度500KB限制

---

## 附录: 关键代码位置

| 功能 | 文件位置 |
|------|----------|
| 主类初始化 | web_search_tools.py:70-175 |
| 搜索引擎列表 | web_search_tools.py:1140-1195 |
| Playwright启动 | web_search_tools.py:1103-1135 |
| LLM过滤 | web_search_tools.py:590-670 |
| LLM摘要 | web_search_tools.py:692-850 |
| 特殊页面检测 | web_search_tools.py:214-290 |
| URL规范化 | web_search_tools.py:4204-4260 |
| 文件保存 | web_search_tools.py:320-550 |

---

*文档版本: 1.0*
*最后更新: 2025-04-17*


---

## 附录 B: 新增功能详解

### B.1 内容后处理

```python
def _post_process_extracted_content(self, content: str) -> str:
    """
    后处理提取的内容，处理常见格式问题
    """
    # 移除CSS规则
    content = re.sub(r'\.[a-zA-Z][\w\-]*\s*\{[^}]*\}\s*', '', content)
    
    # 数字编号项添加换行
    content = re.sub(r'([。！？])\s*([1-9]\d*\.|\([1-9]\d*\))', r'\1\n\2', content)
    
    # 新闻标题格式处理
    content = re.sub(r'(【[^】]*】[^【]{10,}?)(\s+【)', r'\1\n\2', content)
    
    # 清理多余空白
    content = re.sub(r' {3,}', '  ', content)
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
```

### B.2 requests 下载

```python
def _download_webpage_with_requests(self, url: str, timeout: float = 5.0) -> tuple:
    """
    使用 requests 下载网页，返回 (html_content, final_url, title)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    response = requests.get(url, headers=headers, timeout=timeout, 
                          allow_redirects=True, verify=False)
    
    # 检测编码
    detected_encoding = self._detect_html_encoding(response.content)
    html_content = response.content.decode(detected_encoding, errors='replace')
    
    return html_content, response.url, title
```

### B.3 百度URL解码

```python
def _decode_baidu_redirect_url(self, baidu_url: str) -> str:
    """
    解码百度重定向URL
    支持: URL解码、双重解码、base64解码
    """
    # 方法1: 基本URL解码
    # 方法2: 双重URL解码  
    # 方法3: base64解码
    # 返回解码后的真实URL或原URL
```

### B.4 并行下载策略

```python
# 使用 ThreadPoolExecutor 最多5个线程并行下载
max_workers = min(5, len(urls_to_download))

with ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_info = {}
    for result, global_index, target_url in urls_to_download:
        future = executor.submit(
            self._download_single_webpage,
            result, global_index, target_url, search_term
        )
        future_to_info[future] = (result, global_index, target_url)
```

---

## 附录 C: 配置参数速查

### C.1 config.txt 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `zhipu_search_api_key` | str | - | 智谱API密钥 |
| `zhipu_search_engine` | str | search_std | 智谱引擎类型 |
| `web_content_truncation_length` | int | 50000 | 内容截断长度 |
| `simplified_search_output` | bool | True | 简化输出 |
| `web_search_summary` | bool | True | 启用AI摘要 |
| `language` | str | zh | 语言设置（zh/en） |

### C.2 运行时参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `search_term` | str | 必需 | 搜索关键词 |
| `fetch_content` | bool | True | 是否抓取内容 |
| `max_content_results` | int | 5 | 最大内容数 |

---

## 附录 D: 超时配置汇总

| 操作 | 超时 |
|------|------|
| 全局搜索 | 90秒 |
| Baidu导航 | 30秒 |
| DDG/Google导航 | 15秒 |
| 搜索结果页面默认 | 15秒 |
| 选择器查询 | 3秒 |
| 内容清理 | 10秒 |
| requests下载 | 默认5秒（可配置） |
| Playwright下载 | 10秒 |
| 图片下载 | 2秒 |

---

*文档版本: 1.3*
*最后更新: 2026-04-18*
