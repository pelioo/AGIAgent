# WebSearchTools 详细逻辑分析

> **文件**: `src/tools/web_search_tools.py`  
> **大小**: 5201 行，约 275KB  
> **更新时间**: 2026-05-29

---

## 目录

1. [概览](#概览)
2. [类结构图](#类结构图)
3. [核心执行流程](#核心执行流程)
4. [关键设计决策](#关键设计决策)
5. [初始化参数](#初始化参数)
6. [反爬虫机制](#反爬虫机制)
7. [搜索结果数据结构](#搜索结果数据结构)
8. [性能优化点](#性能优化点)
9. [方法详解](#方法详解)

---

## 概览

这是一个 **网页搜索和内容提取工具类**，核心功能是使用浏览器自动化（Playwright）进行网络搜索并提取网页内容。

| 项目 | 说明 |
|------|------|
| **核心类** | `WebSearchTools` |
| **核心依赖** | `playwright`（浏览器自动化）、`requests`（HTTP 下载）、`BeautifulSoup`（HTML 解析）|
| **可选依赖** | LLM API（OpenAI/Anthropic），用于内容过滤和摘要生成 |

---

## 类结构图

```
WebSearchTools
├── __init__()           初始化（LLM配置、Zhipu搜索、路径设置）
├── web_search()         主搜索入口（搜索+内容提取）
├── search_img()         图片搜索
├── fetch_webpage_content()  直接获取指定URL内容
│
├── 🔍 搜索引擎支持
│   ├── 百度 (Baidu)      语言=zh 时启用
│   ├── 必应 (Bing)       始终启用
│   ├── DuckDuckGo        HTML版本
│   └── Google            回退选项
│
├── 📥 内容获取
│   ├── _fetch_webpage_content_with_timeout()  并行下载内容（requests）
│   ├── _fetch_webpage_content()               串行下载（Playwright后备）
│   ├── _download_single_webpage()             单页面下载（requests）
│   └── _download_single_webpage_with_playwright()  单页面下载（Playwright）
│
├── 📝 内容提取
│   ├── _extract_main_content()                主内容提取（CSS选择器）
│   ├── _extract_content_from_html()           从HTML字符串提取
│   ├── _post_process_extracted_content()       后处理（格式化）
│   └── _is_quality_content()                  质量判断
│
├── 🧹 文本清洗
│   ├── _clean_text_for_saving()               完整清洗（去除HTML/JS/CSS）
│   ├── _clean_text_for_saving_simple()        简化清洗（超时后备）
│   └── _clean_body_content()                  body内容清洗
│
├── 💾 文件保存
│   ├── _save_webpage_content()                保存HTML和TXT（Playwright page）
│   ├── _save_webpage_content_from_html()       保存HTML和TXT（HTML字符串）
│   └── _ensure_result_directory()              确保目录存在
│
├── 🔐 特殊页面检测
│   └── _detect_special_page()                 检测验证页、豆丁网、百度文库等
│
├── 🔓 URL处理
│   ├── _decode_baidu_redirect_url()           解码百度重定向URL
│   ├── _decode_bing_redirect_url()            解码必应重定向URL
│   ├── _decode_duckduckgo_redirect_url()      解码DuckDuckGo重定向URL
│   ├── _normalize_url()                       规范化URL
│   └── _normalize_url_for_dedup()             去重规范化
│
├── 🖼️ 图片搜索
│   ├── _extract_google_images_metadata()      Google图片JSON元数据提取
│   ├── _extract_other_engines_images()         其他引擎图片提取
│   └── _format_google_image_object()          格式化Google图片对象
│
├── 🧠 LLM功能
│   ├── _setup_llm_client()                    初始化LLM客户端
│   ├── _extract_relevant_content_with_llm()   LLM内容过滤
│   └── _summarize_search_results_with_llm()   LLM搜索结果摘要
│
└── 📊 工具方法
    ├── _optimize_search_term()                优化搜索词
    ├── _clean_snippet()                        清洗摘要
    ├── _extract_snippet_from_search_result()  提取搜索结果摘要
    └── _print_webpage_summary()               打印网页摘要
```

---

## 核心执行流程

### web_search() 主流程

```
┌──────────────────────────────────────────────────────────────────────┐
│                      web_search() 主流程                             │
│                                                                      │
│  输入: search_term, fetch_content, max_content_results               │
│                                                                      │
│  ┌─────────────────┐                                                  │
│  │ 1. Zhipu AI 检查 │  ← 优先使用Zhipu搜索API（如果配置了API Key）      │
│  └────────┬────────┘                                                  │
│           │ 否                                                        │
│           ▼                                                           │
│  ┌─────────────────┐                                                  │
│  │ 2. Playwright   │  ← 回退到浏览器自动化                              │
│  │    可用性检查   │                                                  │
│  └────────┬────────┘                                                  │
│           │                                                           │
│           ▼                                                           │
│  ┌─────────────────┐                                                  │
│  │ 3. 网络连通性   │  ← 发送请求到baidu.com测试                         │
│  │    测试        │                                                  │
│  └────────┬────────┘                                                  │
│           │                                                           │
│           ▼                                                           │
│  ┌──────────────────────────────────────────────────────────┐        │
│  │ 4. 搜索引擎轮询 (按优先级)                                  │        │
│  │                                                          │        │
km|│  │  中文环境:  百度 → 必应 → DuckDuckGo → Google            │        │
bn|│  │  英文环境:  必应 → DuckDuckGo → Google                    │        │
│  │                                                          │        │
│  │  每个引擎最多重试2次                                      │        │
│  │  失败引擎记录到 failed_engines 跳过后续                  │        │
│  └────────┬─────────────────────────────────────────────────┘        │
│           │                                                           │
│           ▼                                                           │
│  ┌─────────────────┐                                                  │
│  │ 5. URL 解码     │  ← 解码DuckDuckGo/百度/必应重定向URL              │
│  │    和去重       │  ← 规范化后去重                                   │
│  └────────┬────────┘                                                  │
│           │                                                           │
│           ▼                                                           │
│  ┌─────────────────┐                                                  │
│  │ 6. 内容获取     │  ← 并行下载（requests，最多5线程）                 │
│  │   (可选)        │  ← 最多尝试 max_content_results × 3 次            │
│  └────────┬────────┘                                                  │
│           │                                                           │
│           ▼                                                           │
│  ┌─────────────────┐                                                  │
│  │ 7. LLM 摘要     │  ← 如果启用了enable_summary                       │
│  │   (可选)        │  ← 对前10个结果进行深度分析                        │
│  └────────┬────────┘                                                  │
│           │                                                           │
│           ▼                                                           │
│  ┌─────────────────┐                                                  │
│  │ 8. 文件保存     │  ← 保存HTML和TXT到 web_search_result/             │
│  │                 │  ← 包含元数据（标题、URL、时间等）                 │
│  └────────┬────────┘                                                  │
│           │                                                           │
│           ▼                                                           │
│  输出: 完整结果字典                                                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 图片搜索流程 (search_img)

```
┌────────────────────────────────────────────────┐
│           search_img() 图片搜索流程             │
│                                               │
│  1. 检查 Playwright 可用性                    │
│  2. 创建 images 子目录                         │
│  3. 引擎轮询: Google Images → Baidu Images     │
│  4. 提取图片元数据 (JSON 或 DOM)              │
│  5. 图片下载 (requests + ThreadPoolExecutor) │
│  6. 格式转换 (统一转为 JPG)                   │
│  7. 保存到 web_search_result/images/          │
│                                               │
└────────────────────────────────────────────────┘
```

---

## 关键设计决策

### 1. 双模式搜索

| 模式 | 使用条件 | 优势 |
|------|----------|------|
| **Zhipu API** | 配置了有效的 Zhipu API Key | 更快速、更稳定 |
| **Playwright 浏览器** | 未配置 API 或 API 调用失败 | 支持任何网站 |

### 2. 并行内容下载

- 使用 `ThreadPoolExecutor` 并行下载，最多 **5 个线程**
- **线程安全**：使用 `requests`（而非 Playwright）进行并行下载
- 每个下载任务有 **30 秒超时**
- 整体操作有 **90 秒超时**

### 3. 特殊页面过滤

`_detect_special_page()` 检测以下特殊页面：

| 页面类型 | 检测方式 | 处理方式 |
|----------|----------|----------|
| 验证页面 | 包含 "当前环境异常，完成验证后即可继续访问。" | 返回验证消息 |
| 豆丁网 | 包含 "豆丁网" 或 "docin.com" | 标记并跳过 |
| 百度文库 | URL 或内容包含 "wenku.baidu.com" | 标记并跳过 |
| 百度移动端 | URL 或内容包含 "mbd.baidu.com" | 标记并跳过 |
| 百度学术 | 内容包含 "百度学术搜索" 等 | 标记并跳过 |
| DuckDuckGo广告 | URL 或内容包含 "ads-by" | 标记并跳过 |

### 4. URL 去重策略

```python
_normalize_url_for_dedup() 执行步骤:
1. 解码重定向URL（获取真实目标）
2. 去除查询参数（?后的内容）
3. 去除锚点（#后的内容）
4. 去除尾部斜杠（除非是根路径）
5. 转小写比较
```

### 5. 内容清洗流程

`_clean_text_for_saving()` 的清洗步骤：

1. **HTML 标签移除** - `re.sub(r'<[^>]+>', '', content)`
2. **JSON/GraphQL 块移除** - 去除 Apollo 缓存、GraphQL 响应
3. **JavaScript 代码移除** - 移除 `window.`、`console.`、`addEventListener` 等
4. **CSS 属性移除** - 只移除真正的 CSS 属性，保留元数据
5. **单词粘连修复** - `ForIndividuals` → `For Individuals`
6. **URL 保护/替换** - 重要学术URL保留，其他替换为 `[链接]`
7. **行级清洗** - 移除代码行、JSON行、过度标点行

### 6. 搜索引擎优先级

```python
qm|中文环境 (语言 = 'zh'):
lf|  1. 百度 (Baidu)
ds|  2. 必应 (Bing)
dz|  3. DuckDuckGo
wm|  4. Google
yy|
gx|英文环境 (语言 != 'zh'):
pn|  1. 必应 (Bing)        # 无论语言环境，必应始终包含
vu|  2. DuckDuckGo
bd|  3. Google
fy|
> **注意**: 必应始终无条件添加，不受语言环境限制。

### 7. 内容获取验证

| 条件 | 要求 |
|------|------|
| 有效内容 | 至少 200 字符 |
| 可保存内容 | 至少 50 字符（清洗后） |
| 摘要生成 | 至少 1000 字符原始内容 |

---

## 初始化参数

```python
def __init__(
    self,
    llm_api_key: str = None,              # LLM API 密钥
    llm_model: str = None,                # LLM 模型名称
    llm_api_base: str = None,             # LLM API 基础URL
    enable_llm_filtering: bool = False,   # 启用LLM内容过滤
    enable_summary: bool = True,          # 启用LLM摘要生成
    workspace_root: str = None,           # 工作空间根目录
    out_dir: str = None,                  # 输出目录
    verbose: bool = True                  # 详细输出控制
dj|)
fy|
> **注意**: 以下属性通过 `config_loader` 自动初始化，无需手动传入:
> - `zhipu_search_api_key`: 从配置读取智谱搜索 API Key
> - `zhipu_search_engine`: 从配置读取智谱搜索使用的引擎类型
> - `use_zhipu_search`: 根据 API Key 有效性自动设置（智谱搜索优先于 Playwright）

### 路径配置逻辑

```python
# 优先级:
1. workspace_root + "workspace/web_search_result"
2. out_dir + "workspace/web_search_result"
3. os.getcwd() + "workspace/web_search_result"
```

---

## 反爬虫机制

### 1. User-Agent 伪装

```python
user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
```

### 2. Playwright 初始化脚本

```javascript
// 隐藏 webdriver 标志
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 隐藏 Chrome 标志
window.chrome = { runtime: {} };

// 伪造权限查询
navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// 伪造插件列表
navigator.plugins = [1, 2, 3, 4, 5];

// 伪造语言列表
navigator.languages = ['en-US', 'en'];
```

### 3. Chrome 参数优化

| 参数 | 作用 |
|------|------|
| `--disable-blink-features=AutomationControlled` | 禁用自动化控制检测 |
| `--exclude-switches=enable-automation` | 排除自动化开关 |
| `--allow-running-insecure-content` | 允许混合内容 |
| `--disable-web-security` | 禁用Web安全（同源策略） |
| `--ignore-certificate-errors` | 忽略证书错误 |
| `--no-sandbox` | 禁用沙箱模式（Docker环境） |

---

## 搜索结果数据结构

```python
{
    'status': 'success',
    'search_term': '搜索词',
    'results': [
        {
            'title': '网页标题',
            'content': '提取的内容（超过200字符）',
            'content_summary': '内容摘要（截断版本）',
            'source': 'Baidu/Bing/...',
            'snippet': '搜索结果摘要',
            'saved_html_path': 'HTML文件路径',
            'saved_txt_path': 'TXT文件路径',
            'has_full_content': True/False
        },
        ...
    ],
    'timestamp': 'ISO时间戳',
    'total_results': 5,
    'saved_html_files': 5,
    'saved_txt_files': 4,
    'total_txt_files_in_directory': 15,
    'summary': 'LLM生成的综合摘要（如果启用）',
    'summary_available': True/False,
    'files_notice': '文件保存提示',
    'search_material_warning': '⚠️ 警告信息（如文件过多）'
}
```

---

## 性能优化点

| 优化项 | 实现位置 | 说明 |
|--------|----------|------|
| **资源阻塞** | `block_resources()` 函数 | 阻止图片/CSS/字体/媒体加载 |
| **超时控制** | `web_search()` 方法内 | 页面加载 15s，导航 20s |
| **内容截断** | `_save_webpage_content()` 方法 | 超过 500KB 的内容截断清洗 |
| **批量处理** | `web_search()` 方法内 | 最多尝试 max × 3 次获取有效结果 |
| **失败引擎跳过** | `web_search()` 方法内 | 失败的搜索引擎记录，后续跳过 |
| **并行下载** | `_fetch_webpage_content_with_timeout()` 方法 | 最多 5 线程并发下载 |
| **搜索引擎超时** | `web_search()` 方法内 | 百度 30s，其他 15s |

---

## 方法详解

### 核心方法

#### `web_search(search_term, fetch_content=True, max_content_results=5)`

主搜索入口，搜索并提取网页内容。

**参数**:
- `search_term`: 搜索关键词
- `fetch_content`: 是否获取网页内容
- `max_content_results`: 最大内容结果数

**返回**: 包含搜索结果、文件路径、摘要的字典

#### `fetch_webpage_content(url, search_term=None)`

直接获取指定 URL 的内容。

**参数**:
- `url`: 目标 URL
- `search_term`: 搜索词（用于内容过滤）

**返回**: 包含内容、元数据、文件路径的字典

#### `search_img(query)`

图片搜索，支持 Google Images 和 Baidu Images。

**参数**:
- `query`: 图片搜索关键词

**返回**: 包含图片列表、路径、大小的字典

### 内容提取方法

#### `_extract_main_content(page)`

使用 CSS 选择器从页面提取主要内容。

**选择器优先级**:
1. 媒体特定选择器 (Medium, 知乎等)
2. 通用文章选择器 (`.article-content`, `article`, `main` 等)
3. 通用内容选择器 (`.content`, `#content` 等)
4. Markdown 选择器 (`.markdown-body` 等)
5. Wiki/文档选择器
6. Body 回退

#### `_clean_text_for_saving(content)`

完整文本清洗，保留有意义的内容。

**清洗规则**:
- 移除 HTML/JS/CSS 代码
- 修复粘连单词
- 保护重要 URL
- 移除代码片段

### URL 处理方法

#### `_normalize_url_for_dedup(url)`

URL 去重规范化。

**处理流程**:
1. 解码重定向 URL
2. 移除查询参数和锚点
3. 规范化尾部斜杠
4. 转小写

#### `_decode_baidu_redirect_url(url)`

解码百度重定向 URL，支持多种解码方式：
- URL 解码 (单次/双重)
- Base64 解码

### LLM 方法

#### `_summarize_search_results_with_llm(results, search_term)`

使用 LLM 生成搜索结果摘要。

**特性**:
- 逐个分析每个网页结果
- 提取关键信息、事实、数据
- 保留原文语言
- 生成综合总结

---

## 配置说明

### Zhipu API 配置

```python
# 在 config_loader 中配置:
get_zhipu_search_api_key()    # API 密钥
get_zhipu_search_engine()     # 搜索引擎类型
```

### 截断长度配置

```python
get_web_content_truncation_length()  # 网页内容截断长度
get_truncation_length()              # 摘要截断长度
```

---

## 依赖说明

### 必需依赖

```txt
playwright              # 浏览器自动化
requests               # HTTP 请求
beautifulsoup4 (bs4)   # HTML 解析
Pillow (PIL)          # 图片处理
```

### 可选依赖

```txt
anthropic             # Claude API (如使用 Claude 模型)
openai                # OpenAI API (如使用 GPT 模型)
chardet               # 编码检测 (如可用)
```

### 安装命令

```bash
pip install playwright
playwright install chromium
```

---

## 错误处理

### 超时处理

| 类型 | 超时时间 | 处理方式 |
|------|----------|----------|
| 页面加载 | 15s | 跳过该页面 |
| 导航超时 | 20s | 重试或跳过 |
| 整体搜索 | 90s | 返回超时错误 |
| 图片下载 | 3s (每张) | 跳过该图片 |

### 失败恢复

1. **搜索引擎失败**: 记录到 `failed_engines`，后续跳过
2. **内容获取失败**: 尝试使用 `requests` 后备
3. **清洗超时**: 使用简化清洗方法

---

## 文件输出格式

### HTML 文件

```
web_search_result/
├── search_term_page_title_20260101_120000.html
├── another_query_result_20260101_120001.html
└── ...
```

### TXT 文件

```txt
Title: 页面标题
URL: https://example.com/page
Search Term: 搜索词
Timestamp: 2026-01-01T12:00:00
Original Content Length: 15000 characters
Cleaned Content Length: 8000 characters


正文内容...
```

---

## 安全考虑

1. **敏感内容过滤**: 标题包含敏感关键词的结果会被跳过
2. **问题域名过滤**: 视频网站、社交媒体等无法获取正确文字的域名会被跳过
3. **政治内容过滤**: 自动过滤包含敏感政治关键词的页面

---

## 维护建议

### 搜索引擎变更

当搜索引擎结构变化时，可能需要更新：
- CSS 选择器 (`.result_selector`, `.container_selector`)
- URL 格式
- 摘要提取逻辑

### 编码问题

如遇编码问题，检查：
1. HTML meta charset 声明
2. 响应头 Content-Type
3. chardet 库检测结果

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/tools/web_search_tools_z.py` | Zhipu API 搜索实现 |
| `src/tools/print_system.py` | 打印工具 |
| `src/config_loader.py` | 配置加载器 |